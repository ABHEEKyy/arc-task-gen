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


def find_file_by_name_or_partial(query_name: str) -> str | None:
    """Finds any app, shortcut (.lnk), or file on Desktop, Start Menu, workspace, or user library matching full or partial name regardless of extension."""
    raw = query_name.lower().strip()
    for prefix in ["open ", "launch ", "start ", "run ", "the ", "file ", "folder ", "script ", "app "]:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
    
    if not raw:
        return None

    if os.path.exists(raw):
        return os.path.abspath(raw)

    clean_raw = raw.replace("_", " ").replace("-", " ").strip()
    compressed_raw = clean_raw.replace(" ", "")

    user_home = os.path.expanduser("~")
    workspace_root = os.getcwd()
    search_dirs = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, r"OneDrive\Desktop"),
        r"C:\Users\Public\Desktop",
        os.path.join(user_home, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
        workspace_root,
        os.path.abspath(os.path.join(workspace_root, "..")),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Documents"),
        os.path.join(user_home, r"OneDrive\Documents"),
        os.path.join(user_home, "Pictures"),
        os.path.join(user_home, "Videos"),
        user_home,
    ]

    matches = []
    seen = set()

    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        try:
            for root, dirs, files in os.walk(s_dir):
                for item in files + dirs:
                    full_path = os.path.abspath(os.path.join(root, item))
                    if full_path in seen:
                        continue
                    
                    item_lower = item.lower()
                    base_name, ext = os.path.splitext(item_lower)
                    
                    # Clean shortcut suffixes e.g. 'forzahorizon6 - Shortcut' -> 'forzahorizon6'
                    clean_item_base = base_name.replace(" - shortcut", "").replace("-shortcut", "").replace("(shortcut)", "").replace("_", " ").replace("-", " ").strip()
                    item_compressed = clean_item_base.replace(" ", "")

                    score = 0
                    if raw == item_lower or raw == base_name or clean_raw == clean_item_base or compressed_raw == item_compressed:
                        score = 100
                    elif raw in item_lower or raw in base_name or clean_raw in clean_item_base or compressed_raw in item_compressed:
                        score = 85
                    elif item_compressed in compressed_raw:
                        score = 80
                    else:
                        words = [w for w in clean_raw.split() if len(w) > 1]
                        if words and all(w in clean_item_base or w in item_compressed for w in words):
                            score = 75

                    if score > 0:
                        is_dir = os.path.isdir(full_path)
                        is_desktop_or_start = any(k in full_path.lower() for k in ["desktop", "start menu"])
                        
                        # Priority: Desktop/Start Menu shortcut (.lnk) = +150, .exe/.bat/.cmd = +100, file = +40, dir = +0
                        location_bonus = 150 if (ext == ".lnk" and is_desktop_or_start) else 120 if ext == ".lnk" else 100 if ext in [".exe", ".bat", ".cmd", ".ps1"] else 40 if not is_dir else 0
                        final_score = score + location_bonus
                        
                        seen.add(full_path)
                        matches.append((final_score, full_path))

                if root.count(os.sep) - s_dir.count(os.sep) >= 3:
                    del dirs[:]
        except Exception:
            continue

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        return matches[0][1]

    return None



def open_file_in_app(file_query: str, app_query: str) -> str:
    """Finds a matching file/partial name and opens it inside the requested application."""
    file_path = find_file_by_name_or_partial(file_query)
    if not file_path:
        return f"Could not locate any file matching '{file_query}'."

    clean_app = app_query.lower().strip().replace("the ", "")
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "msedge": "msedge.exe",
        "brave": "brave.exe",
        "firefox": "firefox.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "wordpad": "wordpad.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "vlc": "vlc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "spotify": "spotify:",
        "steam": "steam://",
        "discord": "discord:",
        "whatsapp": "whatsapp:",
        "telegram": "telegram:"
    }
    app_cmd = app_map.get(clean_app, clean_app)
    file_name = os.path.basename(file_path)

    try:
        subprocess.Popen(f'start "" {app_cmd} "{file_path}"', shell=True)
        return f"Opened '{file_name}' in {app_query}."
    except Exception as e:
        try:
            os.startfile(file_path)
            return f"Opened '{file_name}' (fallback to default program)."
        except Exception as ex:
            return f"Could not open '{file_name}': {ex}"


