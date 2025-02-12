import tkinter as tk
from tkinter import ttk
from .widgets import *
from .styles import ThemeManager


class EditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor")

        self.main_container = tk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.set_geometry()

        self.theme_manager = ThemeManager()

        # Main container using PanedWindow
        self.main_paned = MainPanedWindow(
            self.main_container, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, sashwidth=2
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # Setup panels
        self.setup_side_panel()
        self.setup_middle_panel()
        self.setup_status_panel()

        self.side_panel.show_panel("file_tree")
        self.theme_manager.apply_theme("dark")

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

    def setup_side_panel(self):
        """Set up the left-side icon panel with working click events."""
        side_panel_width = 50
        self.side_panel = SidePanel(
            main_paned=self.main_paned, icon_panel_width=side_panel_width
        )
        self.main_paned.add(
            self.side_panel.icon_container,
            max_width=side_panel_width,
            minsize=side_panel_width,
        )
        self.main_paned.add(self.side_panel.content_container)

        # Icons
        self.side_panel.add_top_icon("🌐", "file_tree")
        self.side_panel.add_top_icon("💬", "chat")
        self.side_panel.add_bottom_icon("⚙️", "settings")
        self.side_panel.add_bottom_icon("❓", "help")

        # Panels
        self.side_panel.add_panel("file_tree", FileTreePanel(self.main_paned))
        self.side_panel.add_panel("chat", ChatPanel(self.main_paned))

    def setup_middle_panel(self):
        """Setup the middle panel with editor and bottom chat/console"""
        # Middle container for editor and bottom panel
        self.middle_paned = tk.PanedWindow(
            self.main_paned, orient=tk.VERTICAL, sashrelief=tk.RAISED, sashwidth=5
        )
        self.main_paned.add(self.middle_paned)

        # Setup editor
        self.editor_notebook = CustomNotebook(self.middle_paned)
        self.middle_paned.add(self.editor_notebook, stretch="always")

        # Add sample tabs
        self.add_tab("Tab 1")
        self.add_tab("Tab 2")

        # Setup bottom panel with chat/console
        self.bottom_panel = ttk.Frame(self.middle_paned, height=100)
        self.middle_paned.add(self.bottom_panel)

        # Chat/console input area
        self.chat_input_frame = ttk.Frame(self.bottom_panel)
        self.chat_input_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_input = tk.Text(
            self.chat_input_frame, height=3, wrap=tk.WORD, bg="white", fg="black"
        )
        self.chat_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_status_panel(self):
        """Setup the status panel at the bottom"""
        self.status_panel = ttk.Frame(self.main_container, height=20)
        self.status_panel.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(self.status_panel, text="Ready")
        self.status_label.pack(side=tk.LEFT)

    def add_tab(self, tab_name):
        """Add a new tab with content"""
        tab_frame = ttk.Frame(self.editor_notebook)
        self.editor_notebook.add(tab_frame, text=tab_name)

        # Add text widget to the tab
        text_widget = tk.Text(tab_frame)
        text_widget.pack(fill=tk.BOTH, expand=True)

        return tab_frame

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_theme = self.theme_manager.get_current_theme()
        if current_theme == "light":
            self.theme_manager.apply_theme("dark")
        elif current_theme == "dark":
            self.theme_manager.apply_theme("light")
        else:
            self.theme_manager.apply_theme("light")

    def set_theme(self, theme_name: str):
        """Set a specific theme"""
        self.theme_manager.apply_theme(theme_name)

    def run(self):
        """Start the application"""
        self.root.mainloop()
