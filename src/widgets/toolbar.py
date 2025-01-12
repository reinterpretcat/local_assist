import tkinter as tk
from typing import Callable


class ChatToolBar:
    def __init__(self, parent, chat_display, chat_history, on_chat_change: Callable):
        self.chat_history = chat_history
        self.on_chat_change = on_chat_change

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

    def remove_last_message(self):
        """Remove the last message from the active chat."""
        messages = self.chat_history.get_active_chat_messages()
        if messages:
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

        self.copy_last_btn.configure(**button_style)
        self.copy_all_btn.configure(**button_style)
        self.remove_last_btn.configure(**button_style)
