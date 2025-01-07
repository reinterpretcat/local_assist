"""
This module provides classes and functions for recording and playing audio.
"""

import logging
from typing import Dict, List, Optional, Union

import numpy as np
import pygame.mixer

from ..utils import print_system_message, suppress_stdout_stderr


class AudioIO:
    """
    A class for recording and playing audio using PyAudio and Pygame.

    This class provides methods for initializing an input audio stream, recording audio,
    detecting silence in audio data, and playing WAV files using Pygame.

    Attributes:
        RATE: The sample rate for audio recording and playback (default: 24000).
        CHUNK: The buffer size for audio recording (default: 2048).
        THRESHOLD: The threshold for detecting silence in audio data (default: 800).
        SILENCE_LIMIT: The number of seconds of silence before stopping recording (default: 3).
        pa: An instance of the PyAudio object.
        input_stream: The input audio stream for recording.
    """

    RATE = 24000
    CHUNK = 2048
    THRESHOLD = 800
    SILENCE_LIMIT = 30

    def __enter__(self) -> "AudioIO":
        """
        This method is called when the AudioIO instance is used as a context manager.

        Returns:
            The instance of the AudioIO class.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        This method is called when the context manager is exited.
        It closes the audio input stream and terminates the PyAudio instance.
        """
        self.close()

    def __init__(self) -> None:
        pygame.mixer.init(frequency=AudioIO.RATE, size=-16, channels=8, buffer=512)

        self.pa = None
        self.input_stream = None

    def _initialize_input_stream(self) -> None:
        """
        Initialize the input audio stream using PyAudio.
        """
        import pyaudio

        try:
            with suppress_stdout_stderr():
                self.pa = pyaudio.PyAudio()

            self.input_stream = self.pa.open(
                channels=1,
                format=pyaudio.paInt16,
                frames_per_buffer=self.CHUNK,
                input=True,
                rate=self.RATE,
            )
        except Exception as e:
            print_system_message(
                f"_initialize_input_stream: {e}", log_level=logging.ERROR
            )

    def close(self) -> None:
        """
        Close the audio input stream and terminate the PyAudio instance.
        """
        if self.input_stream:
            self.input_stream.close()

        if self.pa:
            self.pa.terminate()

    @staticmethod
    def is_busy() -> bool:
        """Returns true if music mixer is busy"""
        return pygame.mixer.music.get_busy()

    @staticmethod
    def is_silent(data: np.ndarray) -> bool:
        """
        Check if the given audio data is silent based on the configured threshold.

        Args:
            data: The audio data to be checked for silence.

        Returns:
            True if the audio data is silent, False otherwise.
        """
        return np.max(data) < AudioIO.THRESHOLD

    @staticmethod
    def play_wav(file_path: str) -> None:
        """
        Play a WAV audio file using Pygame.

        Args:
            file_path: The path to the WAV file to be played.
        """
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            print_system_message(f"play_wav: {e}", log_level=logging.ERROR)

    def stop_playing(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def stop_recording(self):
        self.stop_recording_flag = True
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

    def record_audio(self) -> Optional[Dict[str, Union[int, np.ndarray]]]:
        """
        Record audio from the microphone and return the recorded data.

        Returns:
            A dictionary containing the recorded audio data and the sampling rate, or None if no audio was recorded.
        """
        if not self.input_stream:
            self._initialize_input_stream()

        frames: List[np.ndarray] = []
        current_silence = 0
        recording = False

        self.stop_recording_flag = False
        self.input_stream.start_stream()
        print_system_message("Listening for sound...", log_level=logging.INFO)

        while True:
            data: np.ndarray = np.frombuffer(
                self.input_stream.read(self.CHUNK), dtype=np.int16
            )

            if not recording and not self.is_silent(data):
                print_system_message(
                    "Sound detected, starting recording...", log_level=logging.INFO
                )
                recording = True

            if recording:
                frames.append(data)
                if self.is_silent(data):
                    current_silence += 1
                else:
                    current_silence = 0

                if (
                    current_silence > (self.SILENCE_LIMIT * self.RATE / self.CHUNK)
                    or self.stop_recording_flag
                ):
                    print_system_message(
                        f"Silence/Interruption detected ({self.stop_recording_flag=}), stopping recording...",
                        log_level=logging.INFO,
                    )
                    break

        self.input_stream.stop_stream()

        if recording:
            raw_data = np.hstack(frames)

            # Convert to float32 and normalize for Hugging Face's `automatic-speech-recognition` pipeline.
            normalized_data = raw_data.astype(np.float32) / np.iinfo(np.int16).max

            return {
                "raw": normalized_data,
                "sampling_rate": self.RATE,
            }
        else:
            return None
