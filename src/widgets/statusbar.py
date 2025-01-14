import tkinter as tk


class ChatStatusBar(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.config(relief=tk.SUNKEN, borderwidth=1)

        # Create sections with separators
        self.chat_info = tk.Label(self, text="Chat info", anchor=tk.W, padx=5)
        self.separator1 = tk.Label(self, text="│", padx=2)
        self.model_info = tk.Label(self, text="Model info", anchor=tk.W, padx=5)
        self.separator2 = tk.Label(self, text="│", padx=2)
        self.stats = tk.Label(self, text="Statistics", anchor=tk.W, padx=5)
        self.separator3 = tk.Label(self, text="│", padx=2)
        self.settings = tk.Label(self, text="Settings", anchor=tk.E, padx=5)

        # Layout with weights
        self.columnconfigure(0, weight=2)  # chat info
        self.columnconfigure(2, weight=1)  # stats
        self.columnconfigure(4, weight=2)  # system message
        self.columnconfigure(6, weight=1)  # settings

        self.chat_info.grid(row=0, column=0, sticky=tk.EW)
        self.separator1.grid(row=0, column=1)
        self.model_info.grid(row=0, column=2, sticky=tk.EW)
        self.separator2.grid(row=0, column=3)
        self.stats.grid(row=0, column=4, sticky=tk.EW)
        self.separator3.grid(row=0, column=5)
        self.settings.grid(row=0, column=6, sticky=tk.EW)

        self.system_msg_timer = None

    def update_chat_info(self, chat_name):
        """Update chat name display"""
        self.chat_info.config(text=f"{chat_name}")
        
    def update_model_info(self, model_name):
        """Updates model info"""
        self.model_info.config(text=model_name)

    def update_stats(self, messages):
        """Update chat statistics"""
        total_msgs = len(messages)
        total_words = sum(len(msg.content.split()) for msg in messages)
        self.stats.config(text=f"Messages: {total_msgs} | Words: {total_words}")


    def update_settings(self, llm_model, markdown_enabled):
        """Update settings display"""
        settings_text = (
            f"Model: {llm_model} | Markdown: {'On' if markdown_enabled else 'Off'}"
        )
        self.settings.config(text=settings_text)

    def apply_theme(self, theme):
        bg = theme["bg"]
        fg = theme["fg"]
        border = theme["border_color"]

        self.config(bg=bg, borderwidth=1, relief=tk.SUNKEN)

        for widget in (self.chat_info, self.model_info, self.stats, self.settings):
            widget.config(bg=bg, fg=fg)

        for sep in (self.separator1, self.separator2, self.separator3):
            sep.config(bg=bg, fg=border)
