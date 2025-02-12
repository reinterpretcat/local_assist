import tkinter as tk
from tkinter import ttk


class MainPanedWindow(ttk.PanedWindow):
    """Extends ttk.PanedWindow with extra functionality"""

    def __init__(self, *args, **kwargs):
        super(MainPanedWindow, self).__init__(*args, **kwargs)
        self.min_width = {}
        self.max_width = {}
        self.pane_to_widget = {}

        # self.bind("<B1-Motion>", self._check_width)
        self.bind("<ButtonRelease-1>", self._set_width)

    def add(self, child, min_width=None, max_width=None, **args):
        super(MainPanedWindow, self).add(child, **args)

        if min_width is not None:
            self.min_width[child] = min_width
        if max_width is not None:
            self.max_width[child] = max_width

        if (min_width is not None) or (max_width is not None):
            # Map the pane identifier to the widget
            pane_id = self.panes()[-1]
            self.pane_to_widget[pane_id] = child

    # def _check_width(self, event):
    #     for index, pane_id in enumerate(self.panes()):
    #         widget = self.pane_to_widget.get(pane_id)
    #         if widget:
    #             current_width = widget.winfo_width()
    #             min_w = self.min_width.get(widget)
    #             max_w = self.max_width.get(widget)

    #             if min_w is not None and current_width < min_w:
    #                 self.sashpos(index, min_w)
    #                 return "break"

    #             if max_w is not None and current_width > max_w:
    #                 self.sashpos(index, max_w)
    #                 return "break"

    def _set_width(self, event):
        for index, pane_id in enumerate(self.panes()):
            widget = self.pane_to_widget.get(pane_id)
            if widget:
                current_width = widget.winfo_width()
                min_w = self.min_width.get(widget)
                max_w = self.max_width.get(widget)

                if min_w is not None and current_width < min_w:
                    self.sashpos(index, min_w)

                if max_w is not None and current_width > max_w:
                    self.sashpos(index, max_w)
