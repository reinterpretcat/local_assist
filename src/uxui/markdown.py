import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import re


def setup_markdown_tags(chat_display: ScrolledText):
    MarkdownProcessor(chat_display).setup_markdown_tags()


def render_markdown(chat_display: ScrolledText, message):
    MarkdownProcessor(chat_display).render_markdown(message)


class MarkdownProcessor:

    # Precompiled regex as a static variable
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

    def __init__(self, chat_display: ScrolledText):
        self.chat_display = chat_display

    def has_markdown_syntax(self, text):
        """Check if the given text contains Markdown syntax that can be processed."""
        return bool(MarkdownProcessor.MARKDOWN_PATTERNS.search(text))

    def setup_markdown_tags(self):
        # Basic styles
        self.chat_display.tag_configure("bold", font=("Arial", 12, "bold"))
        self.chat_display.tag_configure("italic", font=("Arial", 12, "italic"))
        self.chat_display.tag_configure("strike", overstrike=1)
        self.chat_display.tag_configure(
            "code", font=("Courier", 12), background="#f0f0f0"
        )

        # Headers
        for i in range(1, 7):
            size = 20 - (i * 2)
            self.chat_display.tag_configure(f"h{i}", font=("Arial", size, "bold"))

        # Code blocks
        self.chat_display.tag_configure(
            "codeblock",
            font=("Courier", 12),
            background="#f0f0f0",
            spacing1=10,
            spacing3=10,
            lmargin1=20,
            lmargin2=20,
        )

        # Lists
        self.chat_display.tag_configure("bullet", lmargin1=20, lmargin2=40)
        self.chat_display.tag_configure("ordered", lmargin1=20, lmargin2=40)

        # Blockquote
        self.chat_display.tag_configure(
            "blockquote",
            lmargin1=20,
            lmargin2=20,
            background="#f9f9f9",
            spacing1=5,
            spacing3=5,
        )

        # Table tags
        self.chat_display.tag_configure("table", spacing1=5, spacing3=5)
        self.chat_display.tag_configure(
            "th", font=("Arial", 12, "bold"), background="#f0f0f0"
        )
        self.chat_display.tag_configure("td", font=("Arial", 12))

        # Task list
        self.chat_display.tag_configure("task-done", foreground="green")
        self.chat_display.tag_configure("task-pending", foreground="gray")

        # Horizontal rule
        self.chat_display.tag_configure(
            "hr", font=("Arial", 1), spacing1=10, spacing3=10, background="gray"
        )

    def render_markdown(self, text):
        if not self.has_markdown_syntax(text):
            print("no markdown")
            self.chat_display.insert(tk.END, text + "\n")
            return
        print("markdown")

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

            # Task lists
            task_match = re.match(r"^- \[([ x])\] (.+)$", line)
            if task_match:
                done = task_match.group(1) == "x"
                tag = "task-done" if done else "task-pending"
                checkbox = "☒ " if done else "☐ "
                self.chat_display.insert(
                    tk.END, checkbox + task_match.group(2) + "\n", tag
                )
                i += 1
                continue

            # Horizontal rule
            if re.match(r"^([-*_])\1{2,}$", line):
                self.chat_display.insert(tk.END, "─" * 40 + "\n", "hr")
                i += 1
                continue

            # Previous markdown handling...
            header_match = re.match(r"^(#{1,6})\s(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                self.chat_display.insert(
                    tk.END, header_match.group(2) + "\n", f"h{level}"
                )
                i += 1
                continue

            if line.startswith("> "):
                self.chat_display.insert(tk.END, line[2:] + "\n", "blockquote")
                i += 1
                continue

            bullet_match = re.match(r"^[-*]\s(.+)$", line)
            if bullet_match:
                self.chat_display.insert(
                    tk.END, "• " + bullet_match.group(1) + "\n", "bullet"
                )
                i += 1
                continue

            ordered_match = re.match(r"^\d+\.\s(.+)$", line)
            if ordered_match:
                num = int(re.match(r"^\d+", line).group())
                self.chat_display.insert(
                    tk.END, f"{num}. {ordered_match.group(1)}\n", "ordered"
                )
                i += 1
                continue

            line = self.process_inline_styles(line)
            self.chat_display.insert(tk.END, line + "\n")
            i += 1

        if in_table:
            self.render_table(table_data)

        self.chat_display.config(state=current_state)

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

    def handle_code_block(self, lines, start_idx):
        code_content = []
        i = start_idx + 1

        while i < len(lines) and not lines[i].startswith("```"):
            code_content.append(lines[i])
            i += 1

        code_text = "\n".join(code_content)
        self.chat_display.insert(tk.END, code_text + "\n", "codeblock")

        return i + 1 if i < len(lines) else i

    def process_inline_styles(self, text):
        # Inline code
        text = re.sub(r"`([^`]+)`", lambda m: self.add_tag(m.group(1), "code"), text)
        # Bold
        text = re.sub(
            r"\*\*(.+?)\*\*", lambda m: self.add_tag(m.group(1), "bold"), text
        )
        # Italic
        text = re.sub(r"\*(.+?)\*", lambda m: self.add_tag(m.group(1), "italic"), text)
        # Strikethrough
        text = re.sub(r"~~(.+?)~~", lambda m: self.add_tag(m.group(1), "strike"), text)
        return text

    def add_tag(self, text, tag):
        self.chat_display.insert(tk.END, text, tag)
        return ""
