import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from ..models import RoleNames, RoleTags
from ..tools import render_markdown, has_markdown_syntax


class ChatDisplay:
    def __init__(self, parent, theme=None, markdown_enabled=True):
        self.display = ScrolledText(
            parent,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Arial", 12),
        )
        self.display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.markdown_enabled = markdown_enabled
        self._configure_tags(theme)

    def _configure_tags(self, theme):
        self.display.tag_configure(
            RoleTags.USER,
            foreground=theme["user"]["color_prefix"] if theme else "blue",
            font=("Arial", 14, "bold"),
        )
        self.display.tag_configure(
            RoleTags.ASSISTANT,
            foreground=theme["assistant"]["color_prefix"] if theme else "green",
            font=("Arial", 14, "bold"),
        )
        self.display.tag_configure(
            RoleTags.TOOL,
            foreground=theme["tool"]["color_prefix"] if theme else "red",
            font=("Arial", 14, "bold"),
        )
        self.display.tag_configure(RoleTags.CONTENT, foreground="black")

    def append_message(self, role, content):
        self.display.config(state=tk.NORMAL)
        if not self.display.get("end-2c", "end-1c").endswith("\n"):
            self.display.insert(tk.END, "\n")
        self.display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
        self._append_markdown(content)
        self.display.config(state=tk.DISABLED)
        self.display.see(tk.END)

    def append_partial(self, role, token, is_first_token):
        self.display.config(state=tk.NORMAL)
        if is_first_token:
            if not self.display.get("end-2c", "end-1c").endswith("\n"):
                self.display.insert(tk.END, "\n")
            self.display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
        self.display.insert(tk.END, token)
        self.display.config(state=tk.DISABLED)
        self.display.see(tk.END)

    def handle_response_readiness(self, last_message):
        """Called when response is generated and ready for postprocessing"""
        if last_message["role"] == RoleNames.ASSISTANT:
            last_message = last_message["content"]

            # Rerender the message in case of markdown syntax
            if self.markdown_enabled and has_markdown_syntax(last_message):
                self.display.config(state=tk.NORMAL)

                tag_indices = self.display.tag_ranges(RoleTags.ASSISTANT)
                if tag_indices:
                    start_index = tag_indices[-2]
                    self.display.delete(start_index, tk.END)
                    if not self.display.get("end-2c", "end-1c").endswith("\n"):
                        self.display.insert(tk.END, "\n")
                    self.display.insert(
                        tk.END, f"{RoleNames.ASSISTANT}: ", RoleTags.ASSISTANT
                    )
                    render_markdown(self.display, last_message)

                self.display.config(state=tk.DISABLED)

    def _append_markdown(self, text):
        if self.markdown_enabled:
            render_markdown(self.display, text)
        else:
            self.display.insert(tk.END, text + "\n")

    def clear(self):
        self.display.config(state=tk.NORMAL)
        self.display.delete(1.0, tk.END)
        self.display.config(state=tk.DISABLED)

    def update(self, messages):
        self.clear()
        for message in messages:
            if message["role"] != "system":
                self.append_message(message["role"], message["content"])