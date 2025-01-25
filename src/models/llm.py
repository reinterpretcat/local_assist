"""
This module provides a class for interacting with a Language Model (LLM) using the ollama library.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional
from ollama import (
    Client,
    ResponseError,
    Options,
    ListResponse,
    list,
    ProcessResponse,
    ps,
)
import threading

from .common import BaseModel
from ..utils import print_system_message


@dataclass
class ModelSize:
    real: int  # Size in bytes


@dataclass
class ModelDetails:
    format: str
    family: str
    parameter_size: str
    quantization_level: str


@dataclass
class ModelInfo:
    model: str
    size: ModelSize
    details: Optional[ModelDetails] = None


@dataclass
class ModelStatus:
    name: str
    size_vram: int
    size: int


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

        self.model_id_dyn = None
        self.response_statistic = None

        # status update
        self._stop_event = threading.Event()
        self._current_status: Optional[ModelStatus] = None
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        """Main monitoring loop"""
        while not self._stop_event.is_set():
            try:
                response: ProcessResponse = ps()
                if not response.models:
                    self._current_status = None
                    continue

                # Find current model or use first available
                model = next(
                    (m for m in response.models if m.model == self.model_id),
                    response.models[0],
                )

                self._current_status = ModelStatus(
                    name=model.model, size_vram=model.size_vram, size=model.size
                )
            except Exception:
                self._current_status = None
            finally:
                self._stop_event.wait(5.0)

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
            if prompt is None:
                self.messages.pop(system_message_index)
            else:
                self.messages[system_message_index]["content"] = prompt
        elif prompt is not None:
            # Add a new system message if none exists
            self.messages.insert(0, {"role": "system", "content": prompt})

    def set_options(
        self,
        model_id=None,
        temperature=None,
        num_ctx=None,
        num_predict=None,
        system_prompt=None,
    ):
        """Set model options, manage self.options lifecycle, and update system prompt."""
        self.model_id_dyn = model_id

        # Create a dictionary for parameters to evaluate their necessity
        options_dict = {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        }

        # Determine if we need to set options
        has_non_none_options = any(value is not None for value in options_dict.values())
        if has_non_none_options:
            self.options = Options(
                temperature=temperature,
                num_ctx=num_ctx,
                num_predict=num_predict,
            )
        else:
            self.options = None

        # Update the system prompt if different from the current one
        if system_prompt != self.system_prompt:
            self.set_system_prompt(system_prompt)

        print_system_message(
            f"LLM Options are set to: {self.options}, prompt: {system_prompt}"
        )

    def get_model_info(self) -> Optional[ModelStatus]:
        """Returns last model status."""
        return self._current_status

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
            f"Set LLM messages from history ({len(self.messages)})",
            log_level=logging.INFO,
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

    def get_available_models(self) -> List[ModelInfo]:
        """Returns the list of available models."""
        models_info = []
        response: ListResponse = list()
        for model in response.models:
            models_info.append(
                ModelInfo(
                    model=model.model,
                    size=ModelSize(real=model.size.real),
                    details=ModelDetails(
                        format=model.details.format,
                        family=model.details.family,
                        parameter_size=model.details.parameter_size,
                        quantization_level=model.details.quantization_level,
                    ),
                )
            )

        return models_info

    def _update_statistics(self, response):
        """Generate a compact status string for a chat response."""

        def format_duration(key):
            """Convert nanoseconds to human-readable format."""
            value = response.get(key, None)
            if value is None:
                return -1
            ns = int(value)
            if ns >= 1e9:
                return f"{ns / 1e9:.2f}s"
            elif ns >= 1e6:
                return f"{ns / 1e6:.2f}ms"
            return None  # Ignore durations less than milliseconds

        total_duration = format_duration("total_duration")
        load_duration = format_duration("load_duration")
        prompt_eval_duration = format_duration("prompt_eval_duration")
        eval_duration = format_duration("eval_duration")

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

    def forward(self, message: str, image_path: Optional[str] = None) -> Iterator[str]:
        """
        Generate text from user input using the specified LLM.

        Args:
            message: The user input message.

        Returns:
            An iterator that yields the generated text in chunks.
        """

        message = {"role": "user", "content": message}
        if image_path:
            # TODO add more images support
            message["images"] = [image_path]

        self.messages.append(message)

        assistant_role = None
        generated_content = ""

        stream = self.model.chat(
            model=self.model_id_dyn if self.model_id_dyn is not None else self.model_id,
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
