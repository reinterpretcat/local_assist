import tkinter as tk
from typing import Callable, Dict
from ..models import LLM
from ..tools import LLMSettings, get_button_config


def open_llm_settings_dialog(
    root, theme: Dict, llm_settings: LLMSettings, llm_model: LLM, on_complete: Callable
):
    """Open a dialog to set LLM settings."""

    def get_llm_option_value(llm_model, llm_settings_value, option_name):
        if llm_settings_value is not None:
            return llm_settings_value
        return (
            getattr(llm_model.options, option_name, None) if llm_model.options else None
        )

    # Usage
    current_model_id = get_llm_option_value(llm_model, llm_settings.model_id, "model")
    current_temperature = get_llm_option_value(
        llm_model, llm_settings.temperature, "temperature"
    )
    current_num_ctx = get_llm_option_value(llm_model, llm_settings.num_ctx, "num_ctx")
    current_num_predict = get_llm_option_value(
        llm_model, llm_settings.num_predict, "num_predict"
    )
    current_prompt = (
        llm_settings.system_prompt
        if llm_settings.system_prompt is not None
        else llm_model.system_prompt
    )

    settings_window = tk.Toplevel(root)
    settings_window.title("LLM Settings")
    settings_window.configure(bg=theme["popup_bg"])

    # Helper function to create labeled text fields
    def create_labeled_entry(parent, label_text, initial_value, row_num):
        label = tk.Label(
            parent,
            text=label_text,
            font=("Arial", 12, "bold"),
            bg=theme["popup_bg"],
            fg=theme["fg"],
        )
        label.grid(row=row_num, column=0, sticky="w", padx=10, pady=5)

        entry = tk.Entry(
            parent,
            width=50,
            bg=theme["input_bg"],
            fg=theme["input_fg"],
            insertbackground=theme["input_fg"],
        )
        entry.grid(row=row_num, column=1, padx=10, pady=5)

        # Set the initial value correctly
        if initial_value:
            entry.insert(0, str(initial_value))

        return entry

    # Create entry fields for model settings
    model_id_entry = create_labeled_entry(
        settings_window, "Model ID:", current_model_id, 0
    )
    temperature_entry = create_labeled_entry(
        settings_window, "Temperature:", current_temperature, 1
    )
    num_ctx_entry = create_labeled_entry(
        settings_window, "Num Context:", current_num_ctx, 2
    )
    num_predict_entry = create_labeled_entry(
        settings_window, "Num Predict:", current_num_predict, 3
    )

    # System Prompt (multi-line text field) at the bottom
    prompt_label = tk.Label(
        settings_window,
        text="System Prompt:",
        font=("Arial", 12, "bold"),
        bg=theme["popup_bg"],
        fg=theme["fg"],
    )
    prompt_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(20, 5))

    settings_window.grid_columnconfigure(0, weight=1)
    settings_window.grid_columnconfigure(1, weight=1)
    settings_window.grid_rowconfigure(5, weight=1)
    prompt_text = tk.Text(
        settings_window,
        wrap=tk.WORD,
        height=16,
        bg=theme["input_bg"],
        fg=theme["input_fg"],
        insertbackground=theme["input_fg"],
    )
    prompt_text.insert(tk.END, current_prompt)
    prompt_text.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

    # Save Button
    def save_settings():
        updated = False

        def update_setting(attribute, entry_value, current_value):
            nonlocal updated
            # Reset to default (None) if the entry value is empty
            if not entry_value.strip():
                # Only update if the current value is not already None (i.e., reset to None)
                if current_value is not None:
                    setattr(llm_settings, attribute, None)
                    updated = True
            else:
                # Only update if the value differs and is not None
                if entry_value.strip() and entry_value != str(current_value):
                    # Convert entry_value to the type of current_value, handling None
                    if current_value is not None:
                        new_value = type(current_value)(entry_value)
                    else:
                        # For None values, treat them as their default type, e.g., str or int
                        # In case of numbers, default to float or int
                        if isinstance(entry_value, str) and entry_value.isdigit():
                            new_value = int(entry_value)
                        elif (
                            isinstance(entry_value, str)
                            and entry_value.replace(".", "", 1).isdigit()
                        ):
                            new_value = float(entry_value)
                        else:
                            new_value = entry_value  # Keep it as string if no conversion applies
                    if new_value != current_value:
                        setattr(llm_settings, attribute, new_value)
                        updated = True

        # Update settings only if the value differs from the original
        update_setting("model_id", model_id_entry.get(), llm_settings.model_id)
        update_setting("temperature", temperature_entry.get(), llm_settings.temperature)
        update_setting("num_ctx", num_ctx_entry.get(), llm_settings.num_ctx)
        update_setting("num_predict", num_predict_entry.get(), llm_settings.num_predict)

        # Handle system prompt update separately due to multi-line input
        new_prompt = prompt_text.get(1.0, tk.END).strip()
        if new_prompt and new_prompt != (llm_settings.system_prompt or ""):
            llm_settings.system_prompt = new_prompt
            updated = True

        # Call completion function only if settings were updated
        if updated:
            on_complete(llm_settings)

        settings_window.destroy()

    # Frame to center the Save button without expanding it
    button_frame = tk.Frame(settings_window, bg=theme["popup_bg"])
    button_frame.grid(row=6, column=0, columnspan=2, pady=10)

    # Save Button (compact and centered)
    save_button = tk.Button(
        button_frame,
        text="Save",
        command=save_settings,
    )
    save_button.configure(**get_button_config(theme))
    save_button.pack(pady=5)

    # Center and focus on the settings window
    settings_window.transient(root)
    settings_window.grab_set()
    settings_window.wait_window(settings_window)
