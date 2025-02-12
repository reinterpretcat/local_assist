from typing import Dict, Optional
import tkinter as tk
from tkinter import ttk


class ThemeColors:
    def __init__(self, colors: Dict[str, str]):
        # Base colors
        self.background = colors.get("background", "#ffffff")
        self.foreground = colors.get("foreground", "#000000")

        # UI element colors
        self.panel_background = colors.get("panel_background", self.background)
        self.panel_foreground = colors.get("panel_foreground", self.foreground)
        self.border = colors.get("border", "#cccccc")
        self.hover = colors.get("hover", "#e5e5e5")
        self.selection = colors.get("selection", "#0078d4")
        self.selection_inactive = colors.get("selection_inactive", "#e5e5e5")

        # Text colors
        self.text_background = colors.get("text_background", self.background)
        self.text_foreground = colors.get("text_foreground", self.foreground)
        self.text_disabled = colors.get("text_disabled", "#6d6d6d")

        # Control colors
        self.button_background = colors.get("button_background", self.panel_background)
        self.button_foreground = colors.get("button_foreground", self.panel_foreground)
        self.input_background = colors.get("input_background", self.background)
        self.input_foreground = colors.get("input_foreground", self.foreground)

        # Status colors
        self.status_background = colors.get("status_background", "#007acc")
        self.status_foreground = colors.get("status_foreground", "#ffffff")


class ThemeManager:
    def __init__(self):
        self.current_theme: Optional[str] = None
        self._themes: Dict[str, ThemeColors] = {}
        self._style = ttk.Style()
        self._configure_base_styles()

        # Register default themes
        self.register_theme("light", self._create_light_theme())
        self.register_theme("dark", self._create_dark_theme())

    def _configure_base_styles(self):
        """Configure base styles that are common across themes"""
        self._style.layout("Collapsible.TFrame", [("Frame.border", {"sticky": "nswe"})])

        self._style.layout("StatusBar.TFrame", [("Frame.border", {"sticky": "nswe"})])

    def _create_light_theme(self) -> ThemeColors:
        return ThemeColors(
            {
                "background": "#ffffff",
                "foreground": "#000000",
                "panel_background": "#f3f3f3",
                "panel_foreground": "#333333",
                "border": "#cccccc",
                "hover": "#e5e5e5",
                "selection": "#0078d4",
                "selection_inactive": "#e5e5e5",
                "text_background": "#ffffff",
                "text_foreground": "#000000",
                "text_disabled": "#6d6d6d",
                "button_background": "#ffffff",
                "button_foreground": "#000000",
                "input_background": "#ffffff",
                "input_foreground": "#000000",
                "status_background": "#007acc",
                "status_foreground": "#ffffff",
            }
        )

    def _create_dark_theme(self) -> ThemeColors:
        return ThemeColors(
            {
                "background": "#1e1e1e",
                "foreground": "#d4d4d4",
                "panel_background": "#252526",
                "panel_foreground": "#cccccc",
                "border": "#454545",
                "hover": "#2a2d2e",
                "selection": "#264f78",
                "selection_inactive": "#3c3c3c",
                "text_background": "#1e1e1e",
                "text_foreground": "#d4d4d4",
                "text_disabled": "#6d6d6d",
                "button_background": "#252526",
                "button_foreground": "#cccccc",
                "input_background": "#3c3c3c",
                "input_foreground": "#cccccc",
                "status_background": "#007acc",
                "status_foreground": "#ffffff",
            }
        )

    def register_theme(self, name: str, theme: ThemeColors):
        """Register a new theme"""
        self._themes[name] = theme

    def apply_theme(self, theme_name: str):
        """Apply a theme to the application"""
        if theme_name not in self._themes and theme_name != "system":
            raise ValueError(f"Theme '{theme_name}' not found")

        self.current_theme = theme_name

        if theme_name == "system":
            self._style.theme_use("default")
            return

        theme = self._themes[theme_name]

        self._style.configure("TPanedwindow", background=theme.background)

        # Configure ttk styles
        self._style.configure("TFrame", background=theme.panel_background)
        self._style.configure(
            "TLabel",
            background=theme.panel_background,
            foreground=theme.panel_foreground,
        )
        self._style.configure(
            "TButton",
            background=theme.button_background,
            foreground=theme.button_foreground,
            bordercolor=theme.border,
        )
        self._style.map(
            "TButton",
            background=[("active", theme.hover)],
            foreground=[("disabled", theme.text_disabled)],
        )

        self._style.configure(
            "Treeview",
            background=theme.text_background,
            foreground=theme.text_foreground,
            fieldbackground=theme.text_background,
        )
        self._style.map(
            "Treeview",
            background=[("selected", theme.selection)],
            foreground=[("selected", theme.status_foreground)],
        )

        self._style.configure(
            "TNotebook", background=theme.panel_background, bordercolor=theme.border
        )
        self._style.configure(
            "TNotebook.Tab",
            background=theme.panel_background,
            foreground=theme.panel_foreground,
            bordercolor=theme.border,
        )
        self._style.map(
            "TNotebook.Tab",
            background=[("selected", theme.background)],
            foreground=[("selected", theme.foreground)],
        )

        self._style.configure(
            "Collapsible.TFrame",
            background=theme.panel_background,
            bordercolor=theme.border,
        )

        self._style.configure(
            "StatusBar.TFrame",
            background=theme.status_background,
            foreground=theme.status_foreground,
        )

        # Configure non-ttk widgets (minimize usage)
        self._configure_tk_widgets(theme)

    def _configure_tk_widgets(self, theme: ThemeColors):
        """Configure tk widgets that couldn't be replaced with ttk"""
        # Create a mapping of widget classes to their configurations
        tk_configs = {
            tk.Text: {
                "background": theme.text_background,
                "foreground": theme.text_foreground,
                "insertbackground": theme.text_foreground,
                "selectbackground": theme.selection,
                "selectforeground": theme.status_foreground,
                "borderwidth": 1,
                "relief": "solid",
            }
        }

        def configure_widget(widget):
            """Recursively configure widgets"""
            widget_class = widget.__class__
            if widget_class in tk_configs:
                widget.configure(**tk_configs[widget_class])

            # Configure children
            for child in widget.winfo_children():
                configure_widget(child)

        # Get all root windows
        for window in tk._default_root.winfo_children():
            configure_widget(window)

    def get_current_theme(self) -> str:
        """Get the name of the current theme"""
        return self.current_theme or "system"
