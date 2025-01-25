import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from typing import Dict
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

    def apply_theme(self, theme: Dict):
        self.config(bg=theme["bg"], borderwidth=1, relief="solid")
        self.text_frame.configure(bg=theme["bg"])

        for scrolled_text in [self.code_text, self.output_text]:
            configure_scrolled_text(scrolled_text, theme)
            scrolled_text.configure(bg=theme["input_bg"], fg=theme["input_fg"])

        self.run_button.configure(**get_button_config(theme))
