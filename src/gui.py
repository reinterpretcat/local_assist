import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import json
from datetime import datetime
import threading
from typing import Optional

from .audio import AudioIO
from .models import STT, TTS
from .utils import print_system_message


class RoleTags:
    SYSTEM = "system_prefix"
    USER = "user_prefix"
    AI = "ai_prefix"

class ChatGPTUI:
    def __init__(self, root, stt_model: Optional[STT], tts_model: Optional[TTS]):
        self.root = root
        self.root.title("AI Assistance Chat")
        
        self.stt_model = stt_model
        self.tts_model = tts_model
        
        self.chat_history = []  # To store the conversation history
        self.chats = {"Default Chat": []}  # Default chat with empty history
        
        self.is_recording = False  # Tracks the recording state
        self.cancel_response = False  # Flag to cancel AI response
        
        self.listening_message_index = None # Tracks the position of the listening message
        self.audio_io = AudioIO()

        # Default theme (light mode)
        self.theme = {
            "bg": "#f7f7f8",
            "fg": "#000000",
            "input_bg": "#e8eaed",
            "input_fg": "#000000",
            "button_bg": "#10a37f",
            "button_fg": "#ffffff",
            "list_bg": "#ffffff",
            "list_fg": "#000000",
            "chat_bg": "#ffffff",
            "chat_fg": "#000000",
            "system": {
                "color_prefix": "red"
            },
            "ai": {
                "color_prefix": "green"
            },
            "user": {
                "color_prefix": "blue"
            }
        }

        # Configure layout
        self.root.geometry("2048x1436") 
        self.apply_theme()
        

        # Top menu for options
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)
        
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Save Chats", command=self.save_chats_to_file)
        file_menu.add_command(label="Load Chats", command=self.load_chats_from_file)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(label="Change Theme", command=self.load_theme)
        self.menu_bar.add_cascade(label="Settings", menu=settings_menu)

        # Main layout with two frames (main content + input frame)
        self.main_frame = tk.Frame(root, bg=self.theme["bg"])
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Left panel for chat list
        self.left_panel = tk.Frame(self.main_frame, width=200, bg=self.theme["bg"])
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)

        self.chat_list = tk.Listbox(
            self.left_panel,
            bg=self.theme["list_bg"],
            fg=self.theme["list_fg"],
            font=("Arial", 12),
            selectmode=tk.SINGLE,
        )
        self.chat_list.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_list.bind("<<ListboxSelect>>", self.load_selected_chat)

        tk.Button(
            self.left_panel,
            text="New Chat",
            command=self.new_chat,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        ).pack(padx=10, pady=5, fill=tk.X)
        tk.Button(
            self.left_panel,
            text="Rename",
            command=self.edit_chat_name,
            bg=self.theme["button_bg"],
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        ).pack(padx=10, pady=5, fill=tk.X)
        self.delete_button = tk.Button(
            self.left_panel,
            text="Delete Chat",
            command=self.delete_active_chat,
            bg="red",
            fg=self.theme["button_fg"],
            font=("Arial", 12),
        ).pack(padx=10, pady=5, fill=tk.X)
        
        
        # tk.Button(
        #     self.left_panel,
        #     text="Save Chat",
        #     command=self.save_chat,
        #     bg=self.theme["button_bg"],
        #     fg=self.theme["button_fg"],
        #     font=("Arial", 12),
        # ).pack(padx=10, pady=5, fill=tk.X)
        # tk.Button(
        #     self.left_panel,
        #     text="Load Chat",
        #     command=self.load_chat_from_file,
        #     bg=self.theme["button_bg"],
        #     fg=self.theme["button_fg"],
        #     font=("Arial", 12),
        # ).pack(padx=10, pady=5, fill=tk.X)

        # Right panel for chat display
        self.chat_display_frame = tk.Frame(self.main_frame, bg=self.theme["chat_bg"])
        self.chat_display_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat_display = tk.Text(
            self.chat_display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"],
            font=("Arial", 12),
        )
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # configure different colors for user and ai
        self.chat_display.tag_configure(RoleTags.USER, foreground=self.theme["user"]["color_prefix"], font=("Arial", 14, "bold"))
        self.chat_display.tag_configure(RoleTags.AI, foreground=self.theme["ai"]["color_prefix"], font=("Arial", 14, "bold"))
        self.chat_display.tag_configure(RoleTags.SYSTEM, foreground=self.theme["system"]["color_prefix"], font=("Arial", 14, "bold"))
        self.chat_display.tag_configure("message", foreground="black")
        
        
        self.update_chat_list()  # Populate the chat list
        self.load_chat("Default Chat")  # Automatically load the default chat

        # Input area at the bottom (outside main content frame)
        self.input_frame = tk.Frame(self.chat_display_frame, bg=self.theme["bg"], height=50)
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
                messagebox.showinfo("Theme Loaded", "Custom theme applied successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load theme: {e}")
                
    def disable_input(self):
        """Disable user input and send button."""
        self.user_input.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.record_button.config(state=tk.DISABLED)

    def enable_input(self):
        """Enable user input and send button."""
        self.user_input.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        self.record_button.config(state=tk.NORMAL)
        

    def update_theme(self):
        """Update the theme for all widgets."""
        self.apply_theme()
        self.left_panel.configure(bg=self.theme["bg"])
        self.chat_list.configure(bg=self.theme["list_bg"], fg=self.theme["list_fg"])
        self.chat_display.configure(bg=self.theme["chat_bg"], fg=self.theme["chat_fg"])
        self.input_frame.configure(bg=self.theme["bg"])
        self.user_input.configure(bg=self.theme["input_bg"], fg=self.theme["input_fg"])
        self.send_button.configure(bg=self.theme["button_bg"], fg=self.theme["button_fg"])

    # def save_chat(self):
    #     """Save the current chat history."""
    #     chat_name = simpledialog.askstring("Save Chat", "Enter a name to save this chat:", initialvalue="Chat " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    #     if chat_name:
    #         self.chats[chat_name] = self.chat_history[:]
    #         self.update_chat_list()
            
    # def save_chat(self):
    #     """Save the current chat history to the selected chat."""
    #     # Ensure a chat is selected
    #     selection = self.chat_list.curselection()
    #     if not selection:
    #         messagebox.showwarning("Save Chat", "Please select a chat to save.")
    #         return

    #     # Get the selected chat name
    #     selected_index = selection[0]
    #     chat_name = self.chat_list.get(selected_index)

    #     # Save the current chat history to the selected chat
    #     self.chats[chat_name] = self.chat_history[:]

    #     # Update the chat list to reflect any changes (e.g., sorting)
    #     self.update_chat_list()

    #     # Restore selection after updating the list
    #     new_index = list(self.chats.keys()).index(chat_name)
    #     self.chat_list.selection_set(new_index)

    #     messagebox.showinfo("Save Chat", f"Chat '{chat_name}' has been saved.")

            
            
            
    def load_chat(self, chat_name):
        """Load a specific chat into the main chat display."""
        # Switch to the selected chat's history
        self.chat_history = self.chats.get(chat_name, [])
    
        # Update the chat display
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)  # Clear the current display
        for message in self.chat_history:
            self.chat_display.insert(tk.END, f"{message['sender']}: {message['message']}\n")
        self.chat_display.config(state=tk.DISABLED)


    def load_selected_chat(self, event):
        """Load the selected chat into the chat display."""
        selection = self.chat_list.curselection()
        if selection:
            selected_chat = self.chat_list.get(selection)
            self.load_chat(selected_chat)
            
    def save_chats_to_file(self):
        """Save all chats to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(self.chats, file, ensure_ascii=False, indent=4)
                messagebox.showinfo("Save Chats", "All chats have been saved successfully.")
            except Exception as e:
                messagebox.showerror("Save Chats", f"Failed to save chats: {e}")

    def load_chats_from_file(self):
        """Load chats from a file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")]
        )
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

                messagebox.showinfo("Load Chats", "Chats have been loaded successfully.")
            except Exception as e:
                messagebox.showerror("Load Chats", f"Failed to load chats: {e}")


    # def load_chat_from_file(self):
    #     """Load a chat history from a file."""
    #     file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    #     if file_path:
    #         with open(file_path, "r", encoding="utf-8") as file:
    #             loaded_chat = json.load(file)
    #         chat_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    #         self.chats[chat_name] = loaded_chat
    #         self.update_chat_list()

    def update_chat_list(self):
        """Update the chat list display."""
        self.chat_list.delete(0, tk.END)
        for chat_name in sorted(self.chats.keys(), reverse=True):  # Sort by latest first
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
        new_name = simpledialog.askstring("Edit Chat Name", f"Rename '{old_name}' to:", initialvalue=old_name)
        if not new_name:
            return  # User canceled or entered nothing

        # Validate new name
        if new_name in self.chat_list.get(0, tk.END):
            messagebox.showerror("Edit Name", "A chat with this name already exists.")
            return

        # Update the chat name in the list
        self.chat_list.delete(selected_index)
        self.chat_list.insert(selected_index, new_name)
        self.chat_list.selection_set(selected_index)  # Keep the selection on the renamed chat

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
        confirm = messagebox.askyesno("Delete Chat", f"Are you sure you want to delete '{chat_name}'?")
        if confirm:
            # Delete the chat from the dictionary
            del self.chats[chat_name]

            # Refresh chat list
            self.update_chat_list()

            # Automatically select and load the first available chat
            if self.chats:
                first_chat = next(iter(self.chats))
                self.load_chat(first_chat)
            else:
                # Clear the display if no chats are left
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete(1.0, tk.END)
                self.chat_display.config(state=tk.DISABLED)
                self.chat_history = []


    def disable_chat_list(self):
        """Disable the chat list to prevent switching."""
        self.chat_list.config(state=tk.DISABLED)

    def enable_chat_list(self):
        """Enable the chat list after response generation."""
        self.chat_list.config(state=tk.NORMAL)




    def handle_user_input(self, event=None):
        """Handle user input and simulate AI reply."""
        user_message = self.user_input.get().strip()
        if not user_message:
            return
        
        self.user_input.delete(0, tk.END)
        
        # Handle special commands
        if user_message.startswith("/"):
            self.handle_command(user_message)
            return

        self.append_to_chat("You", user_message, RoleTags.USER)
        
         # Disable input and chat list while AI response is generating
        self.disable_input()
        self.disable_chat_list()
        
        # Change Send button to Cancel button
        self.cancel_response = False  # Reset cancel flag
        self.send_button.config(text="Cancel", command=self.cancel_ai_response, state=tk.NORMAL)

        # Start token-by-token AI response
        response_generator = self.generate_ai_response(user_message)
        self.root.after(100, self.display_ai_response, response_generator)
        

    def display_ai_response(self, generator):
        """Display AI response token by token."""
        
        
        if self.cancel_response:
            # Stop the AI response generation
            self.cancel_response = False  # Reset the flag
            self.append_to_chat_partial("AI", "(canceled)", RoleTags.AI)
            self.enable_input()  # Re-enable input
            self.enable_chat_list()  # Re-enable chat list
            self.send_button.config(text="Send", command=self.handle_user_input)  # Revert button text
            return
        
        try:
            token = next(generator)
            self.append_to_chat_partial("AI", token, RoleTags.AI)
            self.root.after(100, self.display_ai_response, generator)  # Schedule next token
        except StopIteration:
            # Add a newline when the response is complete
            # self.chat_display.config(state=tk.NORMAL)
            # self.chat_display.insert(tk.END, "\n")
            # self.chat_display.config(state=tk.DISABLED)
            # Re-enable input when AI response is complete
            self.enable_input()
            self.enable_chat_list()
            self.send_button.config(text="Send", command=self.handle_user_input)  # Revert button text
        
    def generate_ai_response(self, user_message):
        import time
        """Simulate token-by-token AI response generation."""
        response = f"Simulated response to: {user_message}. Here is a detailed explanation token by token."
        for token in response.split():
            yield token
            time.sleep(0.1)  # Simulate delay for each token
          
    def cancel_ai_response(self):
        """Cancel the ongoing AI response generation."""
        self.cancel_response = True  # Set the flag to stop token generation
        self.send_button.config(text="Send", command=self.handle_user_input)  # Revert button to Send
        self.enable_input()  # Re-enable inputs  
    
    def append_to_chat(self, sender, message, tag):
        """Append a message to the chat display."""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add a newline if the last character is not already a newline
        if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
            self.chat_display.insert(tk.END, "\n")
        
        
        self.chat_display.insert(tk.END, f"{sender}: ", tag)
        self.chat_display.insert(tk.END, f"{message}\n", "message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

        self.chat_history.append({"sender": sender, "message": message})


    def append_to_chat_partial(self, sender, token, tag):
        """Append a token to the chat display for partial updates."""
        self.chat_display.config(state=tk.NORMAL)

        # If it's the first token for AI, add the sender label
        if sender == "AI" and (not self.chat_history or self.chat_history[-1]["sender"] != "AI"):
            if not self.chat_display.get("end-2c", "end-1c").endswith("\n"):
               self.chat_display.insert(tk.END, "\n")
            self.chat_display.insert(tk.END, f"{sender}: ", tag)
            self.chat_history.append({"sender": sender, "message": ""})  # Add new history entry

        # Append the token to the display
        self.chat_display.insert(tk.END, f"{token} ")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # Auto-scroll

        # Update chat history
        if self.chat_history and self.chat_history[-1]["sender"] == sender:
            self.chat_history[-1]["message"] += f" {token}"
    
    def append_system_message(self, message):
        before = self.chat_display.index(tk.END)
        self.append_to_chat("System", message, RoleTags.SYSTEM)
        after = self.chat_display.index(tk.END)
        self.listening_message_index = (before, after)
        
    def remove_last_system_message(self):
        if self.listening_message_index:
            before, after = self.listening_message_index
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(before, after)
            
            self.chat_display.config(state=tk.DISABLED)
            self.listening_message_index = None


    # def get_ai_response(self, user_message):
    #     """Simulate an AI response (placeholder for real integration)."""
    #     return f"Simulated response to: {user_message}"

    def new_chat(self):
        """Start a new chat."""
        chat_name = simpledialog.askstring("New Chat", "Enter a name for this chat:")
        if chat_name:
            self.chat_history = []
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.chats[chat_name] = []
            self.update_chat_list()

    def save_chat(self):
        """Save the current chat history."""
        chat_name = simpledialog.askstring("Save Chat", "Enter a name to save this chat:", initialvalue="Chat " + datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        self.chat_history = [
           message for message in self.chat_history if message["message"] != "Listening for your voice..."
        ]
        
        if chat_name:
            self.chats[chat_name] = self.chat_history[:]
            self.update_chat_list()

    def load_selected_chat(self, event):
        """Load the selected chat into the chat display."""
        selection = self.chat_list.curselection()
        if selection:
            selected_chat = self.chat_list.get(selection)
            self.chat_history = self.chats.get(selected_chat, [])
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)

            # Reinsert messages with appropriate tags
            for message in self.chat_history:
                if message["sender"] == "You":
                    self.chat_display.insert(tk.END, "You: ", RoleTags.USER)
                elif message["sender"] == "AI":
                    self.chat_display.insert(tk.END, "AI: ", RoleTags.AI)
                self.chat_display.insert(tk.END, f"{message['message']}\n", "message")   


            self.chat_display.config(state=tk.DISABLED)

    def load_chat_from_file(self):
        """Load a chat history from a file."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as file:
                loaded_chat = json.load(file)
            chat_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.chats[chat_name] = loaded_chat
            self.update_chat_list()

    def update_chat_list(self):
        """Update the chat list display."""
        self.chat_list.delete(0, tk.END)
        for chat_name in sorted(self.chats.keys(), reverse=True):  # Sort by latest
            self.chat_list.insert(tk.END, chat_name)



    def record_voice(self):
        """Toggle recording state and handle recording."""
        if not self.is_recording:
            # Start recording
            self.is_recording = True
            self.record_button.config(text="🛑 Stop", bg="red")  # Change text and color
            self.start_recording()
        else:
            # Stop recording
            self.is_recording = False
            self.record_button.config(text="🎙️ Record", bg=self.theme["button_bg"])  # Revert to default
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

                self.append_to_chat("You", transcription, RoleTags.USER)

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
            self.chat_history = []  # Reset the history
        else:
            self.append_system_message(f"Unknown command '{command}")
