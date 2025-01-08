# Personal AI Chat Assistant

An experimental AI Chat client built with Python/Tkinter for experimentation with local hosted LLMs (ollama). This project represents a "learn by doing" approach where various LLMs (including the ones consumed through the chat client itself) helped in the development process.

![image](https://github.com/user-attachments/assets/3cfd0db5-2e57-4fdc-a691-577589996b49)

## Project Philosophy

This is an experimental project focusing on functionality over code architecture. Some interesting aspects:

- Built primarily for personal use and experimentation with local LLM models
- Code was generated with help of various LLMs
- The application was partially used to improve itself - it generated some of its own code!
- Prioritizes rapid experimentation over architectural patterns (no strict MVC/MVVM)
- Primary use case: Language learning through AI conversation (with German TTS/STT configs)

## Key Features

- Integration with Ollama for local LLM hosting
- Chat history saving and loading
- Text-to-Speech (TTS) for AI responses
- Speech-to-Text (STT) for voice input
- A very naive RAG (Retrieval-Augmented Generation) support for chatting about your documents
- Customizable system prompts
- Custom themes support
- Basic markdown support

## Installation

1. Install Ollama from https://ollama.com/download

2. Pull desired LLM models:
```bash
# Basic models
ollama pull llama2:13b
ollama pull mistral:7b

# Code-specific models
ollama pull qwen2.5-coder:7b

# Language learning models (German)
ollama pull cyberwald/llama-3.1-sauerkrautlm-8b-instruct:q8_0
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Launch the application:
```bash
python3 -m src.main
```

Note: On first run, the application will automatically download required voices and dependencies for STT/TTS functionality.

## Usage Examples

### Basic Usage
```bash
# Default configuration
python3 -m src.main

# Check CUDA availability
python3 -c 'import torch; print(torch.cuda.is_available())'
```

### Language Learning Configurations
```bash
# German learning mode
python3 -m src.main --config config-de.json

# Code assistant mode
python3 -m src.main --config config-code.json
```

## RAG (Retrieval-Augmented Generation)

The application supports chatting with your documents through RAG:
- Upload PDF, Markdown and TXT document formats
- Automatic document embedding and indexing
- Context-aware responses based on your documents
- Currently in experimental phase

## Known Limitations

- Code structure prioritizes experimentation over maintainability
- Some features may be unstable or experimental
- UI is functional but basic
- Limited error handling in some areas


## License

This project is open source and available under the MIT License.

## Acknowledgments

- Initial inspiration from the [june](https://github.com/mezbaul-h/june) project
- Various LLMs that helped generate and improve the code
- The Ollama team for making local LLM hosting accessible
