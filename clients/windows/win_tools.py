"""Explicit Windows actions available to the voice controller."""

import os
import subprocess
import webbrowser
from urllib.parse import urlparse
try:
    import pyautogui
    pyautogui.FAILSAFE = True
except ImportError:
    pyautogui = None

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
        clean_name = app_name.lower().strip()
        for prefix in ["open ", "run ", "launch ", "execute ", "start ", "the "]:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):].strip()
        for prefix in ["open ", "run ", "launch ", "execute ", "start ", "the "]:
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):].strip()


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
        if clean_name.startswith("http://") or clean_name.startswith("https://"):
            webbrowser.open(clean_name)
            return f"Opened {clean_name}"
        elif clean_name == "youtube":
            webbrowser.open("https://www.youtube.com")
            return "Opened https://www.youtube.com"
        elif clean_name == "google":
            webbrowser.open("https://www.google.com")
            return "Opened https://www.google.com"

        # 2. Batch files (.bat / .cmd) and local executable scripts
        # Case A: User generically asks to "open the bat file" or "run bat file"
        if clean_name in ["bat file", "batch file", "the bat file", "the batch file", "bat", "batch", "script", "the script"]:
            # Auto-find the primary batch file in the repository or workspace
            potential_roots = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
                os.path.dirname(__file__),
                os.getcwd(),
                os.path.expanduser("~/Desktop"),
            ]
            for proot in potential_roots:
                if os.path.isdir(proot):
                    for root_dir, _, files in os.walk(proot):
                        for f in files:
                            if f.lower().endswith(".bat") and not f.startswith("."):
                                abs_bat = os.path.join(root_dir, f)
                                try:
                                    subprocess.Popen(f'start "" "{abs_bat}"', shell=True)
                                    return f"Automatically opened batch file: {f}"
                                except Exception as e:
                                    return f"Failed to run batch file {f}: {e}"

        # Case B: Specific file name or path requested
        bat_name = clean_name.replace("batch file", "").replace("bat file", "").strip()
        candidates = [
            clean_name,
            app_name.strip(),
            bat_name,
            f"{bat_name}.bat",
            f"{bat_name}.cmd",
        ]
        search_dirs = [
            os.getcwd(),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
            os.path.dirname(__file__),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~"),
        ]
        for cand in candidates:
            if not cand:
                continue
            for sdir in search_dirs:
                target_path = os.path.join(sdir, cand)
                if os.path.isfile(target_path) and target_path.lower().endswith((".bat", ".cmd", ".exe", ".ps1")):
                    abs_p = os.path.abspath(target_path)
                    try:
                        subprocess.Popen(f'start "" "{abs_p}"', shell=True)
                        return f"Successfully executed batch script: {os.path.basename(abs_p)}"
                    except Exception as e:
                        return f"Failed to execute batch file {os.path.basename(abs_p)}: {e}"


        # If explicitly requesting a .bat or .cmd by name, try direct shell start
        if clean_name.endswith((".bat", ".cmd")):
            try:
                subprocess.Popen(f'start "" "{clean_name}"', shell=True)
                return f"Executed {clean_name}"
            except Exception:
                pass

        # 3. Native Windows Shell os.startfile()
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

        # 4. Try AppOpener (Matches Start Menu & UWP Store apps)
        try:
            from AppOpener import open as open_app
            open_app(clean_name, match_closest=True, throw_error=True)
            return f"Successfully launched {app_name}"
        except Exception:
            pass

        # 5. Fallback: Windows Start-Process via PowerShell
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
