"""Explicit Windows actions available to the voice controller."""

import os
from urllib.parse import urlparse

import pyautogui

pyautogui.FAILSAFE = True

ALLOWED_APPS = {
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
}
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
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


def _safe_app_target(app_name: str) -> str | None:
    value = app_name.strip().lower()
    if value in ALLOWED_APPS:
        return ALLOWED_APPS[value]
    parsed = urlparse(value)
    if parsed.scheme in ALLOWED_URL_SCHEMES and parsed.netloc:
        return app_name.strip()
    return None


class WindowsController:
    @staticmethod
    def launch_application(app_name: str) -> str:
        target = _safe_app_target(app_name)
        if not target:
            return "That app or URL is not allowed. Use calculator, notepad, paint, explorer, or a web URL."
        try:
            os.startfile(target)
        except OSError as error:
            return f"Could not launch {app_name}: {error}"
        return f"Launched {app_name}."

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
