import tkinter as tk


class ChatInput:
    """A text input to provide better chat typing experience"""

    def __init__(self, root):

        self.root = root
        self.input_frame = root.input_frame
        self.theme = root.theme
        self.handle_user_input = root.handle_user_input

        self.user_input = tk.Text(
            self.input_frame,
            font=("Arial", 12),
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            relief=tk.FLAT,
            bd=5,
            height=1,  # Start with single line
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
        self.user_input.bind("<<Modified>>", self.update_height)

    def update_height(self, event=None):
        """Dynamically adjust text widget height after a small delay."""
        if self.user_input.edit_modified():
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
        num_lines = max(1, min(5, (required_height // single_line_height)))

        # Set height only if it has changed
        current_num_lines = int(self.user_input.cget("height"))
        if current_num_lines != num_lines:
            self.user_input.configure(height=num_lines)

        if required_height > (single_line_height * 5):
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.scrollbar.pack_forget()

    def select_all(self, event=None):
        """Select all text in the input widget"""
        self.user_input.tag_add(tk.SEL, "1.0", tk.END)
        self.user_input.mark_set(tk.INSERT, tk.END)
        return "break"  # Prevents default behavior

    def handle_return_key(self, event):
        """Handle Return key press - submit if alone, newline if with Shift."""
        if not event.state & 0x1:  # No Shift key
            self.handle_user_input()
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