import tkinter as tk
from tkinter import ttk
from typing import Callable


class CollapsiblePanel(ttk.Frame):
    def __init__(
        self,
        parent,
        title,
        get_layout_callback: Callable,
        update_layout_callback: Callable,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.update_layout_callback = update_layout_callback
        self.get_layout_callback = get_layout_callback

        self.is_expanded = tk.BooleanVar(value=False)
        self.default_height = 150
        self.current_height = self.default_height
        self.has_been_expanded = False

        # Header Frame
        self.header = ttk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(1, weight=1)
        self.header.bind("<Button-1>", self.toggle)

        # Toggle button
        self.toggle_btn = ttk.Label(self.header, text="▶")
        self.toggle_btn.grid(row=0, column=0, padx=(5, 0))
        self.toggle_btn.bind("<Button-1>", self.toggle)

        # Title label
        self.title_label = ttk.Label(self.header, text=title)
        self.title_label.grid(row=0, column=1, pady=(5, 5), sticky="w")
        self.title_label.bind("<Button-1>", self.toggle)

        # Content Frame
        self.content = ttk.Frame(self)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_remove()

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def toggle(self, event=None):
        if self.is_expanded.get():
            self.collapse()
        else:
            self.expand()

    def collapse(self):
        self.sash_position = self.get_layout_callback()

        self.toggle_btn.configure(text="▶")
        self.content.grid_remove()
        self.is_expanded.set(False)
        self.update_layout_callback()

    def expand(self):
        self.toggle_btn.configure(text="▼")
        self.content.grid()
        self.is_expanded.set(True)

        if not self.has_been_expanded:
            self.has_been_expanded = True
            self.sash_position = self.default_height  # Default if never expanded

        self.update_layout_callback(self.sash_position)

    def add_content(self, widget):
        widget.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)


class CollapsiblePanelManager:
    def __init__(self, container: ttk.Frame, panel: ttk.PanedWindow):
        self.container = container
        self.panel = panel
        self.panels = []

        self.container.grid_columnconfigure(0, weight=1)

    def create_panel(self, title, content_creator, row):
        self.container.grid_rowconfigure(row, weight=0)
        panel = CollapsiblePanel(
            parent=self.container,
            title=title,
            update_layout_callback=self.update_layout,
            get_layout_callback=lambda: self.panel.sash_coord(0)[1],
        )
        panel.grid(row=row, sticky="nsew")

        # Add content using provided creator function
        content = content_creator(panel.content)
        panel.add_content(content)

        self.panels.append(panel)
        return panel

    def update_sash_state(self):
        all_collapsed = all(not panel.is_expanded.get() for panel in self.panels)

        if all_collapsed:
            self.panel.bind("<B1-Motion>", lambda e: "break")
        else:
            self.panel.unbind("<B1-Motion>")

    def resize_to_fit_collapsed_panels(self):
        self.container.update_idletasks()
        total_collapsed_height = sum(
            panel.header.winfo_height() for panel in self.panels
        )
        total_panel_height = self.panel.winfo_height()
        sash_position = max(0, total_panel_height - total_collapsed_height)
        self.panel.sash_place(0, 0, sash_position)

    def update_layout(self, requested_height=None):
        expanded_panels = []
        total_collapsed_height = 0

        for i, panel in enumerate(self.panels):
            if panel.is_expanded.get():
                expanded_panels.append((panel, i))
            else:
                total_collapsed_height += panel.header.winfo_height()

        # Reset row configurations
        for i in range(len(self.panels)):
            self.container.grid_rowconfigure(i, weight=0)

        if not expanded_panels:
            self.resize_to_fit_collapsed_panels()
        else:
            for panel, row in expanded_panels:
                self.container.grid_rowconfigure(row, weight=1)

            if requested_height:
                total_height = self.panel.winfo_height()
                remaining_space = (
                    total_height - requested_height - total_collapsed_height
                )
                min_file_tree_height = 50

                if remaining_space < min_file_tree_height:
                    requested_height = (
                        total_height - min_file_tree_height - total_collapsed_height
                    )

                self.panel.sash_place(0, 0, requested_height)

        self.update_sash_state()
