import tkinter as tk


def handle_command(self, command):
    args = command.split()

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

    elif command.startswith("/show"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for show command:\n"
                "/show prompt - Shows system llm prompt for current chat\n"
            )

        elif len(args) == 2:
            if args[1] == "prompt":
                self.append_system_message(f"{self.llm_model.system_prompt}")

    elif command.startswith("/restore"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for retore command:\n"
                "/restore prompt - Restores system llm prompt from the config\n"
            )

        elif len(args) == 2:
            if args[1] == "prompt":
                system_prompt = self.config.get("llm", {}).get("system_prompt")
                if not system_prompt:
                    self.append_system_message(f"No prompt specified in the config.")
                else:
                    self.llm_model.set_system_prompt(system_prompt)
                    self.append_system_message(
                        f"Prompt set to: `{self.llm_model.system_prompt}`."
                    )

    elif command == "/help":
        self.append_system_message(
            "Available commands:\n"
            "/clear    - Clear the chat history\n"
            "/tts      - Manage text-to-speech\n"
            "/show     - A subcommand to display state info\n"
            "/restore  - A subcommand to restore original state\n"
            "/help     - Display this help message",
        )
    else:
        self.append_system_message(f"Unknown command '{command}")
