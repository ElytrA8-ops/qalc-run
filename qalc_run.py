
import sys
import math
import threading
from pynput import keyboard as pynput_keyboard
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QGuiApplication

class CalculatorWidget(QWidget):
    def event(self, event):
        # Hide window when focus is lost (i.e., user switches to another window)
        if event.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(event)
    def keyPressEvent(self, event):
        # Ctrl+L to clear input
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_L:
            self.input.clear()
        else:
            super().keyPressEvent(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qalc-Run: Calculator")
        self.resize(500, 400)
        self.setStyleSheet("""
            QWidget {
                background: #f7f7f7;
                color: #222;
                font-size: 18px;
                font-family: 'Segoe UI', 'Liberation Sans', Arial, sans-serif;
            }
            QLineEdit {
                padding: 10px;
                border-radius: 6px;
                background: #fff;
                color: #222;
                border: 1px solid #bbb;
                font-size: 20px;
            }
            QLabel#ResultLabel {
                padding: 10px;
                border-radius: 6px;
                background: #e9f5e9;
                color: #217a3c;
                font-weight: bold;
                font-size: 22px;
                border: 1px solid #b6e2c1;
            }
            QLabel#InfoLabel {
                padding: 2px;
                color: #666;
                font-size: 13px;
            }
            QScrollArea {
                background: #f7f7f7;
                border-radius: 6px;
                border: 1px solid #eee;
            }
        """)

        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a calculation and press Enter... (supports %, ans, pi, e, min, max, pow, round)")
        self.input.returnPressed.connect(self.save_and_copy)
        self.input.textChanged.connect(self.calculate)
        self.input.setObjectName("InputField")
        layout.addWidget(self.input)

        self.result = QLabel("")
        self.result.setObjectName("ResultLabel")
        self.result.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result)

        self.info = QLabel("Use %, ans, pi, e, min, max, pow, round. Example: 11+11% or ans*2")
        self.info.setObjectName("InfoLabel")
        self.info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info)

        self.setLayout(layout)
        self.last_answer = 0
        self.history = []

        # History area (scrollable)
        from PySide6.QtWidgets import QScrollArea, QWidget
        self.history_area = QScrollArea()
        self.history_area.setWidgetResizable(True)
        self.history_area.setStyleSheet("")
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_widget.setLayout(self.history_layout)
        self.history_area.setWidget(self.history_widget)
        layout.addWidget(self.history_area, stretch=1)

    def calculate(self):
        expr = self.input.text()
        if not expr.strip():
            self.result.setText("")
            return
        try:
            import re
            # Allow 'ans' for last answer
            expr_mod = expr.replace('ans', str(self.last_answer))

            # Advanced percent handling: handle +, -, *, / before %
            def percent_replacer(match):
                op = match.group(1)
                number = match.group(2)
                before = expr_mod[:match.start()].rstrip()
                # Find the last number/expression before the percent
                prev_match = re.search(r'(\d+(?:\.\d+)?|\))\s*$', before)
                if prev_match:
                    prev = prev_match.group(1)
                    if prev == ')':
                        stack = 1
                        i = len(before) - 2
                        while i >= 0:
                            if before[i] == ')':
                                stack += 1
                            elif before[i] == '(': 
                                stack -= 1
                            if stack == 0:
                                break
                            i -= 1
                        prev = before[i:]
                else:
                    prev = str(self.last_answer)
                if op == '+' or op == '-':
                    return f'{op}(({number}/100)*{prev})'
                elif op == '*':
                    return f'*({number}/100)'
                elif op == '/':
                    return f'/( {number}/100)'
                else:
                    return f'*({number}/100)'

            # Replace patterns like 100+2%, 100-2%, 100*2%, 100/2%
            expr_mod = re.sub(r'([+\-*/])\s*(\d+(?:\.\d+)?)%', percent_replacer, expr_mod)
            # Also handle if expression starts with a number and percent, e.g. 2%
            expr_mod = re.sub(r'^(\d+(?:\.\d+)?)%', r'(\1/100)', expr_mod)

            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
            allowed_names.update({
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "pow": pow,
                "pi": math.pi,
                "e": math.e,
            })
            result = eval(expr_mod, {"__builtins__": {}}, allowed_names)
            self.last_answer = result
            self.result.setText(str(result))
        except Exception as e:
            self.result.setText(f"Error: {e}")

        # Do not save to history here; only on Enter

    def save_and_copy(self):
        result_text = self.result.text()
        expr = self.input.text()
        if result_text and not result_text.startswith("Error") and expr.strip():
            if not self.history or self.history[-1][0] != expr:
                self.history.append((expr, str(self.last_answer)))
                self.update_history_label()
        # Copy to clipboard
        if result_text and not result_text.startswith("Error"):
            QGuiApplication.clipboard().setText(result_text)
        # Hide window and focus previous app
        self.hide()

    def update_history_label(self):
        # Clear previous
        from PySide6.QtWidgets import QLabel
        for i in reversed(range(self.history_layout.count())):
            widget = self.history_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Add all history
        for e, a in self.history[-50:]:
            label = QLabel(f"{e} = {a}")
            label.setStyleSheet("color: #444; font-size: 14px; padding: 2px 0; font-family: 'Segoe UI', 'Liberation Sans', Arial, sans-serif;")
            self.history_layout.addWidget(label)


    def copy_and_focus(self):
        result_text = self.result.text()
        if result_text and not result_text.startswith("Error"):
            QGuiApplication.clipboard().setText(result_text)
        # Select all text for quick overwrite
        self.input.selectAll()

    def closeEvent(self, event):
        # Hide instead of closing
        event.ignore()
        self.hide()

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()


def start_hotkey_listener(win):
    # This runs in a background thread using pynput
    def on_press(key):
        try:
            if key == pynput_keyboard.Key.space and current_keys.get('alt', False):
                win.show_and_focus()
        except Exception:
            pass

    def on_release(key):
        if key == pynput_keyboard.Key.alt_l or key == pynput_keyboard.Key.alt_r:
            current_keys['alt'] = False

    def on_key_event(key, pressed):
        if key == pynput_keyboard.Key.alt_l or key == pynput_keyboard.Key.alt_r:
            current_keys['alt'] = pressed

    current_keys = {'alt': False}

    def listener_on_press(key):
        on_key_event(key, True)
        on_press(key)

    def listener_on_release(key):
        on_key_event(key, False)
        on_release(key)

    with pynput_keyboard.Listener(on_press=listener_on_press, on_release=listener_on_release) as listener:
        listener.join()

def main():
    app = QApplication(sys.argv)
    win = CalculatorWidget()
    win.hide()  # Start hidden

    # Start hotkey listener in a background thread
    t = threading.Thread(target=start_hotkey_listener, args=(win,), daemon=True)
    t.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
