import tkinter as tk
from ..models import RoleNames


class ChatStatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.config(relief=tk.SUNKEN, borderwidth=1)

        # Set label width to prevent shifting
        label_widths = {"chat_info": 15, "model_info": 5, "stats": 20, "sys_msg": 40}

        # Create labels with fixed widths
        self.chat_info = tk.Label(
            self, text="Chat Info", width=label_widths["chat_info"], anchor=tk.W, padx=5
        )
        self.separator1 = tk.Label(self, text="│", padx=2)
        self.model_info = tk.Label(
            self,
            text="Model Info",
            width=label_widths["model_info"],
            anchor=tk.W,
            padx=5,
        )
        self.separator2 = tk.Label(self, text="│", padx=2)
        self.stats = tk.Label(
            self, text="", width=label_widths["stats"], anchor=tk.W, padx=5
        )
        self.separator3 = tk.Label(self, text="│", padx=2)
        self.system_msg = tk.Label(
            self, text="", width=label_widths["sys_msg"], anchor=tk.E, padx=5
        )

        # Grid layout
        self.chat_info.grid(row=0, column=0, sticky=tk.NSEW)
        self.separator1.grid(row=0, column=1, sticky=tk.NS)
        self.model_info.grid(row=0, column=2, sticky=tk.NSEW)
        self.separator2.grid(row=0, column=3, sticky=tk.NS)
        self.stats.grid(row=0, column=4, sticky=tk.NSEW)
        self.separator3.grid(row=0, column=5, sticky=tk.NS)
        self.system_msg.grid(row=0, column=6, sticky=tk.NSEW)

        # Configure column weights
        for col in range(7):
            self.columnconfigure(col, weight=1)

        self.system_msg_timer = None

    def update_chat_info(self, chat_name):
        """Update chat name display"""
        self.chat_info.config(text=f"{chat_name}")

    def update_model_info(self, model_name):
        """Updates model info"""
        self.model_info.config(text=model_name)

    def update_stats(self, messages):
        """Update chat statistics"""
        total_msgs = len([msg for msg in messages if msg["role"] != RoleNames.TOOL])
        total_words = sum(
            len(msg["content"].split())
            for msg in messages
            if msg["role"] != RoleNames.TOOL
        )

        self.stats.config(text=f"Messages: {total_msgs} | Words: {total_words}")

    def update_system_msg(self, message, message_type="info", duration=5000):
        """Update system msg display"""
        # self.extras.config(text=extras_text)
        if self.system_msg_timer:
            self.after_cancel(self.system_msg_timer)

        color = self.system_msg.cget("fg")  # Use theme color by default
        if message_type == "error":
            color = "#bf616a"  # Use error color from theme

        self.system_msg.config(text=message, fg=color)
        self.system_msg_timer = self.after(
            duration, lambda: self.system_msg.config(text="")
        )

    def apply_theme(self, theme):
        self.config(bg=theme["bg"], borderwidth=1, relief=tk.SUNKEN)

        for widget in (self.chat_info, self.model_info, self.stats, self.system_msg):
            widget.config(bg=theme["bg"], fg=theme["fg"])

        for sep in (self.separator1, self.separator2, self.separator3):
            sep.config(bg=theme["bg"], fg=theme["border_color"])
