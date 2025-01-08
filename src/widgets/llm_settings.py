import tkinter as tk
from typing import Dict
from ..models import LLM
from ..tools import get_button_config


def open_llm_settings_dialog(root, theme: Dict, llm_model: LLM):
    """Open a dialog to set LLM settings."""

    current_prompt = llm_model.system_prompt

    settings_window = tk.Toplevel(root)
    settings_window.title("LLM System Prompt")

    settings_window.configure(bg=theme["bg"])

    # System Prompt
    prompt_label = tk.Label(
        settings_window, text="System Prompt:", font=("Arial", 12, "bold")
    )
    prompt_label.pack(anchor="w", padx=10, pady=5)
    prompt_label.configure(bg=theme["bg"], fg=theme["fg"])
    prompt_text = tk.Text(settings_window, wrap=tk.WORD, height=8, width=50)
    prompt_text.insert(tk.END, current_prompt)
    prompt_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
    prompt_text.config(
        bg=theme["input_bg"],
        fg=theme["input_fg"],
        insertbackground=theme["input_fg"],
    )

    # Save Button
    def save_settings():
        llm_model.set_system_prompt(prompt_text.get(1.0, tk.END).strip())
        settings_window.destroy()

    save_button = tk.Button(
        settings_window, text="Save", command=save_settings, bg="green", fg="white"
    )
    save_button.pack(pady=10)
    save_button.configure(**get_button_config(theme))

    # Center the settings window
    settings_window.transient(root)
    settings_window.grab_set()
    settings_window.wait_window(settings_window)
