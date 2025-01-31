import tkinter as tk


def create_tooltip( widget, text):
    """Create a tooltip for a widget."""

    def show_tooltip(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
        label = tk.Label(
            tooltip, text=text, relief="solid", bg="white", pady=2, padx=2
        )
        label.pack()
        widget.tooltip = tooltip
        widget.after(2000, lambda: tooltip.destroy())

    def hide_tooltip(event):
        if hasattr(widget, "tooltip"):
            widget.tooltip.destroy()

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)