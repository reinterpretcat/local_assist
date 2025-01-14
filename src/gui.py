from colorama import Fore
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import threading
import logging
import time
from typing import Optional

from .models import *
from .tools import *
from .widgets import *
from .utils import print_system_message


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
        self.theme = default_theme

        self.llm_model = llm_model
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.rag_model = rag_model

        self.tts_lock = threading.Lock()
        self.active_tts_threads = 0  # Counter for active TTS chunks

        self.history_path = self.config.get("chat", {}).get("history_path", {})
        self.chat_history = ChatHistory(
            history_path=self.history_path,
            history_sort=self.config.get("chat", {}).get("history_sort", False),
        )

        # A flag to track whether tts is enabled or not
        self.tts_enabled = True if self.tts_model else False
        self.is_recording = False  # Tracks the recording state
        self.cancel_response = False  # Flag to cancel AI response

        if self.tts_model:
            self.audio_io = AudioIO()

        # Main container for all elements
        self.main_container = tk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        window_width, _ = self.set_geometry()

        # Container for PanedWindow
        self.paned_container = tk.Frame(self.main_container)
        self.paned_container.pack(fill=tk.BOTH, expand=True)

        # PanedWindow inside its container
        self.main_paned_window = tk.PanedWindow(
            self.paned_container, orient=tk.HORIZONTAL
        )
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

        def save_chat_history(event=None):
            # silently save to self.config.chat.history_path if defined, otherwise show save dialog
            if self.history_path:
                self.chat_history.save_chats(self.history_path)
            else:
                self.save_chats_to_file()

        self.root.bind("<Control-s>", save_chat_history)

        # Left panel for chat list and RAG
        self.left_panel = tk.Frame(self.main_paned_window)
        self.left_panel.pack_propagate(False)
        self.main_paned_window.add(self.left_panel)

        # ChatTree UI
        self.chat_tree = ChatTree(
            self.left_panel,
            self.chat_history,
            on_chat_select=self.handle_chat_select,
        )

        # RAG UI
        if self.rag_model:
            self.rag_panel = RAGManagementUI(
                self.left_panel, self.rag_model, on_chat_start=self.on_rag_chat_start
            )
            self.rag_panel.toggle()

        self.chat_menu = ChatMenu(
            self.root,
            on_save_chats_to_file=self.save_chats_to_file,
            on_load_chats_from_file=self.load_chats_from_file,
            on_llm_settings=lambda: open_llm_settings_dialog(
                self.root,
                self.theme,
                self.llm_model,
                on_complete=lambda: self.update_status_message(
                    message="LLM settings changed."
                ),
            ),
            on_load_theme=self.load_theme,
            on_toggle_rag_panel=self.rag_panel.toggle if self.rag_model else None,
        )

        # Right panel for chat display
        self.chat_display_frame = tk.Frame(self.main_paned_window)
        self.main_paned_window.add(self.chat_display_frame)

        self.chat_display = ChatDisplay(
            parent=self.chat_display_frame,
            markdown_enabled=False,
        )

        # Add toolbar after chat display but before input frame
        self.chat_toolbar = ChatToolBar(
            parent=self.chat_display_frame,
            chat_display=self.chat_display,
            chat_history=self.chat_history,
            on_chat_change=self.handle_chat_select,
        )

        # Input area at the bottom (outside main content frame)
        self.input_frame = tk.Frame(self.chat_display_frame, height=50)
        self.input_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.chat_input = ChatInput(
            root=self,
            input_frame=self.input_frame,
            on_user_input=self.handle_user_input,
            on_record_voice=self.record_voice if self.tts_enabled else None,
            on_cancel_response=self.cancel_ai_response,
        )

        # Status bar at bottom of main container
        self.chat_statusbar = ChatStatusBar(self.main_container)
        self.chat_statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.chat_statusbar.update_model_info(self.llm_model.model_id)

        self.root.bind("<Escape>", self.cancel_ai_response)

        self.apply_theme(self.theme)

    def load_theme(self):
        """Load a custom theme from a JSON file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    self.theme = json.load(file)

                self.apply_theme(theme=self.theme)
                self.update_status_message(message="Theme loaded.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load theme: {e}")

    def disable_ui(self):
        """Disable user input."""
        self.chat_input.disable()
        self.chat_tree.disable()

    def enable_ui(self):
        """Enable user input."""
        self.chat_input.enable()
        self.chat_tree.enable()

    def set_geometry(self):
        """Sets geometry and other properties."""
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

        return window_width, window_height

    def handle_user_input(self, user_message):
        """Handle user input from input."""

        # Handle special commands
        if user_message.startswith("/"):
            handle_command(self, user_message)
            return

        self.handle_user_message(user_message)

    def handle_user_message(self, message):
        """Handle user message and initiate AI reply."""

        self.chat_display.append_message(RoleNames.USER, message)
        self.chat_history.append_message(RoleNames.USER, message)
        self.update_statistics()

        # Disable UI while AI response is generating
        self.disable_ui()
        self.cancel_response = False

        # Start token-by-token AI response
        response_generator = self.generate_ai_response(message)
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
            self.root.after(100, self.display_ai_response, generator)
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
        self.enable_ui()  # Re-enable inputs

    def finish_ai_response(self):
        """Finalize the AI response display after generation and TTS complete."""
        self.enable_ui()

        last_message = self.chat_history.get_last_message()
        self.chat_display.handle_response_readiness(last_message)
        self.update_statistics()

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

    def append_to_chat_partial(self, role, token):
        """Append a token to the chat display for partial updates."""
        messages = self.chat_history.get_active_chat_messages()

        # If it's the first token for assistant
        is_first_token = RoleNames.ASSISTANT and (
            not messages or messages[-1]["role"] != RoleNames.ASSISTANT
        )

        self.chat_display.append_partial(role, token, is_first_token)
        self.chat_history.append_message_partial(role, token, is_first_token)

    def handle_chat_select(self):
        """Update chat display from history manager"""
        messages = self.chat_history.get_active_chat_messages()
        self.chat_statusbar.update_chat_info(self.chat_history.active_path[-1])
        self.update_statistics()
        self.chat_display.update(messages)
        self.llm_model.load_history(messages)

    def append_system_message(self, message):
        self.chat_display.append_message(RoleNames.TOOL, message)
        self.chat_history.append_message(RoleNames.TOOL, message)

    def update_statistics(self):
        """Updates statistics on status bar."""
        messages = self.chat_history.get_active_chat_messages()
        self.chat_statusbar.update_stats(messages)

    def save_chats_to_file(self):
        """Save all chats to a file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                self.chat_history.save_chats(file_path)
                self.history_path = file_path
                self.update_status_message(message="Chats saved.")
            except Exception as e:
                messagebox.showerror("Save Chats", f"Failed to save chats: {e}")

    def load_chats_from_file(self):
        """Load chats from a file"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            try:
                self.chat_history.load_chats(file_path)
                self.chat_tree.load_tree()
                self.chat_tree.expand_to_path(self.chat_history.active_path)
                self.chat_display.clear()

                messages = self.chat_history.get_active_chat_messages()
                self.llm_model.load_history(messages)

                self.history_path = file_path
                self.update_status_message(message="Chats loaded.")
            except Exception as e:
                messagebox.showerror("Load Chats", f"Failed to load chats: {e}")

    def record_voice(self):
        """Toggle recording state and handle recording."""

        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.start_recording()
        else:
            # Stop recording
            self.is_recording = False
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

    def update_status_message(self, message):
        self.chat_statusbar.update_system_msg(message=message)

    def on_rag_chat_start(self, messages):
        """Handle the start of a RAG chat with initial messages"""
        if len(messages) != 2:
            messagebox.showerror("RAG Chat", f"Unexpected messages: {messages}.")
            return

        # Get currently selected chat, if any
        if self.chat_history.active_path:
            # Reset active chat with initial system message
            messages = [messages[0]]
            self.chat_history.set_active_chat_history(messages)
            self.chat_display.update(messages)

            # Process user's message
            self.handle_user_message(messages[1]["content"])
        else:
            messagebox.showerror(
                "RAG Chat",
                "No selected chat. Please select a chat before starting RAG.",
            )

    def apply_theme(self, theme):
        # Configure root and main frames
        self.root.configure(bg=theme["bg"])
        self.main_paned_window.configure(
            bg=theme["bg"],
            sashwidth=4,
            sashpad=1,
            borderwidth=1,
            relief="solid",
        )

        # Configure chat display frame
        self.chat_display_frame.configure(
            bg=theme["chat_bg"], borderwidth=1, relief="solid"
        )

        # Configure left panel
        self.left_panel.configure(bg=theme["bg"], borderwidth=1, relief="solid")

        # Configure input area
        self.input_frame.configure(bg=theme["bg"], relief="solid", borderwidth=1)

        self.chat_display.apply_theme(theme)
        self.chat_input.apply_theme(theme)
        self.chat_menu.apply_theme(theme)
        self.chat_tree.apply_theme(theme)
        self.chat_toolbar.apply_theme(theme)
        self.chat_statusbar.apply_theme(theme)
        if self.rag_model:
            self.rag_panel.apply_theme(theme)
