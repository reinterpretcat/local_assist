import tkinter as tk
from tkinter import messagebox
from typing import Dict
from ..models import RAG


class RAGSettingsWindow:
    def __init__(self, root, rag_model: RAG, theme: Dict, on_save_callback):
        self.window = tk.Toplevel(root)
        self.window.title("🔍 RAG Settings")
        self.window.geometry("800x600")
        self.rag_model = rag_model
        self.theme = theme
        self.on_save_callback = on_save_callback

        # Configure window
        self.window.configure(bg=theme["popup_bg"])
        self.window.grid_columnconfigure(0, weight=0)  # Label column
        self.window.grid_columnconfigure(1, weight=1)  # Input column

        self.create_widgets()
        self.create_buttons()

        self.window.bind("<Escape>", lambda _: self.window.destroy())
        self.window.transient(root)
        self.window.grab_set()
        self.window.wait_window(self.window)

    def create_widgets(self):
        # Similarity Top K
        self.top_k = self.create_labeled_entry(
            "Similar Results (Top K):", self.rag_model.similarity_top_k, 0
        )

        # Prompt Template
        prompt_label = tk.Label(
            self.window,
            text="Prompt Template:",
            font=("Arial", 12, "bold"),
            bg=self.theme["popup_bg"],
            fg=self.theme["fg"],
        )
        prompt_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(20, 5)
        )

        self.template = tk.Text(
            self.window,
            wrap=tk.WORD,
            height=16,
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            insertbackground=self.theme["input_fg"],
            undo=True,
        )
        self.template.insert("1.0", self.rag_model.prompt_template)
        self.template.grid(
            row=2, column=0, columnspan=2, padx=10, pady=5, sticky="nsew"
        )

        # Configure text widget bindings
        self.template.bind("<Control-a>", self.select_all)
        self.template.bind("<Control-z>", self.undo)

        # Make prompt expandable
        self.window.grid_rowconfigure(2, weight=1)

    def create_labeled_entry(self, label_text, initial_value, row_num):
        label = tk.Label(
            self.window,
            text=label_text,
            font=("Arial", 12, "bold"),
            bg=self.theme["popup_bg"],
            fg=self.theme["fg"],
        )
        label.grid(row=row_num, column=0, sticky="w", padx=10, pady=5)

        entry = tk.Entry(
            self.window,
            width=10,
            bg=self.theme["input_bg"],
            fg=self.theme["input_fg"],
            insertbackground=self.theme["input_fg"],
        )
        entry.grid(row=row_num, column=1, sticky="e", padx=10, pady=5)

        if initial_value:
            entry.insert(0, str(initial_value))

        return entry

    def create_buttons(self):
        button_frame = tk.Frame(self.window, bg=self.theme["popup_bg"])
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        button_style = {
            "font": ("Arial", 12),
            "width": 10,
            "bg": self.theme["button_bg"],
            "fg": self.theme["button_fg"],
            "activebackground": self.theme["button_bg_hover"],
            "activeforeground": self.theme["button_fg"],
            "relief": "solid",
            "borderwidth": 1,
        }

        save_btn = tk.Button(
            button_frame, text="Save", command=self.save, **button_style
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            button_frame, text="Cancel", command=self.window.destroy, **button_style
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

    def select_all(self, event=None):
        self.template.tag_add("sel", "1.0", "end")
        return "break"

    def undo(self, event=None):
        self.template.edit_undo()
        return "break"

    def save(self):
        try:
            top_k = int(self.top_k.get())
            prompt_template = self.template.get("1.0", tk.END).strip()
            required = ["{context}", "{question}"]
            if not all(ph in prompt_template for ph in required):
                raise ValueError(f"Template must contain: {required}")

            self.rag_model.prompt_template = prompt_template
            self.top_k = top_k

            self.on_save_callback(prompt_template, top_k)

            self.window.destroy()
        except ValueError as e:
            messagebox.showerror("Error", e)
