"""Explicit Windows actions available to the voice controller."""

import os
import subprocess
import webbrowser
from urllib.parse import urlparse
import pyautogui

pyautogui.FAILSAFE = True

# Common Windows executable and URI aliases
APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "https://google.com",
    "youtube": "https://youtube.com",
    "spotify": "spotify",
    "discord": "discord",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "mspaint": "mspaint",
    "terminal": "wt",
    "cmd": "cmd",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "steam": "steam"
}

VOLUME_KEYS = {"mute": "volumemute", "up": "volumeup", "down": "volumedown"}
SHORTCUT_KEYS = {
    "alt": "alt",
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "win": "win",
    "windows": "win",
    "tab": "tab",
    "enter": "enter",
    "escape": "esc",
    "esc": "esc",
    "space": "space",
    "backspace": "backspace",
    "delete": "delete",
}


class WindowsController:
    @staticmethod
    def launch_application(app_name: str) -> str:
        """Reliably opens Windows applications, URLs, or Windows Store apps."""
        clean_name = app_name.lower().strip().replace("the ", "")

        SYSTEM_COMMANDS = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "settings": "ms-settings:",
            "task manager": "taskmgr.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "terminal": "wt.exe",
            "cmd": "cmd.exe",
            "spotify": "spotify:",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "vscode": "code.cmd",
            "vs code": "code.cmd"
        }

        # 1. Direct web URLs
        if clean_name.startswith("http://") or clean_name.startswith("https://") or "youtube" in clean_name or "google" in clean_name:
            url = clean_name if clean_name.startswith("http") else f"https://{clean_name}.com"
            webbrowser.open(url)
            return f"Opened {url}"

        # 2. Native Windows Shell os.startfile()
        if clean_name in SYSTEM_COMMANDS:
            target = SYSTEM_COMMANDS[clean_name]
            try:
                os.startfile(target)
                return f"Successfully opened {clean_name}"
            except Exception:
                try:
                    subprocess.Popen(f'start "" "{target}"', shell=True)
                    return f"Successfully opened {clean_name}"
                except Exception as e:
                    print(f"[Launch Note]: {e}", flush=True)

        # 3. Try AppOpener (Matches Start Menu & UWP Store apps)
        try:
            from AppOpener import open as open_app
            open_app(clean_name, match_closest=True, throw_error=True)
            return f"Successfully launched {app_name}"
        except Exception:
            pass

        # 4. Fallback: Windows Start-Process via PowerShell
        try:
            cmd = f'powershell -Command "Start-Process \'{clean_name}\'"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return f"Launched {clean_name}"
            else:
                return f"Executable '{app_name}' not found: {res.stderr.strip()}"
        except Exception as e:
            return f"Execution error: {str(e)}"

    @staticmethod
    def system_volume(action: str, amount: int = 10) -> str:
        key = VOLUME_KEYS.get(action.lower())
        if not key:
            return "Volume action must be mute, up, or down."
        presses = 1 if key == "volumemute" else max(1, min(25, amount // 2))
        for _ in range(presses):
            pyautogui.press(key)
        return f"Volume {action.lower()}."

    @staticmethod
    def window_management(action: str) -> str:
        if action == "minimize":
            pyautogui.hotkey("alt", "space")
            pyautogui.press("n")
        elif action == "maximize":
            pyautogui.hotkey("alt", "space")
            pyautogui.press("x")
        elif action == "close":
            pyautogui.hotkey("alt", "f4")
        else:
            return "Window action must be minimize, maximize, or close."
        return f"Window {action}."

    @staticmethod
    def keyboard_shortcut(keys: list[str]) -> str:
        normalized = [SHORTCUT_KEYS.get(key.lower()) for key in keys]
        if not normalized or any(key is None for key in normalized):
            return "That keyboard shortcut contains an unsupported key."
        pyautogui.hotkey(*normalized)
        return f"Pressed {'+'.join(normalized)}."

    @staticmethod
    def type_text(text: str) -> str:
        if len(text) > 500:
            return "Text is limited to 500 characters."
        pyautogui.write(text, interval=0.02)
        return "Typed the requested text."
