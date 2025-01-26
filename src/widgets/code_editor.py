# CodeView is borrowed and adapted from https://github.com/rdbende/chlorophyll/blob/main/chlorophyll/codeview.py

from __future__ import annotations
import inspect
import subprocess
import tempfile
import os
from contextlib import suppress
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from tkinter.font import Font
from typing import Any, Callable, Dict, Type, Union
import pygments
import pygments.lexer
import pygments.lexers
from pyperclip import copy
from tklinenums import TkLineNumbers

from ..tools import (
    configure_scrolled_text,
    get_button_config,
    get_scrollbar_style,
    parse_scheme,
    default_syntax_scheme,
)

LexerType = Union[Type[pygments.lexer.Lexer], pygments.lexer.Lexer]


class Scrollbar(ttk.Scrollbar):
    def __init__(self, root: CodeView, autohide: bool, *args, **kwargs) -> None:
        super().__init__(root, *args, **kwargs)
        self.autohide = autohide

    def set(self, low: str, high: str) -> None:
        if self.autohide:
            if float(low) <= 0.0 and float(high) >= 1.0:
                self.grid_remove()
            else:
                self.grid()
        super().set(low, high)


class CodeView(tk.Text):
    _w: str

    def __init__(
        self,
        root: tk.Misc,
        lexer: LexerType = pygments.lexers.TextLexer,
        color_scheme: (
            dict[str, dict[str, str | int]] | str | None
        ) = default_syntax_scheme,
        tab_width: int = 4,
        linenums_theme: Callable[[], tuple[str, str]] | tuple[str, str] | None = None,
        autohide_scrollbar: bool = False,
        **kwargs,
    ) -> None:
        self._frame = tk.Frame(root)
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(1, weight=1)

        kwargs.setdefault("wrap", "none")
        kwargs.setdefault("font", ("monospace", 11))

        linenum_justify = kwargs.pop("justify", "left")

        super().__init__(self._frame, undo=True, **kwargs)
        super().grid(row=0, column=1, sticky="nswe")

        self.tab_spaces = " " * tab_width
        self.tab_width = tab_width

        self._line_numbers = TkLineNumbers(
            self._frame,
            self,
            justify=linenum_justify,
            colors=linenums_theme,
            borderwidth=0,
        )
        self._vs = Scrollbar(
            self._frame,
            autohide=autohide_scrollbar,
            orient="vertical",
            command=self.yview,
        )
        self._hs = Scrollbar(
            self._frame,
            autohide=autohide_scrollbar,
            orient="horizontal",
            command=self.xview,
        )

        self._line_numbers.grid(row=0, column=0, sticky="ns")
        self._vs.grid(row=0, column=2, sticky="ns")
        self._hs.grid(row=1, column=1, sticky="we")

        super().configure(
            yscrollcommand=self.vertical_scroll,
            xscrollcommand=self.horizontal_scroll,
            tabs=Font(font=kwargs["font"]).measure(" " * tab_width),
        )

        contmand = "Command" if self._windowingsystem == "aqua" else "Control"

        super().bind(f"<{contmand}-c>", self._copy, add=True)
        super().bind(f"<{contmand}-v>", self._paste, add=True)
        super().bind(f"<{contmand}-a>", self._select_all, add=True)
        super().bind(f"<{contmand}-Shift-Z>", self.redo, add=True)
        super().bind("<<ContentChanged>>", self.scroll_line_update, add=True)
        super().bind("<Button-1>", self._line_numbers.redraw, add=True)
        super().bind("<Tab>", self._insert_tab_spaces)
        super().bind("<Shift-ISO_Left_Tab>", self._decrease_indentation)
        super().bind("<Return>", self._auto_indent)

        self._orig = f"{self._w}_widget"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._cmd_proxy)

        self.set_lexer(lexer)
        self._set_color_scheme(color_scheme)
        self._line_numbers.redraw()

    def _select_all(self, *_) -> str:
        self.tag_add("sel", "1.0", "end")
        self.mark_set("insert", "end")
        return "break"

    def redo(self, event: tk.Event | None = None) -> None:
        try:
            self.edit_redo()
        except tk.TclError:
            pass

    def _paste(self, *_):
        insert = self.index(f"@0,0 + {self.cget('height') // 2} lines")

        with suppress(tk.TclError):
            self.delete("sel.first", "sel.last")
            self.tag_remove("sel", "1.0", "end")
            self.insert("insert", self.clipboard_get())

        self.see(insert)

        return "break"

    def _copy(self, *_):
        text = self.get("sel.first", "sel.last")
        if not text:
            text = self.get("insert linestart", "insert lineend")

        copy(text)

        return "break"

    def _cmd_proxy(self, command: str, *args) -> Any:
        try:
            if command in {"insert", "delete", "replace"}:
                start_line = int(
                    str(self.tk.call(self._orig, "index", args[0])).split(".")[0]
                )
                end_line = start_line
                if len(args) == 3:
                    end_line = (
                        int(
                            str(self.tk.call(self._orig, "index", args[1])).split(".")[
                                0
                            ]
                        )
                        - 1
                    )
            result = self.tk.call(self._orig, command, *args)
        except tk.TclError as e:
            error = str(e)
            if 'tagged with "sel"' in error or "nothing to" in error:
                return ""
            raise e from None

        if command == "insert":
            if not args[0] == "insert":
                start_line -= 1
            lines = args[1].count("\n")
            if lines == 1:
                self.highlight_line(f"{start_line}.0")
            else:
                self.highlight_area(start_line, start_line + lines)
            self.event_generate("<<ContentChanged>>")
        elif command in {"replace", "delete"}:
            if start_line == end_line:
                self.highlight_line(f"{start_line}.0")
            else:
                self.highlight_area(start_line, end_line)
            self.event_generate("<<ContentChanged>>")

        return result

    def _setup_tags(self, tags: dict[str, str]) -> None:
        for key, value in tags.items():
            if isinstance(value, str):
                self.tag_configure(f"Token.{key}", foreground=value)

    def highlight_line(self, index: str) -> None:
        line_num = int(self.index(index).split(".")[0])
        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, f"{line_num}.0", f"{line_num}.end")

        line_text = self.get(f"{line_num}.0", f"{line_num}.end")
        start_col = 0

        for token, text in pygments.lex(line_text, self._lexer):
            token = str(token)
            end_col = start_col + len(text)
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, f"{line_num}.{start_col}", f"{line_num}.{end_col}")
            start_col = end_col

    def highlight_all(self) -> None:
        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, "1.0", "end")

        lines = self.get("1.0", "end")
        line_offset = lines.count("\n") - lines.lstrip().count("\n")
        start_index = str(
            self.tk.call(self._orig, "index", f"1.0 + {line_offset} lines")
        )

        for token, text in pygments.lex(lines, self._lexer):
            token = str(token)
            end_index = self.index(f"{start_index} + {len(text)} chars")
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, start_index, end_index)
            start_index = end_index

    def highlight_area(
        self, start_line: int | None = None, end_line: int | None = None
    ) -> None:
        for tag in self.tag_names(index=None):
            if tag.startswith("Token"):
                self.tag_remove(tag, f"{start_line}.0", f"{end_line}.end")

        text = self.get(f"{start_line}.0", f"{end_line}.end")
        line_offset = text.count("\n") - text.lstrip().count("\n")
        start_index = str(
            self.tk.call(self._orig, "index", f"{start_line}.0 + {line_offset} lines")
        )
        for token, text in pygments.lex(text, self._lexer):
            token = str(token)
            end_index = self.index(f"{start_index} + {len(text)} indices")
            if token not in {"Token.Text.Whitespace", "Token.Text"}:
                self.tag_add(token, start_index, end_index)
            start_index = end_index

    def _set_color_scheme(
        self, color_scheme: dict[str, dict[str, str | int]] | str | None
    ) -> None:
        assert isinstance(
            color_scheme, dict
        ), "Must be a dictionary or a built-in color scheme"

        tags = parse_scheme(color_scheme)
        self._setup_tags(tags)

        self.highlight_all()

    def set_lexer(self, lexer: LexerType) -> None:
        self._lexer = lexer() if inspect.isclass(lexer) else lexer
        self.highlight_all()

    def __setitem__(self, key: str, value) -> None:
        self.configure(**{key: value})

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def configure(self, **kwargs) -> None:
        super().configure(**kwargs)

    config = configure

    def pack(self, *args, **kwargs) -> None:
        self._frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs) -> None:
        self._frame.grid(*args, **kwargs)

    def place(self, *args, **kwargs) -> None:
        self._frame.place(*args, **kwargs)

    def pack_forget(self) -> None:
        self._frame.pack_forget()

    def grid_forget(self) -> None:
        self._frame.grid_forget()

    def place_forget(self) -> None:
        self._frame.place_forget()

    def destroy(self) -> None:
        for widget in self._frame.winfo_children():
            tk.BaseWidget.destroy(widget)
        tk.BaseWidget.destroy(self._frame)

    def horizontal_scroll(self, first: str | float, last: str | float) -> CodeView:
        self._hs.set(first, last)

    def vertical_scroll(self, first: str | float, last: str | float) -> CodeView:
        self._vs.set(first, last)
        self._line_numbers.redraw()

    def scroll_line_update(self, event: tk.Event | None = None) -> CodeView:
        self.horizontal_scroll(*self.xview())
        self.vertical_scroll(*self.yview())

    def undo(self, event=None):
        """Undo the most recent action."""
        self.edit_undo()
        return "break"

    def _insert_tab_spaces(self, event):
        """Replace Tab key with spaces."""
        self.insert(tk.INSERT, self.tab_spaces)
        return "break"

    def _decrease_indentation(self, event):
        """Handle Shift+Tab to remove spaces from the start of the current line."""
        line_start = self.index("insert linestart")
        line_end = self.index("insert lineend")
        current_line = self.get(line_start, line_end)

        # Check if the line starts with spaces and remove up to `tab_size` spaces
        if current_line.startswith(" "):
            spaces_to_remove = min(
                self.tab_width, len(current_line) - len(current_line.lstrip(" "))
            )
            new_line = current_line[spaces_to_remove:]
            self.delete(line_start, line_end)
            self.insert(line_start, new_line)
            self.mark_set("insert", f"{line_start}+{len(new_line)}c")

        return "break"

    def _auto_indent(self, event):
        """Auto-indent the next line to match the current line's indentation."""
        current_line = self.get("insert linestart", "insert")
        indentation = len(current_line) - len(current_line.lstrip(" "))
        self.insert(tk.INSERT, "\n" + " " * indentation)
        return "break"


