import tkinter as tk


def handle_command(self, command):
    if command == "/clear":
        # Clear all messages from the chat window
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)  # Remove all text
        self.chat_display.config(state=tk.DISABLED)

        self.chat_history = []
        self.llm_model.load_history(self.chat_history)
        selection = self.chat_list.curselection()
        if selection:
            selected_index = selection[0]
            chat_name = self.chat_list.get(selected_index)
            self.chats[chat_name] = []

    elif command.startswith("/tts"):
        args = command.split()
        if len(args) == 1:
            self.append_system_message(
                "Syntax for TTS commands:\n"
                "/tts on  - Enable text-to-speech\n"
                "/tts off - Disable text-to-speech\n"
                "/tts     - Show this help message",
            )
        elif len(args) == 2:
            if args[1] == "on":
                self.tts_enabled = True
                self.append_system_message("Text-to-speech enabled.")
            elif args[1] == "off":
                self.tts_enabled = False
                self.append_system_message("Text-to-speech disabled.")
            else:
                self.append_system_message(
                    f"Invalid argument '{args[1]}'. Use /tts on, /tts off",
                )
        else:
            self.append_system_message(
                "Too many arguments. Use /tts on, /tts off",
            )

    elif command == "/show":
        if len(args) == 1:
            self.append_system_message(
                "Syntax for show command:\n"
                "/show prompt - Shows system llm prompt for current chat\n"
            )

        elif len(args) == 2:
            if args[1] == "prompt":
                self.append_system_message(f"{self.llm_model.system_prompt}.")

    elif command == "/help":
        self.append_system_message(
            "Available commands:\n"
            "/clear - Clear the chat history\n"
            "/tts   - Manage text-to-speech (use '/tts' for detailed options)\n"
            "/help  - Display this help message",
        )
    else:
        self.append_system_message(f"Unknown command '{command}")
