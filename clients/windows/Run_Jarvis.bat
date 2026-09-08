@echo off
title J.A.R.V.I.S. Conversational Terminal
mode con: cols=100 lines=30
color 0A
echo ===================================================
echo     J.A.R.V.I.S. AMBIENT VOICE ASSISTANT ONLINE
echo ===================================================
echo.
cd /d "%~dp0\..\.."
py clients/windows/windows_voice_controller.py
pause
