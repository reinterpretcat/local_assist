import tkinter as tk

from .gui import EditorApp

if __name__ == "__main__":
    root = tk.Tk()
    app = EditorApp(root)
    app.run()
