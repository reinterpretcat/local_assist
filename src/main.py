"""
This module serves as the entry point for running the GUI program.
"""

import asyncio
import click
import tkinter as tk
# import os
# import time
# import re
# from threading import Thread
# from typing import Optional
from json import loads

from . import __version__
#from .audio import AudioIO
from .gui import AIChatUI
from .models import STT, TTS
from .settings import default_config
from .utils import ThreadSafeState, deep_merge_dicts, logger, print_system_message


async def _real_main(**kwargs):
    
    user_config = loads(kwargs["config"].read()) if kwargs["config"] else {}
    config = deep_merge_dicts(default_config, user_config)

    llm_config = config["llm"]
    stt_config = config.get("stt") or {}
    tts_config = config.get("tts") or {}
    
    ######### TODO: LLM setup #########
    
    
    llm_model = None
    stt_model = STT(**stt_config) if stt_config else None
    tts_model = TTS(**tts_config) if tts_config else None
    
    
    root = tk.Tk()    
    app = AIChatUI(root, stt_model, tts_model)
    
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