class CodeEditorWindow(tk.Toplevel):
    """Actual window to edit and run code."""

    def __init__(self, parent, theme, code=None, tab_size=4):
        super().__init__(parent)
        self.title("Code Editor")

        # Store tab size
        self.tab_size = tab_size
        self.tab_spaces = " " * tab_size

        # Supported languages and their respective lexers
        self.languages = {
            "Python": pygments.lexers.PythonLexer,
            "Rust": pygments.lexers.RustLexer,
        }
        self.selected_language = tk.StringVar(value="Python")  # Default to Python

        # Frame to hold code_text, run_button, and output_text
        self.text_frame = tk.Frame(self)
        self.text_frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Dropdown for selecting language
        self.language_menu = tk.OptionMenu(
            self.text_frame,
            self.selected_language,
            *self.get_mainstream_languages(),
            command=self.update_language,
        )
        self.language_menu.pack(side="top", anchor="w", pady=(0, 5))

        # Frame to hold line numbers and code_text
        self.code_frame = tk.Frame(self.text_frame)
        self.code_frame.pack(side="top", expand=True, fill="both", pady=(0, 5), padx=5)

        self.code_text = CodeView(root=self.code_frame)
        self.code_text.pack(side="right", fill="both", expand=True)

        # Button to run the code (middle portion)
        self.run_button = tk.Button(
            self.text_frame, text="Run Code", command=self.run_code
        )
        self.run_button.pack(pady=10)

        self.output_text = scrolledtext.ScrolledText(
            self.text_frame, wrap=tk.WORD, state="disabled", height=10
        )
        self.output_text.pack(side="top", fill="x", padx=5)

        self.bind("<Escape>", lambda _: self.destroy())

        if code:
            self.code_text.insert(tk.INSERT, code)

        self.code_text.focus_set()

        self.update_language()
        self.update_run_button_state()
        self.apply_theme(theme)

    def get_mainstream_languages(self):
        mainstream_lexers = [
            # Programming Languages
            "Python",
            "JavaScript",
            "Java",
            "C",
            "C++",
            "C#",
            "Ruby",
            "PHP",
            "Swift",
            "Kotlin",
            "Go",
            "Rust",
            "TypeScript",
            "Scala",
            "Perl",
            "R",
            "MATLAB",
            "Shell",
            "Bash",
            "PowerShell",
            # Web Languages
            "HTML",
            "CSS",
            "XML",
            "JSON",
            # Markup and Text
            "Markdown",
            "reStructuredText",
            "LaTeX",
            "Plain Text",
            # Scripting Languages
            "Lua",
            "Tcl",
            "Erlang",
            "Elixir",
            # Functional Languages
            "Haskell",
            "Clojure",
            "F#",
            # Data Languages
            "SQL",
            "YAML",
            "INI",
        ]

        return [
            lexer_info[0]
            for lexer_info in pygments.lexers.get_all_lexers()
            if lexer_info[0] in mainstream_lexers
        ]

    def update_language(self, event=None):
        """Update the lexer and highlight syntax based on the selected language."""
        selected_language = self.selected_language.get()

        # Find the corresponding lexer class
        try:
            lexer = pygments.lexers.get_lexer_by_name(selected_language)
            self.highlight_syntax(lexer=lexer)
        except Exception:
            # Fallback to default lexer if not found
            self.highlight_syntax()

        # Update run button state
        self.update_run_button_state()

    def update_run_button_state(self):
        """Enable run button only for supported languages."""
        selected_language = self.selected_language.get()

        # Check if the selected language is in supported languages
        if selected_language in self.languages:
            self.run_button.config(state=tk.NORMAL)
        else:
            self.run_button.config(state=tk.DISABLED)
            # Optionally, show a tooltip or message about unsupported language
            self.output_text.config(state="normal")
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(
                tk.INSERT, f"Running code is not supported for {selected_language}"
            )
            self.output_text.config(state="disabled")

    def run_code(self):
        code = self.code_text.get("1.0", tk.END).strip()
        selected_language = self.selected_language.get()

        # Define the command for each language
        commands = {
            "Python": ["python3", "-c", code],
            "Rust": ["rustc", "-"],
        }

        if not code:
            messagebox.showwarning("Warning", "Code cannot be empty!")
            return

        # Run the code using subprocess
        try:
            if selected_language == "Rust":
                output = run_rust_code(code)
            else:
                result = subprocess.run(
                    commands[selected_language],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                output = result.stdout
        except subprocess.CalledProcessError as e:
            output = e.stderr
        except Exception as e:
            output = str(e)

        # Update the output text widget
        self.output_text.pack(side="top", fill="x", padx=5)  # Show output
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.INSERT, output)
        self.output_text.config(state="disabled")

    def highlight_syntax(self, lexer=pygments.lexers.PythonLexer()):
        self.code_text.set_lexer(lexer)

    def apply_theme(self, theme: Dict):
        self.config(bg=theme["bg"], borderwidth=1, relief="solid")
        self.text_frame.configure(bg=theme["bg"])
        self.code_frame.configure(bg=theme["bg"])

        editor_schema = {
            "background": theme["input_bg"],
            "foreground": theme["input_fg"],
            "selectbackground": theme["list_select_bg"],
            "selectforeground": theme["list_select_fg"],
            "inactiveselectbackground": theme["list_bg"],
            "insertbackground": "#f9ae58",
            "insertwidth": "1",
            "borderwidth": "0",
            "highlightthickness": "0",
        }
        self.code_text.configure(**editor_schema)
        self.code_text._frame.configure(bg=theme["input_bg"])
        get_scrollbar_style(theme)
        self.code_text._hs.configure(style="Horizontal.CustomScrollbar.TScrollbar")
        self.code_text._vs.configure(style="Vertical.CustomScrollbar.TScrollbar")

        configure_scrolled_text(self.output_text, theme)
        self.output_text.configure(bg=theme["input_bg"], fg=theme["input_fg"])

        self.language_menu.configure(
            width=12,  # Set the width (number of characters)
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            activebackground=theme["input_bg"],
            activeforeground=theme["input_fg"],
            borderwidth=0,
        )
        self.language_menu["menu"].configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            activebackground=theme["input_bg"],
            activeforeground=theme["input_fg"],
            borderwidth=1,
            relief="flat",
        )

        self.run_button.configure(**get_button_config(theme))


def run_rust_code(code):
    # Create a temporary file for Rust code
    with tempfile.NamedTemporaryFile(delete=False, suffix=".rs") as temp_file:
        temp_file.write(code.encode("utf-8"))
        temp_file_path = temp_file.name

    binary_path = temp_file_path.replace(".rs", "")

    # Compile the Rust code
    compile_result = subprocess.run(
        ["rustc", temp_file_path, "-o", binary_path],
        capture_output=True,
        text=True,
        timeout=20,  # Add timeout to prevent hanging
    )
    if compile_result.returncode != 0:
        output = compile_result.stderr
    else:

        run_result = subprocess.run(
            [binary_path],
            capture_output=True,
            text=True,
            timeout=10,  # Add timeout for execution
        )
        output = run_result.stdout if run_result.returncode == 0 else run_result.stderr

    # Cleanup the temporary files
    os.remove(temp_file_path)
    if os.path.exists(binary_path):
        os.remove(binary_path)

    return output
