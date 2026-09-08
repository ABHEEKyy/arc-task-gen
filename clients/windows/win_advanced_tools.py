import os
import subprocess
import webbrowser
import psutil

# Canonical domain maps for casual phrases
DOMAIN_ALIASES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "chatgpt": "https://chatgpt.com",
    "gmail": "https://mail.google.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "netflix": "https://www.netflix.com",
    "amazon": "https://www.amazon.com"
}

# Browser executable commands on Windows
BROWSER_COMMANDS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "firefox": "firefox"
}

class SystemController:
    @staticmethod
    def open_website(site: str, browser: str = "default") -> str:
        """Opens a website on a specified browser or default browser."""
        # 1. Clean domain or resolve nickname
        raw = site.lower().strip()
        
        # Extract site name if phrases like "youtube on brave" are passed in site string
        for b in ["brave", "chrome", "edge", "firefox", "microsoft edge", "google chrome"]:
            raw = raw.replace(f" on {b}", "").replace(f" in {b}", "").replace(b, "")
        for verb in ["open ", "launch ", "start ", "run "]:
            raw = raw.replace(verb, "")
            
        clean_site = raw.strip().replace(" ", "")

        if clean_site in DOMAIN_ALIASES:
            url = DOMAIN_ALIASES[clean_site]
        elif clean_site.startswith("http://") or clean_site.startswith("https://"):
            url = clean_site
        elif "." in clean_site and not clean_site.endswith("."):
            url = f"https://{clean_site}"
        elif clean_site:
            url = f"https://www.google.com/search?q={clean_site}"
        else:
            url = "https://www.google.com"

        # 2. Open via requested browser executable
        browser_key = browser.lower().strip()
        if browser_key in BROWSER_COMMANDS:
            cmd = BROWSER_COMMANDS[browser_key]
            try:
                subprocess.Popen(f'start {cmd} "{url}"', shell=True)
                return f"Opening {clean_site or site} in {browser.title()}."
            except Exception as e:
                webbrowser.open(url)
                return f"Failed {browser}, opened in default browser: {e}"
        else:
            # System default
            webbrowser.open(url)
            return f"Opening {clean_site or site} in default browser."

    @staticmethod
    def terminate_process(process_name: str) -> str:
        """Terminates active background or windowed processes by name."""
        target = process_name.lower().replace(".exe", "").strip()
        closed = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = proc.info['name'].lower()
                if target in p_name:
                    proc.kill()
                    closed.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if closed:
            return f"Terminated: {', '.join(set(closed))}."
        return f"No active process matching '{process_name}' found."

    @staticmethod
    def get_system_telemetry() -> str:
        """Returns active CPU, Memory, and top processes."""
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        return f"System Status: CPU usage is at {cpu}%, RAM is at {mem}%."
