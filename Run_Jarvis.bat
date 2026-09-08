@echo off
title J.A.R.V.I.S. Voice Assistant
cd /d "%~dp0"
start "" py clients\windows\jarvis_bubble.py
py clients\windows\windows_voice_controller.py
pause
