import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List
from ..models import LLM, ModelInfo
from ..tools import LLMSettings, get_button_config


def create_model_info_frame(parent, theme: Dict, model_info: ModelInfo):
    """Create a frame displaying model information."""
    info_frame = tk.Frame(parent, bg=theme["popup_bg"])

    info_text = (
        f"{'Size:':<12}{f'{(model_info.size.real / 1024 / 1024):.2f} MB':<20}"
        f"{'Parameters:':<15}{model_info.details.parameter_size if model_info.details else 'N/A':<20}\n"
        f"{'Format:':<12}{model_info.details.format if model_info.details else 'N/A':<20}"
        f"{'Quantization:':<15}{model_info.details.quantization_level if model_info.details else 'N/A':<20}\n"
        f"{'Family:':<12}{model_info.details.family if model_info.details else 'N/A':<20}"
    )

    info_label = tk.Label(
        info_frame,
        text=info_text,
        justify=tk.LEFT,
        bg=theme["popup_bg"],
        fg=theme["fg"],
        font=("Arial", 10),
    )
    info_label.pack(anchor="w", padx=10)

    return info_frame


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

    current_model_id = get_llm_option_value(llm_model, llm_settings.model_id, "model")
    if current_model_id is None:
        current_model_id = llm_model.model_id

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
    settings_window.grid_columnconfigure(1, weight=1)  # Make second column expandable

    model_label = tk.Label(
        settings_window,
        text="Model:",
        font=("Arial", 12, "bold"),
        bg=theme["popup_bg"],
        fg=theme["fg"],
    )
    model_label.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=5)

    available_models = llm_model.get_available_models()

    # Create dict mapping model names to their info
    model_dict = {model.model: model for model in available_models}

    # Model dropdown
    model_var = tk.StringVar(value=current_model_id)
    style = ttk.Style()
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme["input_bg"])],
        selectbackground=[("readonly", theme["input_bg"])],
        selectforeground=[("readonly", theme["input_fg"])],
    )
    style.configure(
        "TCombobox",
        background=theme["input_bg"],
        foreground=theme["input_fg"],
        arrowcolor=theme["input_fg"],
        selectbackground=theme["input_bg"],
        selectforeground=theme["input_fg"],
        fieldbackground=theme["input_bg"],
    )

    # Configure combobox list popup colors
    settings_window.option_add("*TCombobox*Listbox.background", theme["input_bg"])
    settings_window.option_add("*TCombobox*Listbox.foreground", theme["input_fg"])
    settings_window.option_add("*TCombobox*Listbox.selectBackground", theme["popup_bg"])
    settings_window.option_add("*TCombobox*Listbox.selectForeground", theme["fg"])
    model_dropdown = ttk.Combobox(
        settings_window,
        textvariable=model_var,
        values=sorted(list(model_dict.keys())),
        state="readonly",
        width=50,
        style="Custom.TCombobox",
    )
    model_dropdown.grid(row=0, column=1, padx=10, pady=5)

    # Model info frame
    info_frame = create_model_info_frame(
        settings_window, theme, model_dict[current_model_id]
    )
    info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

    def on_model_change(event):
        """Update model info when selection changes"""
        info_frame.destroy()
        new_info_frame = create_model_info_frame(
            settings_window, theme, model_dict[model_var.get()]
        )
        new_info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

    model_dropdown.bind("<<ComboboxSelected>>", on_model_change)

    # Create other settings fields
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

        if initial_value:
            entry.insert(0, str(initial_value))

        return entry

    temperature_entry = create_labeled_entry(
        settings_window, "Temperature:", current_temperature, 2
    )
    num_ctx_entry = create_labeled_entry(
        settings_window, "Num Context:", current_num_ctx, 3
    )
    num_predict_entry = create_labeled_entry(
        settings_window, "Num Predict:", current_num_predict, 4
    )

    # System Prompt
    prompt_label = tk.Label(
        settings_window,
        text="System Prompt:",
        font=("Arial", 12, "bold"),
        bg=theme["popup_bg"],
        fg=theme["fg"],
    )
    prompt_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(20, 5))

    settings_window.grid_columnconfigure(0, weight=1)
    settings_window.grid_columnconfigure(1, weight=1)
    settings_window.grid_rowconfigure(6, weight=1)

    prompt_text = tk.Text(
        settings_window,
        wrap=tk.WORD,
        height=16,
        bg=theme["input_bg"],
        fg=theme["input_fg"],
        insertbackground=theme["input_fg"],
        undo=True,
    )
    if current_prompt:
        prompt_text.insert(tk.END, current_prompt)
    prompt_text.grid(row=6, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

    def undo(event=None):
        prompt_text.edit_undo()
        return "break"

    def select_all(event=None):
        prompt_text.tag_add("sel", "1.0", "end")
        return "break"

    prompt_text.bind("<Control-a>", select_all)
    prompt_text.bind("<Control-z>", undo)

    def save_settings():
        updated = False

        def update_setting(attribute, entry_value, current_value):
            nonlocal updated
            if not entry_value.strip():
                if current_value is not None:
                    setattr(llm_settings, attribute, None)
                    updated = True
            else:
                if entry_value.strip() and entry_value != str(current_value):
                    if current_value is not None:
                        new_value = type(current_value)(entry_value)
                    else:
                        if isinstance(entry_value, str) and entry_value.isdigit():
                            new_value = int(entry_value)
                        elif (
                            isinstance(entry_value, str)
                            and entry_value.replace(".", "", 1).isdigit()
                        ):
                            new_value = float(entry_value)
                        else:
                            new_value = entry_value
                    if new_value != current_value:
                        setattr(llm_settings, attribute, new_value)
                        updated = True

        # Update model ID from dropdown
        new_model_id = model_var.get()
        if new_model_id != current_model_id:
            llm_settings.model_id = new_model_id
            updated = True

        update_setting("temperature", temperature_entry.get(), llm_settings.temperature)
        update_setting("num_ctx", num_ctx_entry.get(), llm_settings.num_ctx)
        update_setting("num_predict", num_predict_entry.get(), llm_settings.num_predict)

        new_prompt = prompt_text.get(1.0, tk.END).strip()
        if new_prompt != llm_settings.system_prompt:
            llm_settings.system_prompt = new_prompt if new_prompt != "" else None
            updated = True

        if updated:
            on_complete(llm_settings)

        settings_window.destroy()

    # Save button
    button_frame = tk.Frame(settings_window, bg=theme["popup_bg"])
    button_frame.grid(row=7, column=0, columnspan=2, pady=10)

    save_button = tk.Button(
        button_frame,
        text="Save",
        command=save_settings,
    )
    save_button.configure(**get_button_config(theme))
    save_button.pack(pady=5)

    settings_window.bind("<Escape>", lambda _: settings_window.destroy())

    settings_window.transient(root)
    settings_window.grab_set()
    settings_window.wait_window(settings_window)
