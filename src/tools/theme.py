from tkinter import ttk
from typing import Dict

dark_theme = {
    "bg": "#2f343f",  # Arc-Dark background
    "fg": "#d3dae3",  # Arc-Dark foreground
    "border_color": "#3b4048",
    "header_bg": "#353a45",
    "input_bg": "#3b4048",
    "input_fg": "#d3dae3",
    "input_border": "#3b4048",
    "button_bg": "#4c566a",
    "button_bg_hover": "#5e6a82",
    "button_fg": "#d3dae3",
    "button_border": "#4c566a",
    "button_danger_bg": "#bf616a",
    "button_danger_bg_hover": "#a54242",
    "button_danger_fg": "#ffffff",
    "list_bg": "#3b4048",
    "list_fg": "#d3dae3",
    "list_select_bg": "#4c566a",
    "list_select_fg": "#ffffff",
    "list_hover_bg": "#3b4048",
    "chat_bg": "#2f343f",
    "chat_fg": "#d3dae3",
    "chat_border": "#3b4048",
    "scrollbar_bg": "#3b4048",
    "scrollbar_fg": "#4c566a",
    "scrollbar_hover": "#5e6a82",
    "tree_bg": "#3b4048",
    "tree_fg": "#d3dae3",
    "tree_select_bg": "#4c566a",
    "tree_select_fg": "#ffffff",
    "menu_bg": "#353a45",
    "user": {"color_prefix": "#a3be8c", "bg": "#2f343f", "border": "#3b4048"},
    "assistant": {"color_prefix": "#81a1c1", "bg": "#2f343f", "border": "#3b4048"},
    "tool": {"color_prefix": "#e06c75", "bg": "#2f343f", "border": "#3b4048"},
}


def get_button_config(theme: Dict) -> Dict:
    # Configure buttons with common style
    return {
        "bg": theme["button_bg"],
        "fg": theme["button_fg"],
        "activebackground": theme["button_bg_hover"],
        "activeforeground": theme["button_fg"],
        "font": ("Arial", 12),
        "relief": "solid",
        "borderwidth": 1,
    }


def get_list_style(theme: Dict) -> ttk.Style:
    style = ttk.Style()
    style.configure(
        "Treeview",
        rowheight=36,
        font=("TkDefaultFont", 10),
        background=theme["tree_bg"],
        foreground=theme["tree_fg"],
        fieldbackground=theme["tree_bg"],
        selectbackground=theme["tree_select_bg"],
        selectforeground=theme["tree_select_fg"],
    )
    style.configure(
        "Treeview.Heading",
        background=theme["header_bg"],
        foreground=theme["fg"],
        relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", theme["button_bg_hover"])])
    return style
