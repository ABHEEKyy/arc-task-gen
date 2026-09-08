#!/usr/bin/env bash
# macOS launcher script for Jarvis Voice Assistant
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/clients/windows:$PYTHONPATH"
python3 clients/windows/windows_voice_controller.py

