import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from typing import Dict
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token
import subprocess
from ..tools import configure_scrolled_text, get_button_config


class CodeEditorWindow(tk.Toplevel):
    def __init__(self, parent, theme, code):
        super().__init__(parent)
        self.title("Code Editor")

        # Frame to hold code_text, run_button, and output_text
        self.text_frame = tk.Frame(self)  # Assign to self.text_frame for styling
        self.text_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # ScrolledText for editing code (top portion)
        self.code_text = scrolledtext.ScrolledText(
            self.text_frame, wrap=tk.WORD, undo=True
        )
        self.code_text.pack(side="top", expand=True, fill="both", pady=(0, 5), padx=5)
        self.code_text.insert(tk.INSERT, code)

        # Button to run the code (middle portion)
        self.run_button = tk.Button(
            self.text_frame, text="Run Code", command=self.run_code
        )
        self.run_button.pack(pady=10)

        # ScrolledText for displaying output (bottom portion)
        self.output_text = scrolledtext.ScrolledText(
            self.text_frame, wrap=tk.WORD, state="disabled", height=10
        )
        self.output_text.pack(side="top", fill="x", padx=5)

        self.code_text.bind("<KeyRelease>", self.highlight_syntax)

        self.highlight_syntax()
        self.apply_theme(theme)

    def run_code(self):
        code = self.code_text.get("1.0", tk.END)

        # Run the code using subprocess
        try:
            result = subprocess.run(
                ["python3", "-c", code], capture_output=True, text=True, check=True
            )
            output = result.stdout
        except subprocess.CalledProcessError as e:
            output = e.stderr
        except Exception as e:
            output = str(e)

        # Update the output text widget
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.INSERT, output)
        self.output_text.config(state="disabled")

    def highlight_syntax(self, event=None):
        """Apply syntax highlighting to the code_text widget."""
        code = self.code_text.get("1.0", tk.END)
        self.code_text.mark_set("range_start", "1.0")

        # Remove all previous syntax tags
        self.code_text.tag_remove("keyword", "1.0", tk.END)
        self.code_text.tag_remove("builtin", "1.0", tk.END)
        self.code_text.tag_remove("string", "1.0", tk.END)
        self.code_text.tag_remove("comment", "1.0", tk.END)

        # Process code with Pygments
        for token, content in lex(code, PythonLexer()):
            self.code_text.mark_set("range_end", f"range_start + {len(content)}c")

            if token in Token.Keyword:
                self.code_text.tag_add("keyword", "range_start", "range_end")
            elif token in Token.Name.Builtin:
                self.code_text.tag_add("builtin", "range_start", "range_end")
            elif token in Token.Literal.String:
                self.code_text.tag_add("string", "range_start", "range_end")
            elif token in Token.Comment:
                self.code_text.tag_add("comment", "range_start", "range_end")

            # Move the range start marker
            self.code_text.mark_set("range_start", "range_end")

        # Define the styles (colors and fonts) for each token type
        self.code_text.tag_configure(
            "keyword", foreground="#81a1c1", font=("Courier", 12, "bold")
        )
        self.code_text.tag_configure(
            "builtin", foreground="darkorange", font=("Courier", 12)
        )
        self.code_text.tag_configure(
            "string", foreground="green", font=("Courier", 12, "italic")
        )
        self.code_text.tag_configure(
            "comment", foreground="gray", font=("Courier", 12, "italic")
        )

    def apply_theme(self, theme: Dict):
        self.config(bg=theme["bg"], borderwidth=1, relief="solid")
        self.text_frame.configure(bg=theme["bg"])

        for scrolled_text in [self.code_text, self.output_text]:
            configure_scrolled_text(scrolled_text, theme)
            scrolled_text.configure(bg=theme["input_bg"], fg=theme["input_fg"])

        self.run_button.configure(**get_button_config(theme))
