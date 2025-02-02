import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Dict
from PIL import Image, ImageTk
from ..models import RoleNames, RoleTags
from ..tools import *


class ChatDisplay:
    def __init__(self, parent, chat_history: ChatHistory, on_code_editor: Callable):
        self.parent = parent
        self.chat_history = chat_history
        self.on_code_editor = on_code_editor
        self.images = []  # Keep references to prevent garbage collection

        # Store (start, end) indices for each message
        self.message_boundaries = []
        self.selected_message = None

        self.display = ScrolledText(
            parent,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Arial", 12),
        )
        self.display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Context menus
        self.message_menu = tk.Menu(parent, tearoff=0)
        self.message_menu.add_command(label="Edit", command=self.edit_message)
        self.message_menu.add_command(label="Delete", command=self.delete_message)
        self.message_menu.add_command(
            label="Edit and Run Code", command=self.handle_code_run
        )

        self.display.bind("<Button-1>", self.handle_click)
        self.display.bind("<Button-3>", self.show_context_menu)

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

        self._setup_codetags()
        setup_markdown_tags(chat_display=self.display, theme=theme)

        self.display.tag_configure("selected", background="#e0e0e0")
        self.display.tag_lower("selected")  # Put selection behind other tags

    def _setup_codetags(self) -> None:
        # TODO allow to change tags
        tags = parse_scheme(default_syntax_scheme)
        for key, value in tags.items():
            if isinstance(value, str):
                self.display.tag_configure(f"Token.{key}", foreground=value)

    def append_message(self, role, content, image_path=None):
        self.display.config(state=tk.NORMAL)

        # Ensure proper line break before new message
        if not self.display.get("end-2c", "end-1c").endswith("\n"):
            self.display.insert(tk.END, "\n")

        # Store starting position for message
        start_index = self.display.index("insert linestart")

        # Insert role prefix
        self.display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))

        if image_path:
            self.display.insert(tk.END, "\n")
            self._append_image(image_path)

        if content:
            self._append_markdown(content)

        # Ensure message ends with newline
        if not self.display.get("end-2c", "end-1c").endswith("\n"):
            self.display.insert(tk.END, "\n")

        # Store exact message boundary
        end_index = self.display.index("end-1c")

        self.message_boundaries.append(
            {
                "start": start_index,
                "end": end_index,
                "role": role,
                "content": content,
                "image_path": image_path,
            }
        )

        self.display.config(state=tk.DISABLED)
        self.display.see(tk.END)

    def append_partial(self, role, token, is_first_token):
        self.display.config(state=tk.NORMAL)

        if is_first_token:
            if not self.display.get("end-2c", "end-1c").endswith("\n"):
                self.display.insert(tk.END, "\n")
            start_index = self.display.index(tk.END)
            self.display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
            self.message_boundaries.append(
                {
                    "start": start_index,
                    "end": None,
                    "role": role,
                    "content": token,
                    "image_path": None,
                }
            )
        else:
            current_message = self.message_boundaries[-1]
            current_message["content"] = current_message["content"] + token
            current_message["end"] = self.display.index(tk.END)

        self.display.insert(tk.END, token)
        self.display.config(state=tk.DISABLED)
        self.display.see(tk.END)

    def handle_response_readiness(self, last_message):
        """Called when response is generated and ready for postprocessing"""
        if last_message["role"] == RoleNames.ASSISTANT:
            last_message = last_message["content"]

            # Rerender the message in case of markdown syntax
            if (
                self.chat_history.get_chat_settings().markdown_enabled
                and has_markdown_syntax(last_message)
            ):
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

    def _append_image(self, image_path):
        try:
            image = Image.open(image_path)
            # Scale image if too large
            max_width = 400
            if image.width > max_width:
                ratio = max_width / image.width
                new_size = (max_width, int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(image)
            self.images.append(photo)  # Prevent garbage collection

            self.display.image_create(tk.END, image=photo)
            self.display.insert(tk.END, "\n")
        except Exception as e:
            role = RoleNames.TOOL
            self.display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
            self.display.insert(tk.END, f"Error loading image: {str(e)}\n")

    def _append_markdown(self, text):
        if self.chat_history.get_chat_settings().markdown_enabled:
            render_markdown(self.display, text)
        else:
            self.display.insert(tk.END, text + "\n")

    def clear(self):
        self.display.config(state=tk.NORMAL)
        self.display.delete(1.0, tk.END)
        self.display.config(state=tk.DISABLED)
        self.images.clear()

    def update(self, messages: Dict):
        self.clear()
        for message in messages:
            if message["role"] != "system":
                image_path = message.get("image_path", None)
                self.append_message(message["role"], message["content"], image_path)

    def show_context_menu(self, event):
        index = self.display.index(f"@{event.x},{event.y}")
        self.select_message_at_index(index)

        if self.selected_message:
            has_code = "```" in self.selected_message["content"]
            self.message_menu.entryconfig(
                "Edit and Run Code", state=tk.NORMAL if has_code else tk.DISABLED
            )
            self.message_menu.post(event.x_root, event.y_root)

    def handle_code_run(self):
        if self.selected_message:
            content = self.selected_message["content"]
            code_blocks = self.extract_code_blocks(
                content
            )  # You'll need to implement this
            if code_blocks:
                self.on_code_editor(None, "\n\n\n\n".join(code_blocks).strip())

    def handle_click(self, event):
        index = self.display.index(f"@{event.x},{event.y}")
        self.select_message_at_index(index)

    def select_message_at_index(self, index):
        self.display.config(state=tk.NORMAL)
        self.display.tag_remove("selected", "1.0", tk.END)

        for msg in self.message_boundaries:
            start = float(msg["start"])
            end = float(msg["end"])

            if self.display.compare(start, "<=", index) and self.display.compare(
                index, "<=", end
            ):
                self.selected_message = msg
                # Ensure selection spans exact message boundaries
                self.display.tag_add("selected", msg["start"], msg["end"])
                self.display.tag_configure(
                    "selected", background=self.theme["chat_select_bg"]
                )
                break

        self.display.config(state=tk.DISABLED)

    def edit_message(self):
        if self.selected_message:
            # Create edit dialog
            dialog = tk.Toplevel(self.parent)
            dialog.title("Edit Message")

            text = tk.Text(dialog, wrap=tk.WORD, height=10, width=50)
            text.insert("1.0", self.selected_message["content"])
            text.pack(padx=10, pady=10)

            def save():
                new_content = text.get("1.0", tk.END).strip()
                position = self.message_boundaries.index(self.selected_message)
                self.chat_history.update_message(position, new_content)
                self.selected_message["content"] = new_content
                self.update_display()
                dialog.destroy()

            tk.Button(dialog, text="Save", command=save).pack(pady=5)

    def delete_message(self):
        if self.selected_message:
            position = self.message_boundaries.index(self.selected_message)
            self.chat_history.delete_message(position)
            self.message_boundaries.remove(self.selected_message)
            self.selected_message = None
            self.update_display()

    def update_display(self):
        messages = [
            {
                "role": msg["role"],
                "content": msg["content"],
                "image_path": msg.get("image_path"),
            }
            for msg in self.message_boundaries
        ]
        self.clear()
        for message in messages:
            self.append_message(
                message["role"], message["content"], message.get("image_path")
            )

    def clear(self):
        self.display.config(state=tk.NORMAL)
        self.display.delete(1.0, tk.END)
        self.display.config(state=tk.DISABLED)
        self.images.clear()
        self.message_boundaries = []
        self.selected_message = None

    def extract_code_blocks(self, content):
        # Simple code block extraction - you might want to enhance this
        blocks = []
        lines = content.split("\n")
        in_block = False
        current_block = []

        for line in lines:
            if line.startswith("```"):
                if in_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                in_block = not in_block
                continue
            if in_block:
                current_block.append(line)

        return blocks

    def apply_theme(self, theme: Dict):
        self.theme = theme
        self._configure_tags(theme)
        configure_scrolled_text(self.display, theme)
        self.message_menu.configure(
            bg=theme["menu_bg"],
            fg=theme["fg"],
            activebackground=theme["button_bg"],
            activeforeground=theme["button_fg"],
        )
