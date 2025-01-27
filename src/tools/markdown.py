import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import re
from dataclasses import dataclass
from typing import List
from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token


def setup_markdown_tags(chat_display: ScrolledText, theme: dict = None):
    MarkdownProcessor(chat_display, theme).setup_markdown_tags()


def render_markdown(chat_display: ScrolledText, message, theme: dict = None):
    MarkdownProcessor(chat_display, theme).render_markdown(message)


def has_markdown_syntax(text):
    return MarkdownProcessor.has_markdown_syntax(text)


@dataclass
class StyleSpan:
    start: int
    end: int
    tag: str
    text: str


class MarkdownProcessor:
    MARKDOWN_PATTERNS = re.compile(
        r"""
        (?:(?<!\\)\*\*[^*]+\*\*)|             # bold
        (?:(?<!\\)__[^_]+__)|                 # bold with underscore
        (?:(?<!\\)\*[^*]+\*)|                 # italic
        (?:(?<!\\)_[^_]+_)|                   # italic with underscore
        (?:(?<!\\)`[^`]+`)|                   # inline code
        (?:(?<!\\)~~[^~]+~~)|                 # strikethrough
        ^\s*#{1,6}\s.+|                       # headers
        ^[-*_]{3,}\s*$|                       # horizontal rule
        ^\s*[-*+]\s+.+|                       # unordered list
        ^\s*\d+\.\s+.+|                       # ordered list
        ^>\s+.+|                              # blockquote
        ^\s*[-*]\s\[[xX ]\]\s+.+|             # task list
        \|[^|]+\|                             # table
        ^```[\s\S]+?^```                      # multiline code block
        """,
        re.MULTILINE | re.VERBOSE,
    )

    def __init__(self, chat_display: ScrolledText, theme: dict = None):
        self.chat_display = chat_display
        self.theme = theme or {
            "fg": "black",
            "input_bg": "white",
            "input_fg": "black",
        }

    @staticmethod
    def has_markdown_syntax(text):
        return bool(MarkdownProcessor.MARKDOWN_PATTERNS.search(text))

    @staticmethod
    def remove_markdown_code_blocks(text):
        def replace_markdown_block(match):
            # Extract content between ```markdown and ``` tags
            content = match.group(1).strip()
            # Remove any leading/trailing whitespace and newlines
            return content if content else ""

        # Regex pattern for ```markdown blocks
        pattern = re.compile(r"```markdown\s*([\s\S]*?)\s*```", re.MULTILINE)
        return pattern.sub(replace_markdown_block, text)

    def setup_markdown_tags(self):
        for level in range(1, 7):
            self.chat_display.tag_configure(
                f"h{level}",
                font=("Arial", 22 - level * 2, "bold"),
                foreground=self.theme["input_fg"],
                spacing3=10,
            )  # Add space after headers

        self.chat_display.tag_configure("bold", font=("Arial", 12, "bold"))
        self.chat_display.tag_configure("italic", font=("Arial", 12, "italic"))
        self.chat_display.tag_configure(
            "strike", overstrike=True, foreground=self.theme["input_fg"]
        )
        self.chat_display.tag_configure(
            "inline_code", font=("Courier", 10), background=self.theme["input_bg"]
        )
        self.chat_display.tag_configure(
            "code_block",
            font=("Courier", 10),
            background=self.theme["input_bg"],
            lmargin1=20,
            lmargin2=20,
            spacing1=10,  # Space before
            spacing3=10,
        )  # Space after

        # Configure list tags with proper indentation and spacing
        self.chat_display.tag_configure(
            "bullet_list", lmargin1=20, lmargin2=40, spacing1=2
        )
        self.chat_display.tag_configure(
            "numbered_list", lmargin1=20, lmargin2=40, spacing1=2
        )
        for i in range(1, 4):  # Support 3 levels of nesting
            self.chat_display.tag_configure(
                f"nested_list_{i}",
                lmargin1=20 + i * 20,
                lmargin2=40 + i * 20,
                spacing1=2,
            )

        self.chat_display.tag_configure(
            "blockquote",
            background=self.theme["input_bg"],
            lmargin1=20,
            lmargin2=20,
            spacing1=5,
            spacing3=5,
        )

        self.chat_display.tag_configure(
            "hr", background="gray", spacing1=10, spacing3=10
        )

        self.chat_display.tag_configure(
            "table", font=("Arial", 12), spacing1=5, spacing3=5
        )
        self.chat_display.tag_configure(
            "table_header", font=("Arial", 12, "bold"), spacing1=5, spacing3=5
        )

        self.chat_display.tag_configure("task_complete", foreground="green")
        self.chat_display.tag_configure("task_incomplete", foreground="red")

    def render_markdown(self, markdown):
        markdown = MarkdownProcessor.remove_markdown_code_blocks(markdown)
        lines = markdown.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Skip empty lines
            if not line:
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Headers
            if line.startswith("#"):
                count = len(line) - len(line.lstrip("#"))
                if count <= 6:
                    self.chat_display.insert(
                        tk.END, line.lstrip("#").strip() + "\n", f"h{count}"
                    )
                    i += 1
                    continue

            # Code blocks
            if line.startswith("```"):
                language = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    self.apply_syntax_highlighting("\n".join(code_lines), language)
                    self.chat_display.insert(tk.END, "\n", "code_block")
                i += 1
                continue

            # Blockquotes
            if line.startswith(">"):
                quote_lines = []
                while i < len(lines) and (
                    lines[i].startswith(">") or not lines[i].strip()
                ):
                    if lines[i].strip():
                        quote_lines.append(lines[i].lstrip("> "))
                    i += 1
                self.chat_display.insert(
                    tk.END, "\n".join(quote_lines) + "\n", "blockquote"
                )
                continue

            # Horizontal rules
            if re.match(r"^[-*_]{3,}$", line.strip()):
                self.chat_display.insert(tk.END, "_" * 60 + "\n", "hr")
                i += 1
                continue

            # Tables
            if "|" in line:
                table_lines = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                if table_lines:
                    self.render_table(table_lines)
                continue

            # Task lists
            task_match = re.match(r"^(\s*)[-*•] \[([xX ])\] (.+)$", line)
            if task_match:
                indent, check, content = task_match.groups()
                indent_level = len(indent) // 2  # Handle nested task lists

                # Determine tag for nesting and status
                nesting_tag = (
                    f"nested_list_{min(indent_level, 3)}"
                    if indent_level > 0
                    else "bullet_list"
                )
                status_tag = (
                    "task_complete" if check.lower() == "x" else "task_incomplete"
                )

                # Determine checkbox symbol
                checkbox = "☒ " if check.lower() == "x" else "☐ "

                # Insert the rendered task list
                self.chat_display.insert(
                    tk.END, " " * (indent_level * 2), nesting_tag
                )  # Handle nesting
                self.chat_display.insert(
                    tk.END, checkbox, status_tag
                )  # Render checkbox
                self.process_inline_formatting(
                    content
                )  # Process inline formatting for task text
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Lists
            list_match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.+)$", line)
            if list_match:
                indent, marker, content = list_match.groups()
                indent_level = len(indent) // 2

                if indent_level == 0:
                    tag = "bullet_list" if marker in "-*" else "numbered_list"
                else:
                    tag = f"nested_list_{min(indent_level, 3)}"

                prefix = "• " if marker in "-*" else f"{marker} "
                self.chat_display.insert(tk.END, prefix, tag)
                self.process_inline_formatting(content)
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Regular line with inline formatting
            self.process_inline_formatting(line)
            self.chat_display.insert(tk.END, "\n")
            i += 1

    def apply_syntax_highlighting(self, code, language):
        try:
            # Attempt to get the lexer for the specified language (case-insensitive)
            try:
                lexer = get_lexer_by_name(language.lower())
            except Exception:
                # Fallback to auto-detecting the language if the specified one fails
                lexer = guess_lexer(code)

            # Tokenize the code
            self.chat_display.insert(tk.END, "\n")
            start_index = self.chat_display.index(tk.INSERT)
            for token, text in lex(code, lexer):
                token_name = str(token)

                # Determine the tag for the token
                if token_name not in {"Token.Text.Whitespace", "Token.Text"}:
                    self.chat_display.insert(start_index, text, token_name)
                else:
                    self.chat_display.insert(start_index, text)

                # Update the start index
                start_index = self.chat_display.index(
                    f"{start_index} + {len(text)} chars"
                )
        except Exception as e:
            self.chat_display.insert(tk.INSERT, code)
            print(f"Error applying syntax highlighting: {e}")

    def process_inline_formatting(self, text):
        parts = []
        pos = 0
        current_text = ""

        while pos < len(text):
            if text[pos : pos + 2] == "**" and pos + 2 < len(text):
                end_pos = text.find("**", pos + 2)
                if end_pos != -1:
                    parts.append(("normal", current_text))
                    parts.append(("bold", text[pos + 2 : end_pos]))
                    current_text = ""
                    pos = end_pos + 2
                    continue
            elif (text[pos] in ["*", "_"]) and pos + 1 < len(text):
                marker = text[pos]
                end_pos = text.find(marker, pos + 1)
                if (
                    end_pos != -1
                    and not text[pos - 1 : pos].isalnum()
                    and not text[end_pos + 1 : end_pos + 2].isalnum()
                ):
                    parts.append(("normal", current_text))
                    parts.append(("italic", text[pos + 1 : end_pos]))
                    current_text = ""
                    pos = end_pos + 1
                    continue
            elif text[pos : pos + 1] == "`" and pos + 1 < len(text):
                end_pos = text.find("`", pos + 1)
                if end_pos != -1:
                    parts.append(("normal", current_text))
                    parts.append(("inline_code", text[pos + 1 : end_pos]))
                    current_text = ""
                    pos = end_pos + 1
                    continue
            elif text[pos : pos + 2] == "~~" and pos + 2 < len(text):
                end_pos = text.find("~~", pos + 2)
                if end_pos != -1:
                    parts.append(("normal", current_text))
                    parts.append(("strike", text[pos + 2 : end_pos]))
                    current_text = ""
                    pos = end_pos + 2
                    continue

            current_text += text[pos]
            pos += 1

        if current_text:
            parts.append(("normal", current_text))

        for style, content in parts:
            if style == "normal":
                self.chat_display.insert(tk.END, content)
            else:
                self.chat_display.insert(tk.END, content, style)

    def render_table(self, table_lines):
        # Process table data
        rows = []
        col_widths = []

        for line in table_lines:
            if not line.strip():
                continue
            # Split and clean cells
            cells = [cell.strip() for cell in line.split("|")]
            # Remove empty edge cells
            cells = [cell for cell in cells if cell]
            if not cells:
                continue

            rows.append(cells)
            # Update column widths
            if not col_widths:
                col_widths = [len(cell) for cell in cells]
            else:
                col_widths = [
                    max(curr, len(cell)) for curr, cell in zip(col_widths, cells)
                ]

        # Render table
        for i, row in enumerate(rows):
            if i == 1:  # Skip separator row
                continue

            tag = "table_header" if i == 0 else "table"

            # Create formatted row
            formatted_row = ""
            for cell, width in zip(row, col_widths):
                formatted_row += f"{cell.ljust(width)} | "

            self.chat_display.insert(tk.END, formatted_row + "\n", tag)

    def update_output(self, *args):
        markdown = self.input_text.get("1.0", tk.END)
        lines = markdown.split("\n")
        self.chat_display.delete("1.0", tk.END)

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Skip empty lines
            if not line:
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Headers
            if line.startswith("#"):
                count = len(line) - len(line.lstrip("#"))
                if count <= 6:
                    self.chat_display.insert(
                        tk.END, line.lstrip("#").strip() + "\n", f"h{count}"
                    )
                    i += 1
                    continue

            # Code blocks
            if line.startswith("```"):
                language = line[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    highlighted_code = self.apply_syntax_highlighting(
                        "\n".join(code_lines), language
                    )
                    self.chat_display.insert(
                        tk.END, highlighted_code + "\n", "code_block"
                    )
                i += 1
                continue

            # Blockquotes
            if line.startswith(">"):
                quote_lines = []
                while i < len(lines) and (
                    lines[i].startswith(">") or not lines[i].strip()
                ):
                    if lines[i].strip():
                        quote_lines.append(lines[i].lstrip("> "))
                    i += 1
                self.chat_display.insert(
                    tk.END, "\n".join(quote_lines) + "\n", "blockquote"
                )
                continue

            # Horizontal rules
            if re.match(r"^[-*_]{3,}$", line.strip()):
                self.chat_display.insert(tk.END, "_" * 60 + "\n", "hr")
                i += 1
                continue

            # Tables
            if "|" in line:
                table_lines = []
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                if table_lines:
                    self.render_table(table_lines)
                continue

            # Lists
            list_match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.+)$", line)
            if list_match:
                indent, marker, content = list_match.groups()
                indent_level = len(indent) // 2

                if indent_level == 0:
                    tag = "bullet_list" if marker in "-*" else "numbered_list"
                else:
                    tag = f"nested_list_{min(indent_level, 3)}"

                prefix = "• " if marker in "-*" else f"{marker} "
                self.chat_display.insert(tk.END, prefix, tag)
                self.process_inline_formatting(content)
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Task lists
            task_match = re.match(r"^[-*] \[([x ])\] (.+)$", line)
            if task_match:
                is_complete = task_match.group(1) == "x"
                tag = "task_complete" if is_complete else "task_incomplete"
                checkbox = "☒ " if is_complete else "☐ "
                self.chat_display.insert(tk.END, checkbox)
                self.process_inline_formatting(task_match.group(2))
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Regular line with inline formatting
            self.process_inline_formatting(line)
            self.chat_display.insert(tk.END, "\n")
            i += 1
