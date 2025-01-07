import tkinter as tk
from tkinter import messagebox


def update_chat_history(self, history):
    selection = self.chat_list.curselection()
    if not selection:
        messagebox.showerror("Clear command", "No chat selected.")
        return

    selected_index = selection[0]
    chat_name = self.chat_list.get(selected_index)

    self.chat_history = history
    self.llm_model.load_history(self.chat_history)

    self.chats[chat_name] = history
    self.load_chat(chat_name)


def handle_command(self, command):
    args = command.split()

    if command == "/help":
        self.append_system_message(
            "Available commands:\n"
            "/clear    - Clear the chat history (optionally, role can be specified)\n"
            "/compress - Compresses history of currenlty selected chat\n"
            "/tts      - Manage text-to-speech\n"
            "/show     - A subcommand to display state info\n"
            "/stats    - A chat statistics\n"
            "/markdown  - Manage markdown post processing\n"
            "/restore  - A subcommand to restore original state\n"
            "/remove   - Removes messages from the selected chat\n"
            "\n/help   - Display this help message",
        )

    elif command.startswith("/clear"):
        if len(args) == 2:
            # Clear all messages for given role from the chat window
            role = args[1]
            if role == "system":
                messagebox.showerror("Clear command", "System role cannot be cleared.")
                return
            update_chat_history(
                self, [msg for msg in self.chat_history if not (msg["role"] == role)]
            )
        elif len(args) == 1:
            # Clear all messages from the chat window
            update_chat_history(self, [])
        else:
            self.append_system_message(
                "Syntax for clear command:\n"
                "/clear        -  Clears all messages\n"
                "/clear [role] -  Clears all messages for specific role\n"
            )

    elif command.startswith("/tts"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for TTS command:\n"
                "/tts on  - Enable text-to-speech\n"
                "/tts off - Disable text-to-speech\n"
                "/tts     - Show this help message",
            )
        elif len(args) == 2:
            if args[1] == "on":
                if not self.tts_model:
                    self.append_system_message(
                        f"tts is DISABLED in config and cannot be enabled by this command"
                    )
                    return
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

    elif command == "/stats":
        # Chat statistics

        total_messages = len(self.chat_history)
        total_words = sum(
            len(message["content"].split()) for message in self.chat_history
        )

        role_message_count = {}
        role_word_count = {}

        for message in self.chat_history:
            role = message["role"]
            words_in_message = len(message["content"].split())
            # Update message count per role
            role_message_count[role] = role_message_count.get(role, 0) + 1
            # Update word count per role
            role_word_count[role] = role_word_count.get(role, 0) + words_in_message

        # Format the statistics
        stats_message = (
            f"Chat Statistics:\n"
            f"- Total messages: {total_messages}\n"
            f"- Total words: {total_words}\n"
        )

        stats_message += "- Messages per role:\n"
        for role, count in role_message_count.items():
            stats_message += f"  {role}: {count} messages\n"

        stats_message += "- Words per role:\n"
        for role, count in role_word_count.items():
            stats_message += f"  {role}: {count} words\n"

        # Display the statistics as a system message
        self.append_system_message(stats_message)

    elif command.startswith("/markdown"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for markdown command:\n"
                "/markdown on  - Enable markdown post processing\n"
                "/markdown off - Disable tmarkdown post procesing\n"
                "/markdown     - Show this help message",
            )
        elif len(args) == 2:
            if args[1] == "on":
                self.markdown_enabled = True
                self.append_system_message("Markdown enabled.")
            elif args[1] == "off":
                self.markdown_enabled = False
                self.append_system_message("Markdown disabled.")
            else:
                self.append_system_message(
                    f"Invalid argument '{args[1]}'. Use /markdown on, /markdown off",
                )
                return
            update_chat_history(self, self.chat_history)
        else:
            self.append_system_message(
                "Too many arguments. Use /tts on, /tts off",
            )

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

    elif command.startswith("/compress"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for compress command:\n"
                "/compress keep_first keep_last max_words - Compresses history of currenlty selected chat\n"
            )

        elif len(args) == 4:
            keep_first = int(args[1])
            keep_last = int(args[2])
            max_words = int(args[3])
            self.compress_active_chat(
                keep_first=keep_first, keep_last=keep_last, max_words=max_words
            )

    elif command.startswith("/remove"):
        if len(args) != 2 and len(args) != 3:
            self.append_system_message(
                "Syntax for message removal command:\n"
                "/remove last_n  - Removes last n commands of currenlty selected chat\n"
                "/remove from to - Removes messages in [from, to], range of currenlty selected chat\n"
            )

        elif len(args) == 2:
            last_n = int(args[1])
            if last_n < 0 or last_n > len(self.chat_history):
                pass
            else:
                update_chat_history(self, self.chat_history[:-last_n])

        elif len(args) == 3:
            start = int(args[1])
            end = int(args[2])
            if start < 0 or end >= len(self.chat_history) or start > end:
                self.append_system_message(
                    f"Invalid range: start must be >= 0, end must be < {len(self.chat_history)}, and start <= end."
                )
            else:
                update_chat_history(
                    self, self.chat_history[:start] + self.chat_history[end + 1 :]
                )
    else:
        self.append_system_message(f"Unknown command '{command}")
