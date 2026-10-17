#!/usr/bin/env bash
# macOS launcher script for Jarvis Voice Assistant
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/clients/windows:$PYTHONPATH"

# Automatically ensure Ollama local AI daemon is running
if command -v ollama >/dev/null 2>&1; then
    if ! pgrep -x "ollama" >/dev/null 2>&1; then
        ollama serve >/dev/null 2>&1 &
        sleep 1
    fi
fi

if [ -x "$PWD/.venv/bin/python3" ]; then
    exec "$PWD/.venv/bin/python3" clients/windows/windows_voice_controller.py "$@"
else
    exec python3 clients/windows/windows_voice_controller.py "$@"
fi

