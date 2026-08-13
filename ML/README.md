# ML - VLM Integration

OpenRouter account created, API key stored in `.env`
## VLM Testing Results

Tested the local LLaVA model (`vlm_test.py`) on sample UI images:
- **Accuracy:** Correctly identified page layouts, navigation menus, specific text elements (e.g., "Priya Lila", "75%"), and footer structures.
- **Quality:** Output is structured, reliable, and free from hallucinations.

# VLM (Vision-Language Model) Script

## Overview
This script uses a local Vision-Language Model to analyze images and generate text descriptions/answers based on visual input.

## Prerequisites & Installation
Before running the script, ensure you have **Ollama** installed and the **LLaVA** model downloaded.

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2. **Pull the LLaVA model**: Run the following command in your terminal:
   ```bash
   ollama pull llava

   ## Setup & Prerequisites

