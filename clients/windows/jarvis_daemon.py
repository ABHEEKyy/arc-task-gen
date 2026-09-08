"""Background listener daemon that waits for 'Hey Jarvis' to activate the floating Siri bubble.
Instead of opening a CMD terminal window, it opens a sleek Siri-like HUD bubble in the top corner of the screen.
"""

import os
import sys
import socket
import subprocess
import time
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

SAMPLE_RATE = 16_000
FRAME_SAMPLES = 1280
WAKE_THRESHOLD = 0.25
IPC_PORT = 8799


def trigger_jarvis_bubble():
    """Wakes the existing Siri Bubble via local socket IPC, or launches it with pythonw (no CMD window)."""
    # 1. Try waking running bubble on port 8799
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(("127.0.0.1", IPC_PORT))
            s.sendall(b"WAKE\n")
            print("[Daemon]: Sent WAKE signal to active Siri bubble.", flush=True)
            return
    except Exception:
        pass

    # 2. Launch jarvis_bubble.py via pythonw (frameless, no CMD console!)
    bubble_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "jarvis_bubble.py"))
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = "pythonw"

    try:
        print(f">> [Auto-Opening Siri Bubble HUD]: {bubble_path}", flush=True)
        subprocess.Popen([pythonw, bubble_path], cwd=os.path.dirname(bubble_path))
    except Exception as e:
        print(f"[Bubble Launch Error]: {e}", flush=True)
        try:
            subprocess.Popen([sys.executable, bubble_path], cwd=os.path.dirname(bubble_path))
        except Exception as e2:
            print(f"[Fallback Launch Error]: {e2}", flush=True)


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
    print("Background Daemon Listening for 'Hey Jarvis'...")
    print("Wake word will open the Siri-style HUD bubble in the top corner!", flush=True)
    print("==========================================\n", flush=True)

    try:
        while True:
            frame = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
            prediction = model.predict(np.frombuffer(frame, dtype=np.int16))
            score = max([v for k, v in prediction.items() if "jarvis" in k.lower()], default=0.0)
            if score >= WAKE_THRESHOLD:
                print(f"\n>> ['Hey Jarvis' Detected! Activating Siri Bubble...]", flush=True)
                import winsound
                winsound.Beep(880, 100)
                winsound.Beep(1320, 150)

                trigger_jarvis_bubble()

                if hasattr(model, "reset"):
                    model.reset()
                time.sleep(4)
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()


if __name__ == "__main__":
    listen_for_hey_jarvis()
