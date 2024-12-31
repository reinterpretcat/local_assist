"""
This module serves as the entry point for running the GUI program.
"""

import asyncio
import click
from colorama import Fore
import tkinter as tk
import logging
from json import loads

from . import __version__
from .gui import AIChatUI
from .models import LLM, STT, TTS
from .settings import default_config
from .utils import deep_merge_dicts, print_system_message


async def _real_main(**kwargs):
    
    user_config = loads(kwargs["config"].read()) if kwargs["config"] else {}
    config = deep_merge_dicts(default_config, user_config)

    llm_config = config.get("llm") or {}
    stt_config = config.get("stt") or {}
    tts_config = config.get("tts") or {}
    
    llm_model = LLM(**llm_config) if llm_config else None
    stt_model = STT(**stt_config) if stt_config else None
    tts_model = TTS(**tts_config) if tts_config else None
    
    if not llm_model.exists():
        print_system_message(f"Invalid ollama model: {llm_model.model_id}", color=Fore.RED, log_level=logging.ERROR)
        return 2
    
    
    root = tk.Tk()    
    app = AIChatUI(root, llm_model, stt_model, tts_model)
    
    root.mainloop()
    


@click.command()
@click.option(
    "-c",
    "--config",
    help="Configuration file.",
    nargs=1,
    required=False,
    type=click.File("r", encoding="utf-8"),
)

@click.version_option(__version__)
def main(**kwargs):
    asyncio.run(_real_main(**kwargs))
    

if __name__ == "__main__":
    main()
