import tkinter as tk
from tkinter import ttk

from .collapsible_panel import CollapsiblePanelManager


class SidePanel(ttk.Frame):
    def __init__(self, main_paned: ttk.PanedWindow, icon_panel_width: int):
        super().__init__(main_paned, width=icon_panel_width)

        self.main_paned = main_paned
        self.panels = {}
        self.current_panel = None
        self.current_position = None
        self.icon_panel_width = icon_panel_width

        self.icon_container = self

        self.top_group = ttk.Frame(self.icon_container)
        self.top_group.pack(side=tk.TOP, fill=tk.Y, pady=(10, 5))

        self.bottom_group = ttk.Frame(self.icon_container)
        self.bottom_group.pack(side=tk.BOTTOM, fill=tk.Y, pady=(5, 10))

        self.content_container = ttk.Frame(self.main_paned)
        self.content_container.configure(width=0)  # Initially hidden

    def add_panel(self, name, panel):
        """Add a panel to the manager without immediately displaying it."""
        self.panels[name] = panel
        panel.pack_forget()

    def show_panel(self, name):
        """Show the specified panel while hiding others."""
        if name not in self.panels:
            return

        if self.current_panel == name:
            self.hide_current_panel()
            return

        # Hide current panel if any
        if self.current_panel:
            self.panels[self.current_panel].pack_forget()

        # Show new panel
        panel = self.panels[name]
        panel.pack(in_=self.content_container, fill=tk.BOTH, expand=True)
        self.current_panel = name

        if hasattr(panel, "on_shown"):
            panel.on_shown()

        if self.current_position:
            self.main_paned.sashpos(1, self.current_position)

    def hide_current_panel(self):
        """Hide current panel by collapsing container width."""
        if self.current_panel:
            self.panels[self.current_panel].pack_forget()
            self.content_container.configure(width=0)
            self.current_panel = None

            self.current_position = self.main_paned.sashpos(1)
            self.main_paned.sashpos(1, self.icon_panel_width)

    def add_top_icon(self, text, name):
        self._create_icon(self.top_group, text, name)

    def add_bottom_icon(self, text, name):
        self._create_icon(self.bottom_group, text, name)

    def on_icon_click(self, panel_name):
        if self.current_panel == panel_name:
            self.hide_current_panel()
        else:
            self.show_panel(panel_name)

    def _create_icon(self, parent, text, name):
        btn = ttk.Button(
            parent, text=text, width=3, command=lambda: self.on_icon_click(name)
        )
        btn.pack(pady=5)


class FileTreePanel(tk.PanedWindow):
    def __init__(self, main_paned):
        super().__init__(
            main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5
        )
        self.file_tree = ttk.Treeview(self)
        self.add(self.file_tree)
        self.populate_file_tree()

        # Create collapsible panels
        self.collapsible_container = ttk.Frame(self)
        self.add(self.collapsible_container)

        self.panel_manager = CollapsiblePanelManager(self.collapsible_container, self)

        self.panel_manager.create_panel(
            "OUTLINE",
            lambda content: ttk.Treeview(content, show="tree", height=5),
            row=0,
        )
        self.panel_manager.create_panel(
            "TIMELINE",
            lambda content: ttk.Label(
                content,
                text="Recent Changes:\n• Added new feature\n• Fixed bug\n• Updated UI",
                justify=tk.LEFT,
            ),
            row=1,
        )

    def populate_file_tree(self):
        """Populate the file tree with sample items"""
        root_item = self.file_tree.insert("", "end", text="Project", open=True)
        self.file_tree.insert(root_item, "end", text="src")
        self.file_tree.insert(root_item, "end", text="README.md")

    def on_shown(self):
        self.panel_manager.update_layout()


class ChatPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.chat_history = tk.Text(self, wrap=tk.WORD)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.input = tk.Text(self.input_frame, height=3, wrap=tk.WORD)
        self.input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.send_button = ttk.Button(
            self.input_frame, text="Send", command=self.send_message
        )
        self.send_button.pack(side=tk.RIGHT, padx=5)

    def send_message(self):
        message = self.input.get("1.0", tk.END).strip()
        if message:
            self.chat_history.insert(tk.END, f"You: {message}\n\n")
            self.input.delete("1.0", tk.END)
