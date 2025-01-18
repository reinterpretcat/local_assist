import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional
from ..tools import get_button_config, get_list_style


class ChatInput:
    """A text input to provide better chat typing experience"""

    def __init__(
        self,
        root,
        input_frame: tk.Frame,
        on_user_input: Callable,
        on_record_voice: Optional[Callable],
        on_cancel_response: Callable,
        min_height: int = 2,
        max_height: int = 8,
    ):

        self.root = root
        self.input_frame = input_frame
        self.on_user_input = on_user_input
        self.on_cancel_response = on_cancel_response

        self.on_record_voice = on_record_voice
        self.is_recording = False

        self.min_height = min_height
        self.max_height = max_height

        self.undo_stack = []
        self.max_history_size = 64

        self.user_input = tk.Text(
            self.input_frame,
            font=("Arial", 12),
            relief=tk.FLAT,
            undo=True,
            bd=5,
            height=self.min_height,  # Start with single line
            wrap=tk.WORD,  # Enable word wrapping
            width=40,  # Set initial width in characters
        )
        # Create a scrollbar for the text widget
        self.scrollbar = tk.Scrollbar(
            self.input_frame, orient="vertical", command=self.user_input.yview
        )
        self.user_input.configure(yscrollcommand=self.scrollbar.set)

        # Pack the text widget only initially, scrollbar will be packed when needed
        self.user_input.pack(side=tk.LEFT, padx=(10, 5), pady=5, fill=tk.X, expand=True)

        self.user_input.bind("<Control-a>", self.select_all)
        self.user_input.bind("<Return>", self.handle_return_key)
        self.user_input.bind("<Shift-Return>", self.insert_newline)
        self.user_input.bind("<<Modified>>", self.handle_modify)

        self.is_record_enabled = True if on_record_voice is not None else False

        self.record_button = tk.Button(
            self.input_frame,
            text="🎙️ Record",
            command=lambda: (
                self.handle_record_voice() if self.is_record_enabled else None
            ),
            font=("Arial", 12),
        )
        self.record_button.pack(side=tk.RIGHT, padx=(5, 5), pady=5)
        self.record_button.config(state=tk.NORMAL if on_record_voice else tk.DISABLED)

        self.send_button = tk.Button(
            self.input_frame,
            text="Send",
            command=lambda: self._consume_input(),
            font=("Arial", 12),
        )
        self.send_button.pack(side=tk.RIGHT, padx=(5, 10), pady=5)

        self.image_button = tk.Button(
            self.input_frame,
            text="📷 Image",
            command=self.handle_image_selection,
            font=("Arial", 12),
        )
        self.image_button.pack(side=tk.RIGHT, padx=(5, 5), pady=5)

        self.selected_image: Optional[str] = None

    def handle_modify(self, event=None):
        """Dynamically adjust text widget height after a small delay."""
        if self.user_input.edit_modified():
            # self.track_changes()
            self.user_input.edit_modified(False)
            # Delay execution to prevent rapid recalculation
            self.user_input.after(50, self._adjust_height)

    def _adjust_height(self, event=None):
        """Dynamically adjust text widget height based on content."""
        # Get content and calculate required height
        temp_label = tk.Label(
            self.user_input,
            text=self.user_input.get("1.0", "end-1c"),
            font=self.user_input.cget("font"),
            wraplength=self.user_input.winfo_width(),
        )
        required_height = temp_label.winfo_reqheight()
        temp_label.destroy()

        # Get current widget height in pixels
        single_line_height = (
            self.user_input.dlineinfo("1.0")[3]
            if self.user_input.dlineinfo("1.0")
            else 20
        )

        # Calculate the number of lines
        num_lines = max(
            self.min_height,
            min(self.max_height, (required_height // single_line_height)),
        )

        # Set height only if it has changed
        current_num_lines = int(self.user_input.cget("height"))
        if current_num_lines != num_lines:
            self.user_input.configure(height=num_lines)

        if required_height > (single_line_height * 5):
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.scrollbar.pack_forget()

        self.scroll_to_cursor()

    def select_all(self, event=None):
        """Select all text in the input widget"""
        self.user_input.tag_add(tk.SEL, "1.0", tk.END)
        self.user_input.mark_set(tk.INSERT, tk.END)
        return "break"  # Prevents default behavior

    def set_edit_text(self, new_text):
        """Sets text to user input."""
        self.user_input.delete("1.0", tk.END)
        self.user_input.insert(tk.END, new_text)
        self.send_button.config(text="Edit")

    def handle_return_key(self, event):
        """Handle Return key press - submit if alone, newline if with Shift."""
        if not event.state & 0x1:  # No Shift key
            self._consume_input()

            return "break"  # Prevent default newline
        return None  # Allow default newline behavior with Shift

    def insert_newline(self, event=None):
        """Insert newline on Shift+Return"""
        self.user_input.insert("insert", "\n")
        self.user_input.edit_modified(
            True
        )  # Explicitly mark modified to trigger update
        self._adjust_height()  # Update height immediately after insertion
        return "break"

    # Function to scroll to the cursor position
    def scroll_to_cursor(self):
        # Get the current index of the cursor
        cursor_index = self.user_input.index(tk.INSERT)

        # Scroll to the line containing the cursor
        self.user_input.see(cursor_index)

    def handle_record_voice(self):
        """Handle record button."""
        self.record_button.focus_set()

        if not self.is_recording:
            self.is_recording = True
            self.record_button.config(text="🛑 Stop")  # Change text and color
        else:
            self.is_recording = False
            self.record_button.config(text="🎙️ Record")

        self.on_record_voice()

    def handle_image_selection(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.selected_image = file_path
            self._consume_input(with_image=True)

    def _consume_input(self, with_image=False):
        user_message = self.user_input.get("1.0", "end-1c").strip()
        self.user_input.delete("1.0", tk.END)

        if user_message or with_image:
            if with_image:
                self.on_user_input(user_message, image_path=self.selected_image)
                self.selected_image = None
            else:
                self.on_user_input(user_message)

    def disable(self):
        """Disable user input."""
        self.user_input.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)
        self.send_button.config(
            text="Cancel", command=lambda: self.on_cancel_response(), state=tk.NORMAL
        )

    def enable(self):
        """Enable user input."""
        self.user_input.config(state=tk.NORMAL)
        self.record_button.config(
            state=tk.NORMAL if self.is_record_enabled else tk.DISABLED
        )
        self.send_button.config(text="Send", command=lambda: self._consume_input())

    def clear_input(self):
        """Clears input field."""
        self.user_input.delete("1.0", tk.END)

    def apply_theme(self, theme):
        button_config = get_button_config(theme)
        for button in [
            self.send_button,
            self.record_button,
        ]:
            button.configure(**button_config)

        self.user_input.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
            font=("Arial", 12),
            relief="solid",
            borderwidth=1,
        )

        # Configure scrollbar
        self.scrollbar.configure(
            bg=theme["scrollbar_bg"],
            activebackground=theme["scrollbar_hover"],
            troughcolor=theme["scrollbar_bg"],
            width=12,
        )
