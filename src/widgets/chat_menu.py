import tkinter as tk
from .llm_settings import open_llm_settings_dialog


def pad_label(label, width=30):
    """Pad a label to fixed width with spaces"""
    label_len = len(label)
    if label_len >= width:
        return label
    total_padding = width - label_len
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding
    return " " * left_padding + label + " " * right_padding


def add_chat_menu(self):
    """Adds chat menu"""

    self.menu_bar = tk.Menu(self.root)
    self.root.config(menu=self.menu_bar)

    self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.file_menu.add_command(
        label=pad_label("Save Chats"), command=self.save_chats_to_file
    )
    self.file_menu.add_command(
        label=pad_label("Load Chats"), command=self.load_chats_from_file
    )
    self.menu_bar.add_cascade(label="File", menu=self.file_menu)

    self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
    self.settings_menu.add_command(
        label=pad_label("LLM Settings"),
        command=lambda: open_llm_settings_dialog(self.root, self.llm_model),
    )
    self.settings_menu.add_command(
        label=pad_label("Change Theme"), command=self.load_theme
    )
    self.menu_bar.add_cascade(label="Settings", menu=self.settings_menu)

    if self.rag_model:
        self.rag_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.rag_menu.add_command(
            label=pad_label("Toggle RAG Editor"), command=self.toggle_rag_panel
        )
        self.menu_bar.add_cascade(label="RAG", menu=self.rag_menu)
    else:
        self.rag_menu = None
