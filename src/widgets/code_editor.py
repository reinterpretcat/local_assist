import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from typing import Dict
from pygments import lex
from pygments.lexers import PythonLexer
from pygments.token import Token
import subprocess
from ..tools import configure_scrolled_text, get_button_config


class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, *args):
        """redraw line numbers"""
        self.delete("all")

        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(
                2, y, anchor="nw", text=linenum, fill=self.foreground_color
            )
            i = self.textwidget.index("%s+1line" % i)


class CustomScrolledText(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        # let the actual widget perform the requested action
        cmd = (self._orig,) + args
        result = self.tk.call(cmd)

        # generate an event if something was added or deleted,
        # or the cursor position changed
        if (
            args[0] in ("insert", "replace", "delete")
            or args[0:3] == ("mark", "set", "insert")
            or args[0:2] == ("xview", "moveto")
            or args[0:2] == ("xview", "scroll")
            or args[0:2] == ("yview", "moveto")
            or args[0:2] == ("yview", "scroll")
        ):
            self.event_generate("<<Change>>", when="tail")

        # return what the actual widget returned
        return result


class CodeEditorWindow(tk.Toplevel):
    def __init__(self, parent, theme, code):
        super().__init__(parent)
        self.title("Code Editor")

        # Frame to hold code_text, run_button, and output_text
        self.text_frame = tk.Frame(self)
        self.text_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Frame to hold line numbers and code_text
        self.code_frame = tk.Frame(self.text_frame)
        self.code_frame.pack(side="top", expand=True, fill="both", pady=(0, 5), padx=5)

        self.code_text = CustomScrolledText(self.code_frame, undo=True)
        self.code_text.vbar = tk.Scrollbar(
            self.code_frame, orient="vertical", command=self.code_text.yview
        )
        self.code_text.configure(yscrollcommand=self.code_text.vbar.set)
        self.line_numbers = TextLineNumbers(self.code_frame, width=90)
        self.line_numbers.attach(self.code_text)

        self.code_text.vbar.pack(side="right", fill="y")
        self.line_numbers.pack(side="left", fill="y")
        self.code_text.pack(side="right", fill="both", expand=True)

        def on_change(event):
            self.line_numbers.redraw()

        self.code_text.bind("<<Change>>", on_change)
        self.code_text.bind("<Configure>", on_change)
        self.code_text.bind("<Control-a>", self.select_all)
        self.code_text.bind("<Control-z>", self.undo)
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

        self.bind("<Escape>", lambda _: self.destroy())

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

    def select_all(self, event=None):
        """Select all text in the code text widget."""
        self.code_text.tag_add("sel", "1.0", "end")
        return "break"

    def undo(self, event=None):
        """Undo the most recent action."""
        self.code_text.edit_undo()
        return "break"

    def apply_theme(self, theme: Dict):
        self.config(bg=theme["bg"], borderwidth=1, relief="solid")
        self.text_frame.configure(bg=theme["bg"])
        self.code_frame.configure(bg=theme["bg"])

        self.line_numbers.config(background=theme["input_bg"], borderwidth=0)
        self.line_numbers.foreground_color = theme["input_fg"]
        self.line_numbers.config(
            highlightbackground=theme["input_bg"], highlightcolor=theme["input_bg"]
        )

        for scrolled_text in [self.code_text, self.output_text]:
            configure_scrolled_text(scrolled_text, theme)
            scrolled_text.configure(bg=theme["input_bg"], fg=theme["input_fg"])

        self.run_button.configure(**get_button_config(theme))
