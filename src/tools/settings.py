"""
This module defines the application settings using the Pydantic library.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from torch import cuda
from .theme import dark_theme


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
default_theme = dark_theme


default_config = {
    # Chat config
    "chat": {
        "db_path": ".chat/chats.sqlite3",
        "history_sort": False,
    },
    # LLM config
    "llm": {
        "disable_chat_history": False,
        "model": "llama3.1:8b-instruct-q4_0",
        # NOTE Passed as ollama client's Options
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
        #     "num_ctx": 4096
        #
        #     # determines how much text the model generates. Use higher values for longer responses, and lower values for short ones.
        #     "num_predict": 20
        # }
    },
    # retrieval augument generation config
    "rag": {
        # NOTE: actually ignored, but required by BaseModel, so keep it for compatibility
        "model": "qwen2.5-coder:7b",
        # chroma path
        "persist_dir": ".chromadb",
        "embed_cache": ".cache",
        "embed_model_name": "all-MiniLM-L6-v2",
        "chunk_size": 2048,
        "chunk_overlap": 128,
        "similarity_top_k": 4,
        "supported_extensions": [".csv", ".docx", ".epub", ".md", ".pdf", ".txt", ".json"],
        # Prompt for answering question
        "prompt_template": """Context: {context}

Instructions:
1. Answer the question using only the provided context.
2. If the context is insufficient, say "I cannot answer this question based on the provided information."
3. Be concise and accurate.
4. You can use your main (system) prompt for further instructions.

Question: {question}

Answer:""",
    },
    # speech to text config
    "stt": {
        "device": settings.TORCH_DEVICE,
        "generation_args": {"batch_size": 8},
        "model": "openai/whisper-small.en",
    },
    # text to speech config
    "tts": {
        "device": settings.TORCH_DEVICE,
        "model": "tts_models/en/ljspeech/glow-tts",
    },
}
