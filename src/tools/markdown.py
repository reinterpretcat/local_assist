import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import re
from dataclasses import dataclass
from typing import List


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
        r"(^#{1,6}\s.+$)|"  # Headers (e.g., # Header 1)
        r"(^[-*]\s.+$)|"  # Bullet lists (e.g., - Item)
        r"(^\d+\.\s.+$)|"  # Ordered lists (e.g., 1. Item)
        r"(\|.+\|)|"  # Tables (e.g., | Col1 | Col2 |)
        r"(^[-*_]{3,}$)|"  # Horizontal rules (e.g., ---)
        r"(^> .+$)|"  # Blockquotes (e.g., > Quote)
        r"(`.+?`)|"  # Inline code (e.g., `code`)
        r"(\*\*.+?\*\*)|"  # Bold text (e.g., **bold**)
        r"(\*.+?\*)|"  # Italic text (e.g., *italic*)
        r"(~~.+?~~)|"  # Strikethrough text (e.g., ~~strike~~)
        r"(^```.*?```$)|"  # Multiline code blocks (e.g., ``` code ```)
        r"(^- \[([ x])\] .+$)",  # Task lists (e.g., - [x] Task)
        re.MULTILINE | re.DOTALL,  # Support multiline and dotall mode
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

    def setup_markdown_tags(self):
        # Basic styles
        self.chat_display.tag_configure(
            "bold", font=("Arial", 12, "bold"), foreground=self.theme["fg"]
        )
        self.chat_display.tag_configure(
            "italic", font=("Arial", 12, "italic"), foreground=self.theme["fg"]
        )
        self.chat_display.tag_configure(
            "strike", overstrike=1, foreground=self.theme["fg"]
        )
        self.chat_display.tag_configure(
            "code",
            font=("Courier", 12),
            background=self.theme["input_bg"],
            foreground=self.theme["input_fg"],
        )

        # Headers
        for i in range(1, 7):
            size = 20 - (i * 2)
            self.chat_display.tag_configure(
                f"h{i}", font=("Arial", size, "bold"), foreground=self.theme["fg"]
            )

        # Code blocks
        self.chat_display.tag_configure(
            "codeblock",
            font=("Courier", 12),
            background=self.theme["input_bg"],
            foreground=self.theme["input_fg"],
            spacing1=10,
            spacing3=10,
            lmargin1=20,
            lmargin2=20,
        )

        # Lists
        self.chat_display.tag_configure(
            "bullet", lmargin1=20, lmargin2=40, foreground=self.theme["fg"]
        )
        self.chat_display.tag_configure(
            "ordered", lmargin1=20, lmargin2=40, foreground=self.theme["fg"]
        )

        # Blockquote
        self.chat_display.tag_configure(
            "blockquote",
            lmargin1=20,
            lmargin2=20,
            background=self.theme["input_bg"],
            foreground=self.theme["input_fg"],
            spacing1=5,
            spacing3=5,
        )

        # Table tags
        self.chat_display.tag_configure(
            "table", spacing1=5, spacing3=5, foreground=self.theme["fg"]
        )
        self.chat_display.tag_configure(
            "th",
            font=("Arial", 12, "bold"),
            background=self.theme["input_bg"],
            foreground=self.theme["input_fg"],
        )
        self.chat_display.tag_configure(
            "td", font=("Arial", 12), foreground=self.theme["fg"]
        )

        # Task list
        self.chat_display.tag_configure("task-done", foreground=self.theme["fg"])
        self.chat_display.tag_configure("task-pending", foreground=self.theme["fg"])

        # Horizontal rule
        self.chat_display.tag_configure(
            "hr",
            font=("Arial", 1),
            spacing1=10,
            spacing3=10,
            background=self.theme["input_bg"],
        )

    def process_block_with_styles(self, text: str, tag: str):
        """Helper to apply a block tag and then process inline styles."""
        start_idx = self.chat_display.index(tk.END)
        self.process_inline_styles(text)
        end_idx = self.chat_display.index(f"{start_idx} lineend")
        self.chat_display.tag_add(tag, start_idx, end_idx)

    def render_markdown(self, text):
        if not MarkdownProcessor.has_markdown_syntax(text):
            self.chat_display.insert(tk.END, text + "\n")
            return

        # Remove ```markdown wrapper if present
        text = re.sub(r"```markdown\n(.*?)\n```", r"\1", text, flags=re.DOTALL)

        current_state = self.chat_display.cget("state")
        self.chat_display.config(state=tk.NORMAL)

        lines = text.split("\n")
        i = 0
        in_table = False
        table_data = []

        while i < len(lines):
            line = lines[i].rstrip()

            # Empty line ends current context
            if not line:
                if in_table:
                    self.render_table(table_data)
                    table_data = []
                    in_table = False
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            # Code blocks
            if line.startswith("```"):
                i = self.handle_code_block(lines, i)
                continue

            # Tables
            if "|" in line:
                if not in_table:
                    in_table = True
                table_data.append(line)
                i += 1
                continue

            # Headers
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                content = header_match.group(2).strip()
                self.chat_display.insert(tk.END, f"{content}\n", f"h{level}")
                i += 1
                continue

            # Blockquotes
            if line.startswith("> "):
                content = line[2:].strip()
                blockquote_lines = [content]
                while i + 1 < len(lines) and lines[i + 1].startswith("> "):
                    i += 1
                    blockquote_lines.append(lines[i][2:].strip())
                full_quote = " ".join(blockquote_lines)
                self.chat_display.insert(tk.END, f"{full_quote}\n", "blockquote")
                i += 1
                continue

            # Task lists
            task_match = re.match(r"^- \[([ x])\] (.+)$", line)
            if task_match:
                done = task_match.group(1) == "x"
                tag = "task-done" if done else "task-pending"
                checkbox = "☑ " if done else "☐ "
                self.chat_display.insert(tk.END, checkbox)
                content = task_match.group(2).strip()
                self.chat_display.insert(tk.END, f"{content}\n", tag)
                i += 1
                continue

            # Handle other existing patterns...
            ordered_match = re.match(r"^(\d+\.\s)(.+)$", line)
            if ordered_match:
                self.chat_display.insert(tk.END, ordered_match.group(1))
                self.process_inline_styles(ordered_match.group(2))
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue


            if re.match(r"^([-*_])\1{2,}$", line):
                self.chat_display.insert(tk.END, "─" * 40 + "\n", "hr")
                i += 1
                continue

            bullet_match = re.match(r"^[-*]\s(.+)$", line)
            if bullet_match:
                self.chat_display.insert(tk.END, "• ")
                self.process_inline_styles(bullet_match.group(1))
                self.chat_display.insert(tk.END, "\n")
                i += 1
                continue

            self.process_inline_styles(line)
            self.chat_display.insert(tk.END, "\n")
            i += 1

        if in_table:
            self.render_table(table_data)

        self.chat_display.config(state=current_state)

    def find_markdown_spans(self, text: str) -> List[StyleSpan]:
        spans = []
        markers = []

        # Bold markers
        for match in re.finditer(r"\*\*", text):
            markers.append((match.start(), match.end(), "bold"))

        # Italic markers
        for match in re.finditer(r"(?<!\*)\*(?!\*)", text):
            markers.append((match.start(), match.end(), "italic"))

        # Code markers
        for match in re.finditer(r"`", text):
            markers.append((match.start(), match.end(), "code"))

        # Strike markers
        for match in re.finditer(r"~~", text):
            markers.append((match.start(), match.end(), "strike"))

        # Headers
        for match in re.finditer(r"^(#{1,6})\s", text):
            level = len(match.group(1))
            markers.append((match.start(), match.end(), f"h{level}"))

        # Blockquotes
        for match in re.finditer(r"^>\s", text):
            markers.append((match.start(), match.end(), "blockquote"))

        # Task lists
        for match in re.finditer(r"^- \[([ x])\]\s", text):
            is_done = match.group(1) == "x"
            tag = "task-done" if is_done else "task-pending"
            markers.append((match.start(), match.end(), tag))

        # Bullet lists
        for match in re.finditer(r"^[-*]\s", text):
            markers.append((match.start(), match.end(), "bullet"))

        # Ordered lists
        for match in re.finditer(r"^\d+\.\s", text):
            markers.append((match.start(), match.end(), "ordered"))

        # Sort all markers by position
        markers.sort(key=lambda x: x[0])

        # Match opening and closing markers for paired styles
        stack = []
        for marker in markers:
            pos_start, pos_end, style = marker

            # Paired styles (bold, italic, code, strike)
            if style in ["bold", "italic", "code", "strike"]:
                if not stack:
                    stack.append(marker)
                else:
                    last_marker = stack[-1]
                    if last_marker[2] == style:
                        opening_end = last_marker[1]
                        content = text[opening_end:pos_start]
                        spans.append(
                            StyleSpan(
                                start=last_marker[0],
                                end=pos_end,
                                tag=style,
                                text=content,
                            )
                        )
                        stack.pop()
                    else:
                        stack.append(marker)
            # Block-level styles (apply to whole line)
            else:
                end_pos = (
                    len(text)
                    if "\n" not in text[pos_end:]
                    else text.index("\n", pos_end)
                )
                content = text[pos_end:end_pos].strip()
                spans.append(
                    StyleSpan(start=pos_start, end=end_pos, tag=style, text=content)
                )

        spans.sort(key=lambda x: x.start)
        return spans

    def process_inline_styles(self, text: str) -> str:
        if not text:
            return ""

        spans = self.find_markdown_spans(text)
        if not spans:
            self.chat_display.insert(tk.END, text)
            return ""

        last_pos = 0
        for span in spans:
            if span.start > last_pos:
                plain_text = text[last_pos : span.start]
                self.chat_display.insert(tk.END, plain_text)

            self.chat_display.insert(tk.END, span.text, span.tag)
            last_pos = span.end

        if last_pos < len(text):
            remaining_text = text[last_pos:]
            self.chat_display.insert(tk.END, remaining_text)

        return ""

    def handle_code_block(self, lines, start_idx):
        code_content = []
        i = start_idx + 1

        while i < len(lines) and not lines[i].startswith("```"):
            code_content.append(lines[i])
            i += 1

        code_text = "\n".join(code_content)
        self.chat_display.insert(tk.END, code_text + "\n", "codeblock")

        return i + 1 if i < len(lines) else i

    def render_table(self, table_data):
        if not table_data:
            return

        # Parse table structure
        rows = [
            [cell.strip() for cell in row.split("|")[1:-1]]
            for row in table_data
            if row.strip() and not row.strip().startswith("|-")
        ]

        if not rows:
            return

        # Get max width for each column
        col_widths = [
            max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))
        ]

        # Render header
        for i, cell in enumerate(rows[0]):
            padded = cell.ljust(col_widths[i])
            self.chat_display.insert(tk.END, f" {padded} ", "th")
            if i < len(rows[0]) - 1:
                self.chat_display.insert(tk.END, "│")
        self.chat_display.insert(tk.END, "\n")

        # Separator
        self.chat_display.insert(
            tk.END, "─" * (sum(col_widths) + len(col_widths) * 3) + "\n"
        )

        # Render data rows
        for row in rows[1:]:
            for i, cell in enumerate(row):
                padded = cell.ljust(col_widths[i])
                self.chat_display.insert(tk.END, f" {padded} ", "td")
                if i < len(row) - 1:
                    self.chat_display.insert(tk.END, "│")
            self.chat_display.insert(tk.END, "\n")

        self.chat_display.insert(tk.END, "\n")
