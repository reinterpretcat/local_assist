"""
This module provides a class for interacting with a Language Model (LLM) using the ollama library.
"""

import logging
from typing import Dict, Iterator, List, Optional
from ollama import Client, ResponseError, Options

from .common import BaseModel
from ..utils import print_system_message


class LLM(BaseModel):
    """
    A class for interacting with a Language Model (LLM) using the ollama library.

    This class inherits from the BaseModel class and provides methods for checking if a model exists,
    and generating text from user input using the specified LLM.

    Args:
        **kwargs: Keyword arguments for initializing the LLM, including optional arguments
            like 'system_prompt' and 'disable_chat_history'.

    Attributes:
        messages: A list of dictionaries representing the conversation history,
            with each dictionary containing a 'role' (e.g., 'system', 'user', 'assistant') and 'content' keys.
        system_prompt: An optional system prompt to provide context for the conversation.
        is_chat_history_disabled: A flag indicating whether the chat history should be disabled.
        model: An instance of the ollama.Client for interacting with the LLM.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.messages: List[Dict[str, str]] = []

        self.system_prompt: Optional[str] = kwargs.get("system_prompt")

        self.options: Optional[Options] = kwargs.get("options")

        if self.system_prompt:
            self.messages.append({"role": "system", "content": self.system_prompt})

        self.is_chat_history_disabled: Optional[bool] = kwargs.get(
            "disable_chat_history"
        )

        self.model = Client()

        self.response_statistic = None

    def set_system_prompt(self, prompt: str):
        """Update the system prompt and ensure it is reflected in messages."""
        self.system_prompt = prompt

        # Check if a system message already exists in the messages list
        system_message_index = next(
            (
                index
                for index, msg in enumerate(self.messages)
                if msg["role"] == "system"
            ),
            None,
        )

        if system_message_index is not None:
            # Update the existing system message
            self.messages[system_message_index]["content"] = prompt
        else:
            # Add a new system message if none exists
            self.messages.insert(0, {"role": "system", "content": prompt})

    def load_history(self, history: List[Dict[str, str]]):
        """Load conversation history into the LLM class."""
        # Ensure the system prompt is preserved if present
        system_prompt = next(
            (msg["content"] for msg in history if msg["role"] == "system"), None
        )
        if system_prompt:
            self.system_prompt = system_prompt

        self.messages = [msg for msg in history if msg.get("role") != "tool"]

        self.set_system_prompt(self.system_prompt)

        print_system_message(
            f"Set LLM messages from history ({len(self.messages)})", log_level=logging.INFO
        )

    def exists(self) -> bool:
        """
        Check if the specified LLM model exists.

        Returns:
            True if the model exists, False otherwise.
        """
        try:
            # Assert ollama model validity
            _ = self.model.show(self.model_id)

            return True
        except ResponseError:
            return False

    def _update_statistics(self, response):
        """Generate a compact status string for a chat response."""

        def format_duration(ns):
            """Convert nanoseconds to human-readable format."""
            ns = int(ns)
            if ns >= 1e9:
                return f"{ns / 1e9:.2f}s"
            elif ns >= 1e6:
                return f"{ns / 1e6:.2f}ms"
            return None  # Ignore durations less than milliseconds

        total_duration = format_duration(response["total_duration"])
        load_duration = format_duration(response["load_duration"])
        prompt_eval_duration = format_duration(response["prompt_eval_duration"])
        eval_duration = format_duration(response["eval_duration"])

        # Optional: timestamp conversion for logging/debugging
        eval_count = response["eval_count"]
        prompt_eval_count = response["prompt_eval_count"]

        # Build status message
        status_parts = []
        if total_duration:
            status_parts.append(f"Total:{total_duration}")
        if load_duration:
            status_parts.append(f"Load:{load_duration}")
        if prompt_eval_duration:
            status_parts.append(f"Prompt:{prompt_eval_duration}")
        if eval_duration:
            status_parts.append(f"Eval:{eval_duration}")
        status_parts.append(f"Tokens:{prompt_eval_count}")
        status_parts.append(f"Evals:{eval_count}")

        # Join and return status string
        self.response_statistic = "|".join(status_parts)

    def forward(self, message: str) -> Iterator[str]:
        """
        Generate text from user input using the specified LLM.

        Args:
            message: The user input message.

        Returns:
            An iterator that yields the generated text in chunks.
        """
        self.messages.append({"role": "user", "content": message})

        assistant_role = None
        generated_content = ""

        stream = self.model.chat(
            model=self.model_id,
            messages=self.messages,
            stream=True,
            options=self.options,
        )

        for chunk in stream:
            token = chunk["message"]["content"]

            if assistant_role is None:
                assistant_role = chunk["message"]["role"]

            generated_content += token

            # we have reached end of message
            if chunk["done"] == True:
                self._update_statistics(response=chunk)

            yield token

        if self.is_chat_history_disabled:
            self.messages.pop()
        else:
            self.messages.append({"role": assistant_role, "content": generated_content})
