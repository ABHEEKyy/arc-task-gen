"""Background listener daemon that waits for 'Hey Jarvis' to open the single CMD window.
Once opened, user says 'Hello Jarvis' inside the window to execute commands.
"""

import os
import subprocess
import time
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

SAMPLE_RATE = 16_000
FRAME_SAMPLES = 1280
WAKE_THRESHOLD = 0.45


def launch_single_jarvis_window():
    """Opens Run_Jarvis.bat ONLY if not already open."""
    bat_path = os.path.join(os.path.dirname(__file__), "Run_Jarvis.bat")
    if not os.path.exists(bat_path):
        bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Run_Jarvis.bat"))
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            cmdline = proc.info.get('cmdline') or []
            if any('windows_voice_controller.py' in str(arg) or 'Run_Jarvis.bat' in str(arg) for arg in cmdline):
                print("[Daemon Note]: Jarvis terminal window is already active.", flush=True)
                return
    except Exception:
        pass

    try:
        # Launch Run_Jarvis.bat in a visible interactive CMD window
        print(f">> [Auto-Opening]: {bat_path}", flush=True)
        subprocess.Popen(f'cmd.exe /c start "J.A.R.V.I.S. Conversational Terminal" "{bat_path}"', shell=True)
    except Exception as e:
        print(f"[Launch Error]: {e}", flush=True)



def listen_for_hey_jarvis():
    openwakeword.utils.download_models()
    models_to_load = ["hey_jarvis"]
    for path in openwakeword.get_pretrained_model_paths():
        if "jarvis" in os.path.basename(path).lower() and os.path.basename(path) not in models_to_load:
            models_to_load.append(path)

    model = Model(wakeword_models=models_to_load)
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAME_SAMPLES,
    )

    print("\n==========================================", flush=True)
    print("Background Daemon Listening...")
    print("Say 'Hey Jarvis' to open the single Jarvis window!", flush=True)
    print("==========================================\n", flush=True)

    try:
        while True:
            frame = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
            prediction = model.predict(np.frombuffer(frame, dtype=np.int16))
            score = max([v for k, v in prediction.items() if "jarvis" in k.lower()], default=0.0)
            if score >= WAKE_THRESHOLD:
                print(f"\n>> ['Hey Jarvis' Detected! Opening single window...]", flush=True)
                import winsound
                winsound.Beep(880, 100)
                winsound.Beep(1320, 150)
                
                launch_single_jarvis_window()
                
                if hasattr(model, "reset"):
                    model.reset()
                time.sleep(5)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


if __name__ == "__main__":
    listen_for_hey_jarvis()
