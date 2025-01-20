import tkinter as tk
from ..tools import ChatSettings
from ..models import RoleNames


class ChatStatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.config(relief=tk.SUNKEN, borderwidth=1)

        # Set label width to prevent shifting
        label_widths = {
            "chat_info": 15,
            "state_info": 10,
            "model_info": 40,
            "stats": 20,
            "sys_msg": 30,
        }

        column_weights = {
            "chat_info": 3,
            "state_info": 2,
            "model_info": 7,
            "stats": 3,
            "sys_msg": 6,
        }

        # Create labels with fixed widths
        self.chat_info = tk.Label(
            self, text="Chat Info", width=label_widths["chat_info"], anchor=tk.W, padx=5
        )
        self.separator1 = tk.Label(self, text="│", padx=1)
        self.state_info = tk.Label(
            self, text="", width=label_widths["state_info"], anchor=tk.W, padx=0
        )
        self.separator2 = tk.Label(self, text="│", padx=1)
        self.model_info = tk.Label(
            self,
            text="--",
            width=label_widths["model_info"],
            anchor=tk.W,
            padx=1,
        )
        self.separator3 = tk.Label(self, text="│", padx=1)
        self.stats = tk.Label(
            self, text="", width=label_widths["stats"], anchor=tk.W, padx=5
        )
        self.separator4 = tk.Label(self, text="│", padx=2)
        self.system_msg = tk.Label(
            self, text="", width=label_widths["sys_msg"], anchor=tk.E, padx=5
        )

        # Grid layout
        self.chat_info.grid(row=0, column=0, sticky=tk.NSEW)
        self.columnconfigure(0, weight=column_weights["chat_info"])

        self.separator1.grid(row=0, column=1, sticky=tk.NS)
        self.columnconfigure(1, weight=1)

        self.state_info.grid(row=0, column=2, sticky=tk.NSEW)
        self.columnconfigure(2, weight=column_weights["state_info"])

        self.separator2.grid(row=0, column=3, sticky=tk.NS)
        self.columnconfigure(3, weight=1)

        self.model_info.grid(row=0, column=4, sticky=tk.NSEW)
        self.columnconfigure(4, weight=column_weights["model_info"])

        self.separator3.grid(row=0, column=5, sticky=tk.NS)
        self.columnconfigure(5, weight=1)

        self.stats.grid(row=0, column=6, sticky=tk.NSEW)
        self.columnconfigure(6, weight=column_weights["stats"])

        self.separator4.grid(row=0, column=7, sticky=tk.NS)
        self.columnconfigure(7, weight=1)

        self.system_msg.grid(row=0, column=8, sticky=tk.NSEW)
        self.columnconfigure(8, weight=column_weights["sys_msg"])

        self.system_msg_timer = None

    def update_chat_info(self, chat_name):
        """Update chat name display"""
        self.chat_info.config(text=f"  {chat_name}")

    def update_model_info(self, model_info):
        """Updates model info"""
        self.model_info.config(text=model_info)

    def update_stats(self, messages):
        """Update chat statistics"""
        total_msgs = len([msg for msg in messages if msg["role"] != RoleNames.TOOL])
        total_words = sum(
            len(msg["content"].split())
            for msg in messages
            if msg["role"] != RoleNames.TOOL
        )

        self.stats.config(text=f"Messages: {total_msgs} | Words: {total_words}")

    def update_state_info(self, settings: ChatSettings):
        """Update state info display"""
        state_infos = []
        if settings.replies_allowed:
            state_infos.append("🤖💬")
        else:
            state_infos.append("🤖🚫")

        if settings.markdown_enabled:
            state_infos.append("📝✅")
        else:
            state_infos.append("📝❌")

        self.state_info.config(text=f"{' | '.join(state_infos)}")

    def update_system_msg(self, message, message_type="info", duration=3000):
        """Update system msg display"""
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

        for widget in (
            self.chat_info,
            self.model_info,
            self.stats,
            self.state_info,
            self.system_msg,
        ):
            widget.config(bg=theme["bg"], fg=theme["fg"])

        for sep in (self.separator1, self.separator2, self.separator3, self.separator4):
            sep.config(bg=theme["bg"], fg=theme["border_color"])
