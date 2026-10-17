#!/usr/bin/env bash
# macOS launcher script for Jarvis Voice Assistant
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/clients/windows:$PYTHONPATH"
if [ -x "$PWD/.venv/bin/python3" ]; then
    exec "$PWD/.venv/bin/python3" clients/windows/windows_voice_controller.py "$@"
else
    exec python3 clients/windows/windows_voice_controller.py "$@"
fi

