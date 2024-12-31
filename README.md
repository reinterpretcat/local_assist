# Description

A  GUI chat client for ollama with TTS/STT integration. The main goal is to build "hackable" UI to experiment with the local hosted AI. A main use case for me is to chat in German with LLM to learn better the language (yeah, a poor man's approach).

The GUI itself built using LLM in a few days (I'm not expert in Python), so the quality is not the main strength. As start, I used some scripts from [june](https://github.com/mezbaul-h/june) project.

![image](https://github.com/user-attachments/assets/f9fb5092-406c-4c38-ab1e-3b35d6363624)


## Installation

1. Install Ollama: https://ollama.com/download
2. Download LLM model `ollama pull <model_name>`, for example `ollama pull llama3.1:8b-instruct-q4_0`
3. Install dependencies via `pip install -r requirements.txt`
4. Run `python3 -m src.main`

At first run, the app will automatically download voices/dependencies for STT/TTS


## Usage

```shell
# check cuda
python3 -c 'import torch; print(torch.cuda.is_available())'

# run with default config
python3 -m src.main

# german learning
python3 -m src.main --config config-de.json

# speak in russian
python3 -m src.main --config config-ru.json
```


## TODO

## General
- improve chat history handling
- add more customization for LLM
- make code more readable

## UI
- add scrollbar to chat area
