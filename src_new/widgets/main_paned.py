import tkinter as tk


class MainPanedWindow(tk.PanedWindow):
    """Extends tk.PanedWindow with extra functionality"""

    def __init__(self, *args, **kwargs):
        super(MainPanedWindow, self).__init__(*args, **kwargs)
        self.max_width = {}
        self.bind("<B1-Motion>", self._check_width)
        self.bind("<ButtonRelease-1>", self._set_width)

    def add(self, child, max_width=None, **args):
        super(MainPanedWindow, self).add(child, **args)
        self.max_width[child] = max_width

    def _check_width(self, event):
        for widget, width in self.max_width.items():
            if width and widget.winfo_width() >= width:
                self.paneconfig(widget, width=width)
                return "break"

    def _set_width(self, event):
        for widget, width in self.max_width.items():
            if width and widget.winfo_width() >= width:
                self.paneconfig(widget, width=width - 1)
