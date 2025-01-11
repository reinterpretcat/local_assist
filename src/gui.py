from colorama import Fore
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText
import json
import threading
import logging
import time
from typing import Optional

from .models import LLM, STT, TTS, RAG
from .utils import print_system_message
from .tools import *
from .widgets import *


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
        self,
        root,
        config,
        llm_model: LLM,
        stt_model: Optional[STT],
        tts_model: Optional[TTS],
        rag_model: Optional[RAG],
    ):
        self.root = root
        self.root.title("AI Assistance Chat")

        self.config = config

        self.llm_model = llm_model
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.rag_model = rag_model

        self.tts_lock = threading.Lock()
        self.active_tts_threads = 0  # Counter for active TTS chunks

        self.chat_history = ChatHistory(on_history_changed=self.update_chat_display)

        # A flag to track whether tts is enabled or not
        self.tts_enabled = True if self.tts_model else False
        self.is_recording = False  # Tracks the recording state
        self.cancel_response = False  # Flag to cancel AI response
        self.markdown_enabled = False  # Flag for markdown post processing

        if self.tts_model:
            self.audio_io = AudioIO()

        self.theme = default_theme

        # Calculate window size based on screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set window size to 70% of screen size
        window_width = int(screen_width * 0.7)
        window_height = int(screen_height * 0.7)

        # Calculate position for center of screen
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2

        # Set geometry with format: 'widthxheight+x+y'
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

        min_width = int(screen_width * 0.3)  # 30% of screen width
        min_height = int(screen_height * 0.3)  # 30% of screen height
        self.root.minsize(min_width, min_height)

        # Main PanedWindow
        self.main_paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned_window.pack(fill=tk.BOTH, expand=True)

        left_panel_width = int(window_width * 0.25)  # 25% of window width
        min_left_panel_width = int(window_width * 0.15)  # 15% minimum

        # Set initial sash position
        def configure_sash(event=None):
            self.root.update_idletasks()
            self.main_paned_window.sash_place(0, left_panel_width, 0)
            # Set minimum size for the paned window sections
            self.main_paned_window.paneconfigure(
                self.left_panel,
                minsize=min_left_panel_width,
            )

        # Bind the configuration to when the window is fully loaded
        self.root.bind("<Map>", configure_sash)

        # Left panel for chat list and RAG
        self.left_panel = tk.Frame(self.main_paned_window)
        # self.left_panel.configure(width=600)  # Set minimum width
        self.left_panel.pack_propagate(False)  # Prevent the panel from shrinking
        self.main_paned_window.add(self.left_panel)

        self.chat_tree = ChatTree(
            self.left_panel,
            self.chat_history,
            on_chat_select=self.update_chat_display,
        )

        self.chat_menu = ChatMenu(
            self.root,
            on_save_chats_to_file=self.save_chats_to_file,
            on_load_chats_from_file=self.load_chats_from_file,
            on_llm_settings=lambda: open_llm_settings_dialog(
                self.root, self.theme, self.llm_model
            ),
            on_load_theme=self.load_theme,
            on_toggle_rag_panel=self.toggle_rag_panel if self.rag_model else None,
        )

        # RAG UI
        if self.rag_model:
            self.rag_panel = RAGManagementUI(
                self.left_panel, self.rag_model, on_chat_start=self.on_rag_chat_start
            )
            self.rag_panel.frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.rag_visible = True

        # Right panel for chat display
        self.chat_display_frame = tk.Frame(self.main_paned_window)
        self.main_paned_window.add(self.chat_display_frame)

        self.chat_display = ScrolledText(
            self.chat_display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Arial", 12),
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.chat_display.tag_configure(
            RoleTags.USER,
            foreground=self.theme["user"]["color_prefix"] if self.theme else "blue",
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(
            RoleTags.ASSISTANT,
            foreground=(
                self.theme["assistant"]["color_prefix"] if self.theme else "green"
            ),
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(
            RoleTags.TOOL,
            foreground=self.theme["tool"]["color_prefix"] if self.theme else "red",
            font=("Arial", 14, "bold"),
        )
        self.chat_display.tag_configure(RoleTags.CONTENT, foreground="black")

        # Input area at the bottom (outside main content frame)
        self.input_frame = tk.Frame(self.chat_display_frame, height=50)
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.input_holder = ChatInput(
            root=self,
            input_frame=self.input_frame,
            handle_user_input=self.handle_user_input,
        )
        self.user_input = self.input_holder.user_input

        self.record_button = tk.Button(
            self.input_frame,
            text="🎙️ Record",
            command=self.record_voice,
            font=("Arial", 12),
        )
        self.record_button.pack(side=tk.RIGHT, padx=(5, 5), pady=5)
        self.record_button.config(state=tk.NORMAL if self.tts_model else tk.DISABLED)

        self.send_button = tk.Button(
            self.input_frame,
            text="Send",
            command=self.handle_user_input,
            font=("Arial", 12),
        )
        self.send_button.pack(side=tk.RIGHT, padx=(5, 10), pady=5)
        self.root.bind("<Escape>", self.cancel_ai_response)

        self.apply_theme()
        setup_markdown_tags(self.chat_display, self.theme)
        # self.update_chat_list()
        # self.create_default_chat()
        self.toggle_rag_panel()

    def apply_theme(self):
        """Apply the current theme to the chat and rag window."""
        if self.theme:
            apply_app_theme(self)

    def load_theme(self):
        """Load a custom theme from a JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    self.theme = json.load(file)
                self.apply_theme()
                messagebox.showinfo(
                    "Theme Loaded", "Custom theme applied successfully!"
                )
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load theme: {e}")

    def disable_ui(self):
        """Disable user input."""
        self.user_input.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)

        self.chat_tree.disable()

    def enable_ui(self):
        """Enable user input."""
        self.user_input.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.NORMAL if self.tts_model else tk.DISABLED)

        self.chat_tree.enable()

    def handle_user_input(self, event=None):
        """Handle user input from input."""
        user_message = self.user_input.get("1.0", "end-1c").strip()
        if not user_message:
            return
        self.user_input.delete("1.0", tk.END)

        # Handle special commands
        if user_message.startswith("/"):
            handle_command(self, user_message)
            return

        self.handle_user_message(user_message)

    def handle_user_message(self, user_message):
        """Handle user message and initiate AI reply."""

        self.append_to_chat(RoleNames.USER, user_message)

        # Disable UI while AI response is generating
        self.disable_ui()

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
            if self.tts_model:
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
        self.enable_ui()  # Re-enable inputs

    def finish_ai_response(self):
        """Finalize the AI response display after generation and TTS complete."""
        self.enable_ui()
        self.send_button.config(text="Send", command=self.handle_user_input)

        last_message = self.chat_history.get_last_message()

        if last_message["role"] == RoleNames.ASSISTANT:
            last_message = last_message["content"]

            # Rerender the message in case of markdown syntax
            if self.markdown_enabled and has_markdown_syntax(last_message):
                self.chat_display.config(state=tk.NORMAL)

                tag_indices = self.chat_display.tag_ranges(RoleTags.ASSISTANT)
                if tag_indices:
                    start_index = tag_indices[-2]
                    self.chat_display.delete(start_index, tk.END)
                    if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
                        self.chat_display.insert(tk.END, "\n")
                    self.chat_display.insert(
                        tk.END, f"{RoleNames.ASSISTANT}: ", RoleTags.ASSISTANT
                    )
                    render_markdown(self.chat_display, last_message)

                self.chat_display.config(state=tk.DISABLED)

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
        if not self.tts_model or self.active_tts_threads == 0:
            self.cancel_response = False  # Reset the flag
            self.finish_ai_response()
        else:
            self.root.after(100, self.check_tts_completion)

    def append_to_chat(self, role, content):
        """Append a message to the chat display."""
        self.chat_display.config(state=tk.NORMAL)

        if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
            self.chat_display.insert(tk.END, "\n")

        self.chat_display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
        self.append_markdown(content)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

        self.chat_history.append_message(role, content)

    def append_to_chat_partial(self, role, token):
        """Append a token to the chat display for partial updates."""
        messages = self.chat_history.get_active_chat_messages()

        self.chat_display.config(state=tk.NORMAL)

        # If it's the first token for assistant, add the role label
        if role == RoleNames.ASSISTANT and (
            not messages or messages[-1]["role"] != RoleNames.ASSISTANT
        ):
            if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
                self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, f"{role}: ", RoleNames.to_tag(role))
            # Add new message to history
            self.chat_history.append_message(role, "")

        # Append the token to the display
        self.chat_display.insert(tk.END, f"{token}")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # Auto-scroll

        # Update the content of the last message
        messages = self.chat_history.get_active_chat_messages()
        if messages and messages[-1]["role"] == role:
            current_content = messages[-1]["content"]
            messages[-1]["content"] = current_content + token

    def update_chat_display(self):
        """Update chat display from history manager"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)

        messages = self.chat_history.get_active_chat_messages()
        for idx, message in enumerate(messages):
            if message["role"] == RoleNames.USER:
                self.chat_display.insert(tk.END, "You: ", RoleTags.USER)
            elif message["role"] == RoleNames.ASSISTANT:
                self.chat_display.insert(tk.END, "Assistant: ", RoleTags.ASSISTANT)
            elif message["role"] == RoleNames.TOOL:
                self.chat_display.insert(tk.END, "Tool: ", RoleTags.TOOL)

            elif idx == 0 and message["role"] == "system":
                print_system_message(
                    f"skip initial system message: {message}", color=Fore.LIGHTBLUE_EX
                )
                continue

            self.append_markdown(message["content"])

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.yview_moveto(1.0)

        # Update LLM model history if needed
        self.llm_model.load_history(messages)

        # Scroll to the end
        self.chat_display.yview_moveto(1.0)

    def append_markdown(self, text):
        if self.markdown_enabled:
            render_markdown(self.chat_display, text)
        else:
            self.chat_display.insert(tk.END, text + "\n")

    def append_system_message(self, message):
        self.append_to_chat(RoleNames.TOOL, message)

    def clear_messages(self):
        """Clear chat display."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def save_chats_to_file(self):
        """Save all chats to a file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                self.chat_history.save_chats(file_path)
                messagebox.showinfo(
                    "Save Chats", "All chats have been saved successfully."
                )
            except Exception as e:
                messagebox.showerror("Save Chats", f"Failed to save chats: {e}")

    def load_chats_from_file(self):
        """Load chats from a file"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    loaded_chats = json.load(file)

                self.chat_history.load_chats(loaded_chats)
                self.chat_tree.load_tree()
                self.clear_messages()

                messagebox.showinfo(
                    "Load Chats", "Chats have been loaded successfully."
                )
            except Exception as e:
                messagebox.showerror("Load Chats", f"Failed to load chats: {e}")

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
                text="🎙️ Record",
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
        if not self.tts_model:
            return

        try:
            self.audio_io.stop_recording()

        except AttributeError:
            print_system_message("No audio captured. Press record to try again.")

    def on_rag_chat_start(self, messages):
        """Handle the start of a RAG chat with initial messages"""
        if len(messages) != 2:
            messagebox.showerror("RAG Chat", f"Unexpected messages: {messages}.")
            return

        # Get currently selected chat, if any
        if self.chat_history.active_path:
            # Reset active chat with initial system message
            self.chat_history.set_active_chat_history(messages=[messages[0]])

            # Update display
            self.update_chat_display()

            # Process user's message
            self.handle_user_message(messages[1]["content"])
        else:
            messagebox.showerror(
                "RAG Chat",
                "No selected chat. Please select a chat before starting RAG.",
            )

    def toggle_rag_panel(self):
        """Toggle the visibility of the RAG panel."""
        if not self.rag_model:
            return

        if self.rag_visible:
            self.rag_panel.frame.pack_forget()
        else:
            self.rag_panel.frame.pack(fill=tk.BOTH, expand=True)
        self.rag_visible = not self.rag_visible
