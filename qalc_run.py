
import sys
import math
import threading
from pynput import keyboard as pynput_keyboard
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QLabel
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QGuiApplication

class CalculatorWidget(QWidget):
    def insert_bracket_pair(self):
        # Insert () and move cursor between them in the input field
        cursor_pos = self.input.cursorPosition()
        text = self.input.text()
        new_text = text[:cursor_pos] + '()' + text[cursor_pos:]
        self.input.setText(new_text)
        self.input.setCursorPosition(cursor_pos + 1)

    def keyPressEvent(self, event):
        # Ctrl+L to clear input
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_L:
            self.input.clear()
            return
        # Only handle ( key in the input field
        if self.input.hasFocus() and event.text() == '(':  # Shift+9
            self.insert_bracket_pair()
            return
        super().keyPressEvent(event)
    def bracket_suggestion(self, text):
        # Returns suggestion string if brackets are unbalanced, else empty
        open_count = text.count('(')
        close_count = text.count(')')
        if open_count > close_count:
            n = open_count - close_count
            return f"Suggestion: add {n} closing bracket{'s' if n > 1 else ''}."
        return ""
    def suggest_correction(self, expr, error_msg):
        import re
        # Very basic suggestions for common mistakes
        suggestions = []
        if 'unexpected EOF' in error_msg or 'parenthesis' in error_msg:
            suggestions.append("Check for missing parenthesis.")
        if 'name' in error_msg:
            suggestions.append("Check for typos in function or variable names.")
        if '%' in expr and not re.search(r'[+\-*/]\s*\d+%', expr):
            suggestions.append("Did you mean to use e.g. 100+2% or 100*2%?")
        if expr.strip().endswith(('+', '-', '*', '/')):
            suggestions.append("Expression ends with an operator. Remove or complete it.")
        if not suggestions:
            suggestions.append("Check your expression for typos or syntax errors.")
        return ' '.join(suggestions)
    def event(self, event):
        # Hide window when focus is lost (i.e., user switches to another window)
        if event.type() == QEvent.WindowDeactivate:
            self.hide()
        return super().event(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qalc-Run: Calculator")
        self.resize(400, 540)
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
                font-size: 22px;
            }
            QLabel#ResultLabel {
                padding: 10px;
                border-radius: 6px;
                background: #e9f5e9;
                color: #217a3c;
                font-weight: bold;
                font-size: 26px;
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
            QPushButton {
                background: #fff;
                border: 1px solid #bbb;
                border-radius: 6px;
                font-size: 20px;
                padding: 12px 0;
                min-width: 0;
                min-height: 0;
            }
            QPushButton:pressed {
                background: #e9f5e9;
            }
        """)

        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QScrollArea, QWidget
        main_layout = QVBoxLayout()

        # Display area
        self.display = QLineEdit()
        self.display.setPlaceholderText("Enter calculation or use keypad...")
        self.display.setObjectName("InputField")
        self.display.returnPressed.connect(self.save_and_copy)
        self.display.textChanged.connect(self.calculate)
        main_layout.addWidget(self.display)

        # Result area
        self.result = QLabel("")
        self.result.setObjectName("ResultLabel")
        self.result.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.result)

        # Info label
        self.info = QLabel("Use %, ans, pi, e, min, max, pow, round. Example: 11+11% or ans*2")
        self.info.setObjectName("InfoLabel")
        self.info.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info)

        # ...no keypad...

        # History area (scrollable)
        self.history_area = QScrollArea()
        self.history_area.setWidgetResizable(True)
        self.history_area.setStyleSheet("")
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setAlignment(Qt.AlignTop)
        self.history_widget.setLayout(self.history_layout)
        self.history_area.setWidget(self.history_widget)
        main_layout.addWidget(self.history_area, stretch=1)

        self.setLayout(main_layout)
        self.last_answer = 0
        self.history = []

    # ...no keypad handler...

    # For compatibility with old code
    @property
    def input(self):
        return self.display

    def calculate(self):
        expr = self.input.text()
        if not expr.strip():
            self.result.setText("")
            self.info.setText("Use %, ans, pi, e, min, max, pow, round. Example: 11+11% or ans*2")
            return
        # Show bracket suggestion if needed (in info label)
        suggestion = self.bracket_suggestion(expr)
        if suggestion:
            self.info.setText(suggestion)
        else:
            self.info.setText("Use %, ans, pi, e, min, max, pow, round. Example: 11+11% or ans*2")
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
            # Syntax highlighting: green for valid
            self.input.setStyleSheet(self.input.styleSheet() + "QLineEdit { background: #e9f5e9; color: #222; }")
        except Exception as e:
            # Syntax highlighting: red for error
            self.input.setStyleSheet(self.input.styleSheet() + "QLineEdit { background: #ffeaea; color: #a33; }")
            simple_msg = self.simplify_error(str(e))
            self.result.setText(simple_msg)

        # Do not save to history here; only on Enter
    def simplify_error(self, msg):
        # Map common Python/math errors to short, simple language
        msg = msg.lower()
        if 'unexpected eof' in msg or 'parenthesis' in msg or 'unmatched' in msg:
            return "Missing parenthesis."
        if 'name' in msg and 'not defined' in msg:
            return "Unknown name."
        if 'division by zero' in msg:
            return "Divide by zero."
        if 'invalid syntax' in msg:
            return "Syntax error."
        if 'math domain error' in msg:
            return "Math error."
        if 'unsupported operand' in msg:
            return "Bad operator or value."
        if 'float' in msg and 'cannot be interpreted' in msg:
            return "Bad number."
        # fallback
        return "Can't calculate."

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
        # Clear any error/suggestion and reset input highlight
        self.result.setText("")
        self.input.setStyleSheet(self.input.styleSheet().replace("QLineEdit { background: #ffeaea; color: #a33; }", "QLineEdit { background: #fff; color: #222; }"))


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
