from tkinter import ttk

dark_theme = {
    "bg": "#2f343f",  # Arc-Dark background
    "fg": "#d3dae3",  # Arc-Dark foreground
    "border_color": "#3b4048",
    "header_bg": "#3b4048",
    "input_bg": "#3b4048",
    "input_fg": "#d3dae3",
    "input_border": "#3b4048",
    "button_bg": "#4c566a",  # Arc-Dark button background
    "button_bg_hover": "#5e6a82",  # Arc-Dark button hover background
    "button_fg": "#d3dae3",  # Same as foreground color
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
    "user": {"color_prefix": "#81a1c1", "bg": "#2f343f", "border": "#3b4048"},
    "assistant": {"color_prefix": "#88c0d0", "bg": "#2f343f", "border": "#3b4048"},
    "tool": {"color_prefix": "#d3dae3", "bg": "#2f343f", "border": "#3b4048"},
}


def apply_app_theme(self):
    apply_chat_theme(self)
    if hasattr(self, "rag_panel"):
        self.rag_panel.theme = self.theme
        apply_rag_theme(self.rag_panel)


def apply_chat_theme(self):
    """Apply theme to main chat window components using provided theme dictionary"""

    # Configure root and main frames
    self.root.configure(bg=self.theme["bg"])
    self.main_paned_window.configure(
        bg=self.theme["bg"],
        sashwidth=4,
        sashpad=1,
        borderwidth=1,
        relief="solid",
    )

    # Configure menu
    self.menu_bar.configure(
        bg=self.theme["bg"],
        fg=self.theme["fg"],
        activebackground=self.theme["button_bg"],
        activeforeground=self.theme["button_fg"],
        borderwidth=0,
    )

    for menu in self.menu_bar.winfo_children():
        menu.configure(
            bg=self.theme["bg"],
            fg=self.theme["fg"],
            activebackground=self.theme["button_bg"],
            activeforeground=self.theme["button_fg"],
            selectcolor=self.theme["button_fg"],
        )

    # Configure left panel
    self.left_panel.configure(bg=self.theme["bg"], borderwidth=1, relief="solid")

    # Configure chat list
    self.chat_list.configure(
        bg=self.theme["list_bg"],
        fg=self.theme["list_fg"],
        selectbackground=self.theme["list_select_bg"],
        selectforeground=self.theme["list_select_fg"],
        highlightbackground=self.theme["chat_border"],
        font=("Arial", 12),
        relief="solid",
        borderwidth=1,
    )

    # Configure buttons
    button_config = {
        "bg": self.theme["button_bg"],
        "fg": self.theme["button_fg"],
        "activebackground": self.theme["button_bg_hover"],
        "activeforeground": self.theme["button_fg"],
        "font": ("Arial", 12),
        "relief": "solid",
        "borderwidth": 1,
    }

    for button in [
        self.new_chat_button,
        self.rename_button,
        self.compress_button,
        self.send_button,
        self.record_button,
        self.delete_button,
    ]:
        button.configure(**button_config)

    # Configure chat display frame
    self.chat_display_frame.configure(
        bg=self.theme["chat_bg"], borderwidth=1, relief="solid"
    )

    # Configure chat display
    self.chat_display.configure(
        bg=self.theme["chat_bg"],
        fg=self.theme["chat_fg"],
        font=("Arial", 12),
        insertbackground=self.theme["chat_fg"],
        selectbackground=self.theme["list_select_bg"],
        selectforeground=self.theme["list_select_fg"],
        highlightbackground=self.theme["chat_border"],
        relief="solid",
        borderwidth=1,
    )
    self.chat_display.vbar.configure(
        bg=self.theme["scrollbar_bg"],
        activebackground=self.theme["scrollbar_hover"],
        troughcolor=self.theme["scrollbar_bg"],
        width=12,
        elementborderwidth=0,
    )

    # Configure scrollbar
    self.input_holder.scrollbar.configure(
        bg=self.theme["scrollbar_bg"],
        activebackground=self.theme["scrollbar_hover"],
        troughcolor=self.theme["scrollbar_bg"],
        width=12,
    )

    # Configure input area
    self.input_frame.configure(bg=self.theme["bg"], relief="solid", borderwidth=1)

    self.user_input.configure(
        bg=self.theme["input_bg"],
        fg=self.theme["input_fg"],
        insertbackground=self.theme["input_fg"],
        font=("Arial", 12),
        relief="solid",
        borderwidth=1,
    )


def apply_rag_theme(self):
    """Apply theme to RAG panel components using provided theme dictionary"""
    # Configure frame and components
    self.frame.configure(bg=self.theme["bg"], borderwidth=1, relief="solid")
    self.collection_frame.configure(
        bg=self.theme["bg"], fg=self.theme["fg"], borderwidth=1, relief="solid"
    )
    self.data_store_frame.configure(
        bg=self.theme["bg"], fg=self.theme["fg"], borderwidth=1, relief="solid"
    )
    self.tree_frame.configure(bg=self.theme["bg"])

    # Configure buttons with common style
    button_config = {
        "bg": self.theme["button_bg"],
        "fg": self.theme["button_fg"],
        "activebackground": self.theme["button_bg_hover"],
        "activeforeground": self.theme["button_fg"],
        "font": ("Arial", 12),
        "relief": "solid",
        "borderwidth": 1,
    }

    for button in [
        self.new_collection_button,
        self.rename_collection_button,
        self.upload_button,
        self.context_button,
        self.delete_button,
    ]:
        button.configure(**button_config)

    # Configure scrollbar
    self.vsb.configure(
        bg=self.theme["scrollbar_bg"],
        activebackground=self.theme["scrollbar_hover"],
        troughcolor=self.theme["scrollbar_bg"],
        width=12,
    )

    # Apply custom styles
    style = ttk.Style()
    style.configure(
        "Treeview",
        rowheight=36,
        font=("TkDefaultFont", 10),
        background=self.theme["tree_bg"],
        foreground=self.theme["tree_fg"],
        fieldbackground=self.theme["tree_bg"],
        selectbackground=self.theme["tree_select_bg"],
        selectforeground=self.theme["tree_select_fg"],
    )
    style.configure(
        "Treeview.Heading",
        background=self.theme["header_bg"],
        foreground=self.theme["fg"],
        relief="flat",
    )
    style.map(
        "Treeview.Heading", background=[("active", self.theme["button_bg_hover"])]
    )
    # Apply styles to Treeview
    self.data_store_tree.configure(style="Treeview")

    # Apply theme to RAGQueryEditor components
    def editor_style_callback(editor):
        theme = self.theme

        editor.root.configure(bg=theme["bg"])

        editor.summary_label.configure(bg=theme["bg"], fg=theme["fg"])
        editor.summary_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        editor.context_label.configure(bg=theme["bg"], fg=theme["fg"])
        editor.context_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        editor.query_label.configure(bg=theme["bg"], fg=theme["fg"])
        editor.query_text.configure(
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )

        editor.progress_frame.configure(bg=theme["bg"])
        editor.progress_label.configure(bg=theme["bg"], fg=theme["fg"])
        editor.progress_bar.configure(
            style="Horizontal.TProgressbar"
        )  # Assuming ttk.Progressbar is used

        editor.button_frame.configure(bg=theme["bg"])
        editor.apply_button.configure(
            bg=theme["button_bg"],
            fg=theme["button_fg"],
            activebackground=theme["button_bg_hover"],
            activeforeground=theme["button_fg"],
            relief="solid",
            borderwidth=1,
        )

    self.editor_style_callback = editor_style_callback
