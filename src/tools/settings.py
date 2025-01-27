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
        "history_path": "history.json",
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
        #     "num_ctx": 1024
        #
        #     # determines how much text the model generates. Use higher values for longer responses, and lower values for short ones.
        #     "num_predict": 20
        # }
    },
    # retrieval augument generation config
    "rag": {
        # LLM to use for RAG
        "model": "llama3.1:8b-instruct-q4_0",
        # NOTE same as for llm, but used only for RAG
        "options": {
            # "seed": 123,
            # "num_ctx": 1024
            # "num_predict": 20
            "num_ctx": 4096,
            # "temperature": 0.3,
            # "top_p": 0.8,  # More focused token selection
        },
        # where to store data
        "persist_directory": ".chromadb",
        # how many tokens to request
        "token_limit": 4096,
        # summarization relevance threshold
        "min_relevance": 0.1,
        # maximum number of results (chunks) to retrieve from store
        "top_k": 2048,
        # summarization prompt is used to extract information from documents
        "summarize_prompt": """You are a precise document summarizer. Create a concise summary that:
    1. Preserves key information (dates, numbers, names, technical details)
    2. Maintains the logical flow of information
    3. Focuses on factual content rather than narrative
    4. Uses clear structure with paragraphs for different topics
    5. Uses original language of the text
    6. Returns rather empty string if cannot summarize
    Prioritize accuracy of technical details and specific information over brevity.""",
        # context prompt is used to chat over used documents
        "context_prompt": """You are a helpful assistant that provides accurate answers based on the given context.
    Follow these guidelines:
    1. Only use information from the provided context
    2. If the context doesn't contain enough information, acknowledge the limitations
    3. Maintain a natural, conversational tone while being precise""",
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
