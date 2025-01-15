from tkinter import messagebox
from .chat_history import LLMSettings
import json


def handle_command(self, command):
    args = command.split()

    if command == "/help":
        self.append_system_message(
            "Available commands:\n"
            "/clear    - Clear the chat history (optionally, role can be specified)\n"
            "/config   - Show configuration\n"
            "/echo     - Echoes message from `tool` role\n"
            "/tts      - Manage text-to-speech\n"
            "/show     - A subcommand to display state info\n"
            "/stats    - A chat statistics\n"
            "/markdown - Manage markdown post processing\n"
            "/reply    - Allows to enable/disable AI replies\n"
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
            self.chat_history.clear_messages_by_role(role)
            self.handle_chat_select()

        elif len(args) == 1:
            # Clear all messages from the chat window
            self.chat_history.clear_all_messages()
            self.handle_chat_select()
        else:
            self.append_system_message(
                "Syntax for clear command:\n"
                "/clear        -  Clears all messages\n"
                "/clear [role] -  Clears all messages for specific role\n"
            )

    elif command.startswith("/config"):
        if len(args) != 2:
            if self.chat_display.markdown_enabled:
                self.append_system_message(
                    f"```json\n{json.dumps(self.config, indent=2)}\n```"
                )
            else:
                self.append_system_message(f"\n{json.dumps(self.config, indent=2)}")
        elif len(args) == 2:

            def get_nested_value(data, path):
                keys = path.split(".")
                for key in keys:
                    if isinstance(data, dict) and key in data:
                        data = data[key]
                    else:
                        return None
                return data

            self.append_system_message(
                f"\n{json.dumps(get_nested_value(self.config, args[1]), indent=2)}"
            )
    elif command.startswith("/echo"):
        if len(args) != 1:
            self.append_system_message(command[len("/echo") :])

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
                self.update_status_message("Text-to-speech enabled.")
            elif args[1] == "off":
                self.tts_enabled = False
                self.update_status_message("Text-to-speech disabled.")
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

        messages = self.chat_history.get_active_chat_messages()
        total_messages = len(messages)
        total_words = sum(len(message["content"].split()) for message in messages)

        role_message_count = {}
        role_word_count = {}

        for message in messages:
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
                "Syntax for markdown command (applies for active chat only):\n"
                "/markdown on  - Enable markdown post processing\n"
                "/markdown off - Disable tmarkdown post procesing\n"
                "/markdown     - Show this help message",
            )
        elif len(args) == 2:
            if args[1] == "on":
                enabled = True
            elif args[1] == "off":
                enabled = False
            else:
                self.append_system_message(
                    f"Invalid argument '{args[1]}'. Use /markdown on, /markdown off",
                )
                return

            self.chat_history.set_chat_settings(
                self.chat_history.get_chat_settings().replace(markdown_enabled=enabled)
            )

            self.update_status_message(
                f"Markdown {'enabled' if enabled else 'disabled'}."
            )
            self.handle_chat_select()
        else:
            self.append_system_message(
                "Too many arguments. Use /tts on, /tts off",
            )

    elif command.startswith("/reply"):
        if len(args) == 1:
            self.append_system_message(
                "Syntax for reply command:\n"
                "/reply on  - Enable AI reply\n"
                "/reply off - Disable AI reply\n"
                "/reply     - Show this help message",
            )
        elif len(args) == 2:
            if args[1] == "on":
                enabled = True
                self.update_status_message("Replies enabled.")
            elif args[1] == "off":
                enabled = False
                self.update_status_message("Replies disabled.")
            else:
                self.append_system_message(
                    f"Invalid argument '{args[1]}'. Use /reply on, /reply off",
                )
                return

            self.chat_history.set_chat_settings(
                self.chat_history.get_chat_settings().replace(replies_allowed=enabled)
            )

        else:
            self.append_system_message(
                "Too many arguments. Use /reply on, /reply off",
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
            self.chat_history.clear_last_n_messages(last_n)
            self.handle_chat_select()

        elif len(args) == 3:
            start = int(args[1])
            end = int(args[2])
            self.chat_history.clear_messages_in_range(start, end)
            self.handle_chat_select()
    else:
        self.append_system_message(f"Unknown command '{command}")
