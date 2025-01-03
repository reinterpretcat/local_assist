"""
This module defines the application settings using the Pydantic library.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from torch import cuda


class Settings(BaseSettings):
    """
    Application settings class.

    This class inherits from the Pydantic BaseSettings class and defines the configuration settings for the
    application. Default values can be overridden by setting environment variables.

    Attributes:
        HF_TOKEN: The Hugging Face token for accessing models and resources.
        TORCH_DEVICE: The device to use for PyTorch computations (e.g. 'cuda' or 'cpu').
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    HF_TOKEN: str = ""
    TORCH_DEVICE: str = "cuda" if cuda.is_available() else "cpu"


settings = Settings()

default_theme = {
    "bg": "#f7f7f8",
    "fg": "#000000",
    "input_bg": "#e8eaed",
    "input_fg": "#000000",
    "button_bg": "#10a37f",
    "button_fg": "#ffffff",
    "list_bg": "#ffffff",
    "list_fg": "#000000",
    "chat_bg": "#ffffff",
    "chat_fg": "#000000",
    "tool": {"color_prefix": "red"},
    "assistant": {"color_prefix": "green"},
    "user": {"color_prefix": "blue"},
}

default_config = {
    "llm": {
        "disable_chat_history": False,
        "model": "llama3.1:8b-instruct-q4_0",
        # NOTE OLLama options are supported
        # "options": {
        #     # adjusts creativity. Lower values for precise responses, higher values for creative answers.
        #     "temperature": 0.7,
        #
        #     # seed for determenistic responses
        #     "seed": 123,
        #
        #     # controls how much of the previous conversation or text the model
        #     # should remember. This is especially important in longer conversations or when you want the model to keep
        #     # track of a lot of information.
        #     "num_ctx": 1024
        #
        #     # determines how much text the model generates. Use higher values for longer responses, and lower values for short ones.
        #     "num_predict": 20
        # }
    },
    "stt": {
        "device": settings.TORCH_DEVICE,
        "generation_args": {"batch_size": 8},
        "model": "openai/whisper-small.en",
    },
    "tts": {
        "device": settings.TORCH_DEVICE,
        "model": "tts_models/en/ljspeech/glow-tts",
    },
}
