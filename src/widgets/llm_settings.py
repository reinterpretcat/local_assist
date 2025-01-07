import tkinter as tk
from ..models import LLM

def open_llm_settings_dialog(root, llm_model: LLM):
    """Open a dialog to set LLM settings."""
    settings_window = tk.Toplevel(root)
    settings_window.title("LLM System Prompt")

    current_prompt = llm_model.system_prompt

    # System Prompt
    tk.Label(
        settings_window, text="System Prompt:", font=("Arial", 12, "bold")
    ).pack(anchor="w", padx=10, pady=5)
    prompt_text = tk.Text(settings_window, wrap=tk.WORD, height=8, width=50)
    prompt_text.insert(tk.END, current_prompt)
    prompt_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    # Save Button
    def save_settings():
        llm_model.set_system_prompt(prompt_text.get(1.0, tk.END).strip())
        settings_window.destroy()

    tk.Button(
        settings_window, text="Save", command=save_settings, bg="green", fg="white"
    ).pack(pady=10)

    # Center the settings window
    settings_window.transient(root)
    settings_window.grab_set()
    settings_window.wait_window(settings_window)