class WindowsController:
    @staticmethod
    def launch_application(app_name: str) -> str:
        """Reliably opens Windows applications, URLs, Windows Store apps, or files by full/partial name."""
        raw_cmd = app_name.lower().strip()
        for prefix in ["open ", "run ", "launch ", "execute ", "start "]:
            if raw_cmd.startswith(prefix):
                raw_cmd = raw_cmd[len(prefix):].strip()

        # Handle 'open X in Y' or 'open X with Y'
        if " in " in raw_cmd:
            parts = raw_cmd.split(" in ", 1)
            return open_file_in_app(parts[0].strip(), parts[1].strip())
        elif " with " in raw_cmd:
            parts = raw_cmd.split(" with ", 1)
            return open_file_in_app(parts[0].strip(), parts[1].strip())

        clean_name = raw_cmd.replace("the ", "").strip()

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
            "steam": "steam://",
            "discord": "discord:",
            "whatsapp": "whatsapp:",
            "telegram": "telegram:",
            "vlc": "vlc.exe",
            "word": "winword.exe",
            "excel": "excel.exe",
            "powerpoint": "powerpnt.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "vscode": "code",
            "vs code": "code"
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

        # macOS Native App & URL launcher
        import sys
        if sys.platform == "darwin":
            mac_apps = {
                "chrome": "Google Chrome",
                "google chrome": "Google Chrome",
                "safari": "Safari",
                "terminal": "Terminal",
                "vscode": "Visual Studio Code",
                "vs code": "Visual Studio Code",
                "code": "Visual Studio Code",
                "spotify": "Spotify",
                "notes": "Notes",
                "calculator": "Calculator",
                "calc": "Calculator",
                "music": "Music",
                "finder": "Finder",
                "slack": "Slack",
                "discord": "Discord",
            }
            target_app = mac_apps.get(clean_name, clean_name)
            res = subprocess.run(["open", "-a", target_app], capture_output=True, text=True)
            if res.returncode == 0:
                return f"Launched {target_app}"
            res = subprocess.run(["open", clean_name], capture_output=True, text=True)
            if res.returncode == 0:
                return f"Opened {clean_name}"
            return f"Application '{app_name}' not found on macOS."

        # 2. Search for exact or partial matching files across any extension
        file_path = find_file_by_name_or_partial(clean_name)
        if file_path and clean_name not in SYSTEM_COMMANDS:
            try:
                os.startfile(file_path)
                return f"Successfully opened file: {os.path.basename(file_path)}"
            except Exception as e:
                print(f"[File Launch Error]: {e}", flush=True)

        # 3. Native Windows Shell os.startfile() for system apps
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

        # If file was found earlier but wasn't launched yet
        if file_path:
            try:
                os.startfile(file_path)
                return f"Successfully opened file: {os.path.basename(file_path)}"
            except Exception as e:
                pass

        # 4. Try AppOpener (Matches Start Menu & UWP Store apps)
        try:
            from AppOpener import open as open_app
            open_app(clean_name, match_closest=True, throw_error=True)
            return f"Successfully launched {app_name}"
        except Exception:
            pass

        # 5. Fallback for Windows
        try:
            cmd = f'powershell -Command "Start-Process \'{clean_name}\'"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return f"Launched {clean_name}"
            else:
                return f"Executable or file '{app_name}' not found: {res.stderr.strip()}"
        except Exception as e:
            return f"Execution error: {str(e)}"


    @staticmethod
    def system_volume(action: str, amount: int = 10) -> str:
        import sys
        if sys.platform == "darwin":
            if action == "mute":
                subprocess.run(["osascript", "-e", "set volume with output muted"], capture_output=True)
            elif action == "up":
                subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"], capture_output=True)
            elif action == "down":
                subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"], capture_output=True)
            return f"Volume {action}."
        key = VOLUME_KEYS.get(action.lower())
        if not key:
            return "Volume action must be mute, up, or down."
        presses = 1 if key == "volumemute" else max(1, min(25, amount // 2))
        for _ in range(presses):
            pyautogui.press(key)
        return f"Volume {action.lower()}."

    @staticmethod
    def window_management(action: str) -> str:
        import sys
        if sys.platform == "darwin":
            if action == "minimize":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "m" using {command down}'], capture_output=True)
            elif action == "maximize":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using {control down, command down}'], capture_output=True)
            elif action == "close":
                subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "w" using {command down}'], capture_output=True)
            return f"Window {action}."
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
