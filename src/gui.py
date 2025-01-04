from colorama import Fore
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import json
import threading
import logging
import time

from .audio import AudioIO
from .gui_rag import RAGManagementUI
from .models import LLM, STT, TTS, RAG
from .utils import compress_messages, print_system_message
from .settings import default_theme


class RoleTags:
    TOOL = "tool_prefix"
    USER = "user_prefix"
    ASSISTANT = "ai_prefix"
    CONTENT = "content_prefix"


class RoleNames:
    TOOL = "tool"
    USER = "user"
    ASSISTANT = "assistant"

    @staticmethod
    def to_tag(role) -> RoleTags:
        if role == RoleNames.ASSISTANT:
            return RoleTags.ASSISTANT
        elif role == RoleNames.USER:
            return RoleTags.USER

        return RoleTags.TOOL


class AIChatUI:
    def __init__(
        self, root, llm_model: LLM, stt_model: STT, tts_model: TTS, rag_model: RAG
    ):
        self.root = root
        self.root.title("AI Assistance Chat")

        self.llm_model = llm_model
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.rag_model = rag_model

        self.tts_lock = threading.Lock()
        self.active_tts_threads = 0  # Counter for active TTS chunks

        self.chats = {}
        self.chat_history = []  # To store the conversation history

        self.tts_enabled = True  # A flag to track whether tts is enabled or not
        self.is_recording = False  # Tracks the recording state
        self.cancel_response = False  #  Flag to cancel AI response

        self.listening_message_index = (
            None  # Tracks the position of the listening message
        )
        self.audio_io = AudioIO()

        self.theme = default_theme

        self.root.geometry("2048x1436")
        self.apply_theme()

        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Save Chats", command=self.save_chats_to_file)
        file_menu.add_command(label="Load Chats", command=self.load_chats_from_file)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(
            label="LLM Settings", command=self.open_llm_settings_dialog
        )
        settings_menu.add_command(label="Change Theme", command=self.load_theme)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)

        rag_menu = tk.Menu(self.menu_bar, tearoff=0)
        rag_menu.add_command(label="Manage RAG Data", command=self.toggle_rag_panel)
        self.menu_bar.add_cascade(label="RAG", menu=rag_menu)

        # Main PanedWindow
        self.main_paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True)

        # Left panel for chat list and RAG
        self.left_panel = tk.Frame(self.main_paned_window, bg=self.theme["bg"])
        self.main_paned_window.add(self.left_panel, minsize=200)

        # Chat list
        self.chat_list = tk.Listbox(
            self.left_panel,
            bg=self.theme["list_bg"],
            fg=self.theme["list_fg"],
            font=("Arial", 12),
            selectmode=tk.SINGLE,
        )
        self.chat_list.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_list.bind("<<ListboxSelect>>", self.load_selected_chat)

        self.new_chat_button = tk.Button(
            self.left_panel,
            text="New Chat",
            command=self.new_chat,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.new_chat_button.pack(padx=10, pady=5, fill=tk.X)

        self.rename_button = tk.Button(
            self.left_panel,
            text="Rename",
            command=self.edit_chat_name,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.rename_button.pack(padx=10, pady=5, fill=tk.X)

        self.compress_button = tk.Button(
            self.left_panel,
            text="Compress Chat",
            command=self.compress_active_chat,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.compress_button.pack(padx=10, pady=5, fill=tk.X)

        self.delete_button = tk.Button(
            self.left_panel,
            text="Delete Chat",
            command=self.delete_active_chat,
            bg="red",
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.delete_button.pack(padx=10, pady=5, fill=tk.X)

        # RAG UI
        self.rag_panel = RAGManagementUI(self.left_panel, self.rag_model)
        self.rag_panel.frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.rag_visible = True

        # Right panel for chat display
        self.chat_display_frame = tk.Frame(
            self.main_paned_window, bg=self.theme["chat_bg"]
        )
        self.main_paned_window.add(self.chat_display_frame, minsize=800)

        self.chat_display = tk.Text(
            self.chat_display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"],
            font=("Arial", 12),
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.chat_display.tag_configure(
            RoleTags.USER,
            foreground=self.theme["user"]["color_prefix"],
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(
            RoleTags.ASSISTANT,
            foreground=self.theme["assistant"]["color_prefix"],
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(
            RoleTags.TOOL,
            foreground=self.theme["tool"]["color_prefix"],
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(RoleTags.CONTENT, foreground="black")

        # Input area at the bottom (outside main content frame)
        self.input_frame = tk.Frame(
            self.chat_display_frame, bg=self.theme["bg"], height=50
        )
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.user_input = tk.Entry(
            self.input_frame,
            font=("Arial", 12),
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            relief=tk.FLAT,
            bd=5,
        )
        self.user_input.pack(side=tk.LEFT, padx=(10, 5), pady=5, fill=tk.X, expand=True)
        self.user_input.bind("<Return>", self.handle_user_input)

        self.record_button = tk.Button(
            self.input_frame,
            text="🎙️ Record",
            command=self.record_voice,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.record_button.pack(side=tk.RIGHT, padx=(5, 5), pady=5)

        self.send_button = tk.Button(
            self.input_frame,
            text="Send",
            command=self.handle_user_input,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        )
        self.send_button.pack(side=tk.RIGHT, padx=(5, 10), pady=5)
        self.root.bind("<Escape>", self.cancel_ai_response)

        self.update_chat_list()
        self.create_default_chat()
        self.toggle_rag_panel()

    def apply_theme(self):
        """Apply the current theme to the root window."""
        self.root.configure(bg=self.theme["bg"])

    def load_theme(self):
        """Load a custom theme from a JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    self.theme = json.load(file)
                self.update_theme()
                messagebox.showinfo(
                    "Theme Loaded", "Custom theme applied successfully!"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load theme: {e}")

    def disable_input(self):
        """Disable user input and send button."""
        self.user_input.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)
        self.compress_button.config(state=tk.DISABLED)

    def enable_input(self):
        """Enable user input and send button."""
        self.user_input.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.NORMAL)
        self.compress_button.config(state=tk.NORMAL)

    def update_theme(self):
        """Update the theme for all widgets."""
        self.apply_theme()
        self.left_panel.configure(bg=self.theme["bg"])
        self.chat_list.configure(bg=self.theme["list_bg"], fg=self.theme["list_fg"])
        self.chat_display.configure(bg=self.theme["chat_bg"], fg=self.theme["chat_fg"])
        self.input_frame.configure(bg=self.theme["bg"])
        self.user_input.configure(bg=self.theme["input_bg"], fg=self.theme["input_fg"])
        self.send_button.configure(
            bg=self.theme["button_bg"], fg=self.theme["button_fg"]
        )
        self.delete_button.configure(
            bg=self.theme["button_bg"], fg=self.theme["button_fg"]
        )
        self.rename_button.configure(
            bg=self.theme["button_bg"], fg=self.theme["button_fg"]
        )
        self.new_chat_button.configure(
            bg=self.theme["button_bg"], fg=self.theme["button_fg"]
        )

    def create_default_chat(self):
        """Create the default chat on app startup."""
        # Use new_chat logic to ensure consistency
        chat_name = "Default Chat"
        if chat_name not in self.chats:
            self.chats[chat_name] = [
                {
                    "role": RoleNames.TOOL,
                    "content": "Welcome to the chat with AI assistant! Use /help to list available meta commands.",
                }
            ]
            self.chat_history = self.chats[chat_name]
            self.update_chat_list()
            self.load_chat(chat_name)

    def load_chat(self, chat_name):
        """Load a specific chat into the main chat display."""
        # Switch to the selected chat's history
        self.chat_history = self.chats.get(chat_name, [])

        # Update the chat display
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)  # Clear the current display

        self.focus_on_chat(chat_name)
        self.user_input.focus_set()

        self.reinsert_messages_from_history()

    def save_chats_to_file(self):
        """Save all chats to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(self.chats, file, ensure_ascii=False, indent=4)
                messagebox.showinfo(
                    "Save Chats", "All chats have been saved successfully."
                )
            except Exception as e:
                messagebox.showerror("Save Chats", f"Failed to save chats: {e}")

    def load_chats_from_file(self):
        """Load chats from a file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    loaded_chats = json.load(file)

                # Replace existing chats with the loaded ones
                self.chats = loaded_chats

                # Refresh chat list
                self.update_chat_list()

                # Load the first chat automatically
                if self.chats:
                    first_chat = next(iter(self.chats))
                    self.load_chat(first_chat)

                messagebox.showinfo(
                    "Load Chats", "Chats have been loaded successfully."
                )
            except Exception as e:
                messagebox.showerror("Load Chats", f"Failed to load chats: {e}")

    def update_chat_list(self):
        """Update the chat list display."""
        self.chat_list.delete(0, tk.END)
        for chat_name in sorted(
            self.chats.keys(), reverse=True
        ):  # Sort by latest first
            self.chat_list.insert(tk.END, chat_name)

    def edit_chat_name(self):
        """Edit the selected chat's name."""
        selection = self.chat_list.curselection()
        if not selection:
            messagebox.showwarning("Edit Name", "Please select a chat to rename.")
            return

        # Get the currently selected chat name
        selected_index = selection[0]
        old_name = self.chat_list.get(selected_index)

        # Prompt for a new name
        new_name = simpledialog.askstring(
            "Edit Chat Name", f"Rename '{old_name}' to:", initialvalue=old_name
        )
        if not new_name:
            return  # User canceled or entered nothing

        # Validate new name
        if new_name in self.chat_list.get(0, tk.END):
            messagebox.showerror("Edit Name", "A chat with this name already exists.")
            return

        # Update the chat name in the list
        self.chat_list.delete(selected_index)
        self.chat_list.insert(selected_index, new_name)
        self.chat_list.selection_set(
            selected_index
        )  # Keep the selection on the renamed chat

        # Update the underlying chat data
        self.chats[new_name] = self.chats.pop(old_name)

    def delete_active_chat(self):
        """Delete the currently selected chat after confirmation."""
        selection = self.chat_list.curselection()
        if not selection:
            messagebox.showwarning("Delete Chat", "Please select a chat to delete.")
            return

        # Get the selected chat name
        selected_index = selection[0]
        chat_name = self.chat_list.get(selected_index)

        # Confirmation dialog
        confirm = messagebox.askyesno(
            "Delete Chat", f"Are you sure you want to delete '{chat_name}'?"
        )
        if confirm:
            # Delete the chat from the dictionary
            del self.chats[chat_name]

            # Check if any chats remain
            if not self.chats:
                # Automatically create a new default chat
                default_chat_name = "Default Chat"
                self.chats[default_chat_name] = []
                self.chat_history = []
                self.update_chat_list()
                self.load_chat(default_chat_name)
            else:
                # Refresh chat list and load the first available chat
                self.update_chat_list()
                first_chat = next(iter(self.chats))
                self.load_chat(first_chat)

    def focus_on_chat(self, chat_name):
        """Set focus on the given chat in the chat list."""
        try:
            chat_index = list(self.chats.keys()).index(chat_name)
            self.chat_list.selection_clear(0, tk.END)  # Clear any existing selection
            self.chat_list.selection_set(chat_index)  # Select the desired chat
            self.chat_list.see(chat_index)  # Ensure the chat is visible
        except ValueError:
            print_system_message(
                "cannot find chat: {chat_name}",
                log_level=logging.WARN,
                color=Fore.YELLOW,
            )

    def disable_chat_list(self):
        """Disable the chat list to prevent switching."""
        self.chat_list.config(state=tk.DISABLED)
        self.new_chat_button.config(state=tk.DISABLED)
        self.rename_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)

    def enable_chat_list(self):
        """Enable the chat list after response generation."""
        self.chat_list.config(state=tk.NORMAL)
        self.new_chat_button.config(state=tk.NORMAL)
        self.rename_button.config(state=tk.NORMAL)
        self.delete_button.config(state=tk.NORMAL)

    def handle_user_input(self, event=None):
        """Handle user input from input."""
        user_message = self.user_input.get().strip()
        if not user_message:
            return
        self.user_input.delete(0, tk.END)

        # Handle special commands
        if user_message.startswith("/"):
            self.handle_command(user_message)
            return

        self.handle_user_message(user_message)

    def handle_user_message(self, user_message):
        """Handle user message and initiate AI reply."""

        self.append_to_chat(RoleNames.USER, user_message)

        # Disable input and chat list while AI response is generating
        self.disable_input()
        self.disable_chat_list()

        # Change Send button to Cancel button
        self.cancel_response = False  # Reset cancel flag
        self.send_button.config(
            text="Cancel", command=self.cancel_ai_response, state=tk.NORMAL
        )

        # Start token-by-token AI response
        response_generator = self.generate_ai_response(user_message)
        self.root.after(100, self.display_ai_response, response_generator)

    def display_ai_response(self, generator):
        """Display AI response token by token."""
        if self.cancel_response:
            # Stop the AI response generation
            self.audio_io.stop_playing()
            self.append_to_chat_partial(RoleNames.ASSISTANT, "(canceled)")
            self.check_tts_completion()
            return

        try:
            token = next(generator)
            self.append_to_chat_partial(RoleNames.ASSISTANT, token)
            self.root.after(
                100, self.display_ai_response, generator
            )  # Schedule next token
        except StopIteration:
            self.check_tts_completion()

    def generate_ai_response(self, user_message):
        """Generate token-by-token AI response."""

        buffer = []
        min_chunk_size = 10
        splitters = [".", ",", "?", ":", ";"]

        for token in self.llm_model.forward(user_message):
            buffer.append(token)
            if token == "\n" or (len(buffer) >= min_chunk_size and token in splitters):
                chunk = "".join(buffer).strip()
                buffer.clear()

                if chunk:
                    # Queue this chunk for TTS processing
                    threading.Thread(
                        target=self.speak_text, args=(chunk,), daemon=True
                    ).start()

            yield token

        # Process any remaining text in buffer
        if buffer:
            chunk = "".join(buffer).strip()

            if chunk:
                threading.Thread(
                    target=self.speak_text, args=(chunk,), daemon=True
                ).start()

        self.check_tts_completion()

    def cancel_ai_response(self, event=None):
        """Cancel the ongoing AI response generation."""
        self.cancel_response = True  # Set the flag to stop token generation
        self.send_button.config(
            text="Send", command=self.handle_user_input
        )  # Revert button to Send
        self.enable_input()  # Re-enable inputs

    def speak_text(self, text):
        """Speak the given text using TTS."""

        if not self.tts_enabled:
            return

        with self.tts_lock:  # Ensure only one thread uses the TTS engine at a time
            self.active_tts_threads += 1
            try:
                synthesis = self.tts_model.forward(text)

            except Exception as e:
                print_system_message(
                    f"tts_model.forward exception: {e}",
                    color=Fore.RED,
                    log_level=logging.ERROR,
                )

            if synthesis:
                while self.audio_io.is_busy():
                    time.sleep(0.25)

                self.tts_model.model.synthesizer.save_wav(
                    wav=synthesis, path=self.tts_model.file_path
                )

                if self.cancel_response:
                    self.active_tts_threads -= 1
                    return

                self.audio_io.play_wav(self.tts_model.file_path)
                while self.audio_io.is_busy():
                    if self.cancel_response:  # Stop playback if canceled
                        self.audio_io.stop_playing()  # Stop the audio playback immediately
                        break
                    time.sleep(0.25)  # Poll for cancellation

            self.active_tts_threads -= 1

    def check_tts_completion(self):
        """Check if all TTS threads are complete and finalize response."""
        if self.active_tts_threads == 0:
            self.cancel_response = False  # Reset the flag
            self.finish_ai_response()
        else:
            self.root.after(100, self.check_tts_completion)

    def finish_ai_response(self):
        """Finalize the AI response display after generation and TTS complete."""
        self.enable_input()
        self.enable_chat_list()
        self.send_button.config(text="Send", command=self.handle_user_input)

    def append_to_chat(self, role, content):
        """Append a message to the chat display."""
        self.chat_display.config(state=tk.NORMAL)

        # Add a newline if the last character is not already a newline
        if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
            self.chat_display.insert(tk.END, "\n")

        self.chat_display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
        self.chat_display.insert(tk.END, f"{content}\n", RoleTags.CONTENT)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

        self.chat_history.append({"role": role, "content": content})

    def append_to_chat_partial(self, role, token):
        """Append a token to the chat display for partial updates."""
        self.chat_display.config(state=tk.NORMAL)

        # If it's the first token for assistant, add the role label
        if role == RoleNames.ASSISTANT and (
            not self.chat_history
            or self.chat_history[-1]["role"] != RoleNames.ASSISTANT
        ):
            if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
                self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
            self.chat_history.append(
                {"role": role, "content": ""}
            )  # Add new history entry

        # Append the token to the display
        self.chat_display.insert(tk.END, f"{token}")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # Auto-scroll

        # Update chat history
        if self.chat_history and self.chat_history[-1]["role"] == role:
            self.chat_history[-1]["content"] += f"{token}"

    def append_system_message(self, message):
        before = self.chat_display.index(tk.END)
        self.append_to_chat(RoleNames.TOOL, message)
        after = self.chat_display.index(tk.END)
        self.listening_message_index = (before, after)

    def remove_last_system_message(self):
        if self.listening_message_index:
            before, after = self.listening_message_index
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(before, after)

            self.chat_display.config(state=tk.DISABLED)
            self.listening_message_index = None

    def new_chat(self):
        """Start a new chat."""
        chat_name = simpledialog.askstring("New Chat", "Enter a name for this chat:")
        if chat_name and chat_name not in self.chats:
            self.chats[chat_name] = [
                {"role": RoleNames.TOOL, "content": "Welcome to your new chat!"}
            ]
            self.chat_history = self.chats[chat_name]

            # Update chat list and focus on the new chat
            self.update_chat_list()
            self.load_chat(chat_name)
        elif chat_name in self.chats:
            messagebox.showerror("New Chat", "A chat with this name already exists.")

    def load_selected_chat(self, event):
        """Load the selected chat into the chat display."""
        selection = self.chat_list.curselection()
        if selection:
            selected_chat = self.chat_list.get(selection)
            self.chat_history = self.chats.get(selected_chat, [])
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)

            self.reinsert_messages_from_history()

    def update_chat_list(self):
        """Update the chat list display."""
        self.chat_list.delete(0, tk.END)
        for chat_name in sorted(self.chats.keys(), reverse=True):  # Sort by latest
            self.chat_list.insert(tk.END, chat_name)

    def reinsert_messages_from_history(self):
        """Reinsert messages with appropriate tags."""
        for message in self.chat_history:
            if message["role"] == RoleNames.USER:
                self.chat_display.insert(tk.END, "You: ", RoleTags.USER)
            elif message["role"] == RoleNames.ASSISTANT:
                self.chat_display.insert(tk.END, "Assistant: ", RoleTags.ASSISTANT)
            elif message["role"] == RoleNames.TOOL:
                self.chat_display.insert(tk.END, "Tool: ", RoleTags.TOOL)

            self.chat_display.insert(
                tk.END, f"{message['content']}\n", RoleTags.CONTENT
            )

        self.chat_display.config(state=tk.DISABLED)
        self.llm_model.load_history(self.chat_history)

    def compress_active_chat(self):
        """Compress chat history for the selected chat or all chats."""
        selection = self.chat_list.curselection()
        if selection:
            # Compress the selected chat's history
            selected_chat = self.chat_list.get(selection)
            if selected_chat in self.chats:
                self.chats[selected_chat] = compress_messages(self.chats[selected_chat])
                self.llm_model.load_history(self.chats[selected_chat])  # Sync with LLM
                self.load_chat(selected_chat)  # Refresh the chat display
                messagebox.showinfo(
                    "Compress Chat",
                    f"Chat history for '{selected_chat}' compressed successfully!",
                )
            else:
                messagebox.showerror("Compress Chat", "Selected chat not found.")

    def record_voice(self):
        """Toggle recording state and handle recording."""

        self.record_button.focus_set()

        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.record_button.config(text="🛑 Stop", bg="red")  # Change text and color
            self.start_recording()
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.config(
                text="🎙️ Record", bg=self.theme["button_bg"]
            )  # Revert to default
            self.stop_recording()

    def start_recording(self):
        """Start recording in a separate thread."""
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def record_audio(self):
        """Capture audio using the microphone."""
        self.append_system_message("Listening for your voice...")

        try:
            audio_data = self.audio_io.record_audio()
            if audio_data is not None:
                print_system_message("Transcribing audio...")

                transcription = self.stt_model.forward(audio_data)

                self.handle_user_message(transcription)

        except Exception as e:
            print_system_message(f"Recording error: {e}")

    def stop_recording(self):
        """Stop recording and process the audio."""
        try:
            self.audio_io.stop_recording()
            self.remove_last_system_message()

        except AttributeError:
            print_system_message("No audio captured. Press record to try again.")

    def handle_command(self, command):
        if command == "/clear":
            # Clear all messages from the chat window
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)  # Remove all text
            self.chat_display.config(state=tk.DISABLED)

            # Reset the history
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
                # No argument provided, show help
                self.append_system_message(
                    "Syntax for TTS commands:\n"
                    "/tts on  - Enable text-to-speech\n"
                    "/tts off - Disable text-to-speech\n"
                    "/tts      - Show this help message",
                )
            elif len(args) == 2:
                if args[1] == "on":
                    self.tts_enabled = True
                    self.append_system_message("Text-to-speech enabled.")
                elif args[1] == "off":
                    self.tts_enabled = False
                    self.append_system_message("Text-to-speech disabled.")
                else:
                    # Invalid argument, show help
                    self.append_system_message(
                        f"Invalid argument '{args[1]}'. Use /tts on, /tts off",
                    )
            else:
                # Too many arguments, show help
                self.append_system_message(
                    "Too many arguments. Use /tts on, /tts off",
                )
        elif command == "/help":
            self.append_system_message(
                "Available commands:\n"
                "/clear - Clear the chat history\n"
                "/tts   - Manage text-to-speech (use '/tts' for detailed options)\n"
                "/help  - Display this help message",
            )
        else:
            self.append_system_message(f"Unknown command '{command}")

    def toggle_rag_panel(self):
        """Toggle the visibility of the RAG panel."""
        if self.rag_visible:
            self.rag_panel.frame.pack_forget()
        else:
            self.rag_panel.frame.pack(fill=tk.BOTH, expand=True)
        self.rag_visible = not self.rag_visible

    def open_llm_settings_dialog(self):
        """Open a dialog to set LLM settings."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("LLM System Prompt")

        current_prompt = self.llm_model.system_prompt

        # System Prompt
        tk.Label(
            settings_window, text="System Prompt:", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        prompt_text = tk.Text(settings_window, wrap=tk.WORD, height=8, width=50)
        prompt_text.insert(tk.END, current_prompt)
        prompt_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Save Button
        def save_settings():
            self.llm_model.set_system_prompt(prompt_text.get(1.0, tk.END).strip())
            settings_window.destroy()

        tk.Button(
            settings_window, text="Save", command=save_settings, bg="green", fg="white"
        ).pack(pady=10)

        # Center the settings window
        settings_window.transient(self.root)
        settings_window.grab_set()
        settings_window.wait_window(settings_window)
