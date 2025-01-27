import tkinter as tk
import re
from ..models import RoleNames
from typing import Callable
from tkinter import simpledialog, messagebox


class ChatToolBar:
    def __init__(
        self,
        parent,
        chat_display,
        chat_history,
        on_chat_change: Callable,
        on_chat_edit: Callable,
        on_code_run: Callable,
    ):
        self.chat_history = chat_history
        self.on_chat_change = on_chat_change
        self.on_chat_edit = on_chat_edit
        self.on_code_run = on_code_run

        self.frame = tk.Frame(parent, bg="lightgray", bd=1, relief=tk.SOLID)
        self.frame.place(x=0, y=0)  # Initial placement

        button_style = {
            "width": 2,
            "height": 1,
            "relief": "flat",
            "font": ("TkDefaultFont", 8),
        }

        # Remove last message button
        self.remove_last_btn = tk.Button(
            self.frame, text="🗑️", command=self.remove_last_message, **button_style
        )
        self.remove_last_btn.pack(side=tk.RIGHT, padx=2)
        self._create_tooltip(self.remove_last_btn, "Remove Last Message")

        # Run last code snippet button
        self.run_last_btn = tk.Button(
            self.frame, text="▶", command=self.run_code_snippet, **button_style
        )
        self.run_last_btn.pack(side=tk.RIGHT, padx=2)
        self._create_tooltip(self.run_last_btn, "Run Last Code Snippet")

        # Edit last message button
        self.edit_last_btn = tk.Button(
            self.frame, text="📝", command=self.edit_last_message, **button_style
        )
        self.edit_last_btn.pack(side=tk.RIGHT, padx=2)
        self._create_tooltip(self.edit_last_btn, "Edit Last Message")

        # Copy all messages button
        self.copy_all_btn = tk.Button(
            self.frame, text="📑", command=self.copy_all_messages, **button_style
        )
        self.copy_all_btn.pack(side=tk.RIGHT, padx=2)
        self._create_tooltip(self.copy_all_btn, "Copy All Messages")

        # Copy last message button
        self.copy_last_btn = tk.Button(
            self.frame, text="📋", command=self.copy_last_message, **button_style
        )
        self.copy_last_btn.pack(side=tk.RIGHT, padx=2)
        self._create_tooltip(self.copy_last_btn, "Copy Last Message")

        # Bind the resize event to reposition the toolbar
        parent.bind("<Configure>", lambda event: self.position_toolbar(chat_display))

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""

        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            label = tk.Label(
                tooltip, text=text, relief="solid", bg="white", pady=2, padx=2
            )
            label.pack()
            widget.tooltip = tooltip
            widget.after(2000, lambda: tooltip.destroy())

        def hide_tooltip(event):
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def copy_last_message(self):
        """Copy the last message to the clipboard."""
        messages = self.chat_history.get_active_chat_messages()
        if messages:
            last_message = messages[-1]["content"]
            self.frame.clipboard_clear()
            self.frame.clipboard_append(last_message)

    def copy_all_messages(self):
        """Copy all messages to the clipboard."""
        messages = self.chat_history.get_active_chat_messages()
        if messages:
            all_messages = "\n".join(msg["content"] for msg in messages)
            self.frame.clipboard_clear()
            self.frame.clipboard_append(all_messages)

    def edit_last_message(self):
        """Edit the last message for the specified role or remove a message for another role."""
        messages = self.chat_history.get_active_chat_messages()

        # TODO refactor this as is very fragile
        # Step 1: Find and edit the last message for role_to_edit
        last_user_message_index = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == RoleNames.USER:
                last_user_message_index = i
                old_message = messages[i]

                def on_edit(new_content, new_image):
                    content_modified = (
                        new_content is not None
                        and new_content.strip() != old_message["content"]
                    )
                    image_modified = (
                        new_image is not None
                        and new_image != old_message.get("image_path")
                    )

                    if content_modified or image_modified:
                        if content_modified:
                            old_message["content"] = new_content.strip()
                        if image_modified:
                            old_message["image_path"] = new_image

                        # Remove the last assistant message if user message was modified
                        for j in range(len(messages) - 1, last_user_message_index, -1):
                            if messages[j]["role"] == RoleNames.ASSISTANT:
                                messages.pop(j)
                                break

                        return True  # Indicate that changes were made
                    return False  # No changes were made

                self.on_chat_edit(
                    old_message["content"],
                    old_message.get("image_path", None),
                    on_edit,
                )
                return

    def run_code_snippet(self):
        """Extracts code from the last message and runs it"""
        messages = self.chat_history.get_active_chat_messages()
        if messages:
            last_message = messages[-1]["content"]
            pattern = r"```(\w*)\n(.*?)\n```"

            # Find all matches in the markdown text
            matches = re.findall(pattern, last_message, re.DOTALL)
            if matches:
                language, content = matches[-1]
                if content.strip():
                    self.on_code_run(content.strip())

    def remove_last_message(self):
        """Remove the last message from the active chat."""
        messages = self.chat_history.get_active_chat_messages()
        if messages:
            confirm = messagebox.askyesno(
                "Confirm", "Are you sure you want to remove the last message?"
            )
            if confirm:
                messages.pop()
                self.on_chat_change()

    def position_toolbar(self, chat_display):
        """Position toolbar at the top-right corner of the chat display."""

        # Ensure geometry is calculated and get toolbar width dynamically
        self.frame.update_idletasks()
        chat_display_width = chat_display.display.winfo_width()

        self.frame.place(
            x=chat_display_width,
            y=14,
            anchor="ne",
        )

    def apply_theme(self, theme):
        """Apply the given theme to the toolbar and its buttons."""
        self.frame.configure(bg=theme["menu_bg"])

        button_style = {
            "bg": theme["button_bg"],
            "fg": theme["button_fg"],
            "activebackground": theme["button_bg_hover"],
            "activeforeground": theme["button_fg"],
        }

        for button in [
            self.copy_last_btn,
            self.copy_all_btn,
            self.edit_last_btn,
            self.remove_last_btn,
            self.run_last_btn,
        ]:
            button.configure(**button_style)
