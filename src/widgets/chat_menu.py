import tkinter as tk
from typing import Callable, Optional, Dict


def pad_label(label, width=30):
    """Pad a label to fixed width with spaces"""
    label_len = len(label)
    if label_len >= width:
        return label
    total_padding = width - label_len
    left_padding = total_padding // 2
    right_padding = total_padding - left_padding
    return " " * left_padding + label + " " * right_padding


class ChatMenu:
    def __init__(
        self,
        root,
        on_save_chats_to_file: Callable,
        on_load_chats_from_file: Callable,
        on_llm_settings: Callable,
        on_load_theme: Callable,
        on_code_editor: Callable,
        on_toggle_rag_panel: Optional[Callable],
    ):
        """Adds chat menu"""

        self.root = root
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(
            label=pad_label("Save Chats"), command=on_save_chats_to_file
        )
        self.file_menu.add_command(
            label=pad_label("Load Chats"), command=on_load_chats_from_file
        )
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.settings_menu.add_command(
            label=pad_label("LLM Settings"),
            command=on_llm_settings,
        )
        self.settings_menu.add_command(
            label=pad_label("Change Theme"), command=on_load_theme
        )
        self.menu_bar.add_cascade(label="Settings", menu=self.settings_menu)

        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        if on_toggle_rag_panel:
            self.tools_menu.add_command(
                label=pad_label("Toggle RAG Editor"), command=on_toggle_rag_panel
            )

        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(
            label=pad_label("Show Code Editor"), command=on_code_editor
        )

    def apply_theme(self, theme: Dict):
        self.theme = theme
        # Configure menu
        self.menu_bar.configure(
            bg=theme["menu_bg"],
            fg=theme["fg"],
            activebackground=theme["button_bg"],
            activeforeground=theme["button_fg"],
            borderwidth=0,
        )

        for menu in self.menu_bar.winfo_children():
            menu.configure(
                bg=theme["menu_bg"],
                fg=theme["fg"],
                activebackground=theme["button_bg"],
                activeforeground=theme["button_fg"],
                selectcolor=theme["button_fg"],
            )
