"""J.A.R.V.I.S. Floating Siri-Style Voice Bubble
A sleek, ambient HUD bubble widget in the top corner of the Windows screen.
Replaces the CMD terminal window with an interactive, animated Siri-like orb.

Features:
- Frameless, always-on-top, transparent rounded HUD pill.
- Real-time animated glowing Siri orb (pulsing breathing rings & audio reactivity).
- Speaks and interacts exactly like J.A.R.V.I.S. (greeting, STT, Gemini tools, SAPI5/ElevenLabs TTS).
- Single-instance IPC server on port 8799: Wakes up instantly when 'Hey Jarvis' is spoken.
- Click-to-talk: click the glowing orb anytime to speak immediately.
- Draggable across the desktop, auto-idle and auto-dismiss after completion.
"""

import os
import sys
import time
import math
import socket
import threading
import tkinter as tk
from tkinter import font as tkfont
from dotenv import load_dotenv

# Ensure client directory is on path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

load_dotenv()

# Import Jarvis voice engine modules
from windows_voice_controller import (
    speak_jarvis,
    play_chime,
    play_done_chime,
    VoiceController,
    SAMPLE_RATE,
    CHANNELS,
    FRAME_SAMPLES,
    MAX_BUFFER_FRAMES,
    COMMAND_SECONDS,
    WAKE_THRESHOLD
)
from win_tools import WindowsController

IPC_PORT = 8799
BUBBLE_WIDTH = 390
BUBBLE_HEIGHT = 100
CORNER_OFFSET_X = 35
CORNER_OFFSET_Y = 28


class SiriOrbAnimator:
    """Draws an animated, multi-layered Siri-like glowing orb with harmonic wave rings."""
    def __init__(self, canvas: tk.Canvas, center_x: int, center_y: int, radius: int):
        self.canvas = canvas
        self.cx = center_x
        self.cy = center_y
        self.base_radius = radius
        self.phase = 0.0
        self.state = "IDLE"  # IDLE, GREETING, LISTENING, PROCESSING, SPEAKING
        self.mic_level = 0.0

    def set_state(self, state: str):
        self.state = state

    def set_mic_level(self, level: float):
        self.mic_level = min(max(level, 0.0), 1.0)

    def draw_frame(self):
        self.phase += 0.08
        self.canvas.delete("orb")

        # Color schemes based on state
        if self.state == "LISTENING":
            colors = ["#00f2fe", "#38bdf8", "#818cf8", "#f43f5e"]
            pulse_amp = 7.0 + self.mic_level * 18.0
            speed = 1.6
        elif self.state == "PROCESSING":
            colors = ["#a855f7", "#ec4899", "#00f2fe", "#6366f1"]
            pulse_amp = 8.0
            speed = 2.4
        elif self.state == "SPEAKING":
            colors = ["#00f2fe", "#10b981", "#38bdf8", "#06b6d4"]
            pulse_amp = 6.0
            speed = 1.3
        else:  # IDLE / STANDBY
            colors = ["#0ea5e9", "#6366f1", "#0284c7", "#38bdf8"]
            pulse_amp = 3.5
            speed = 0.8

        # Draw 4 concentric dynamic rings
        for i in range(4, 0, -1):
            ring_phase = self.phase * speed + (i * 0.7)
            distortion = math.sin(ring_phase) * pulse_amp
            r = max(8, self.base_radius * (i / 4.0) + distortion)
            color = colors[i - 1]

            # Outer aura rings vs core
            if i == 4:
                # Soft outer glow
                self.canvas.create_oval(
                    self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                    outline=color, width=2, tags="orb"
                )
            elif i == 3:
                self.canvas.create_oval(
                    self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                    outline=color, width=3, tags="orb"
                )
            elif i == 2:
                self.canvas.create_oval(
                    self.cx - r, self.cy - r, self.cx + r, self.cy + r,
                    fill=color, outline="", tags="orb"
                )
            else:
                # Inner bright white/cyan core
                core_r = max(4, r * 0.6)
                self.canvas.create_oval(
                    self.cx - core_r, self.cy - core_r, self.cx + core_r, self.cy + core_r,
                    fill="#ffffff", outline="", tags="orb"
                )


class JarvisBubbleApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. Siri Bubble")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Transparent background configuration for Windows
        self.root.attributes("-transparentcolor", "#010101")
        self.root.config(bg="#010101")

        # Position in top-right corner of screen
        screen_w = self.root.winfo_screenwidth()
        x_pos = screen_w - BUBBLE_WIDTH - CORNER_OFFSET_X
        y_pos = CORNER_OFFSET_Y
        self.root.geometry(f"{BUBBLE_WIDTH}x{BUBBLE_HEIGHT}+{x_pos}+{y_pos}")

        # Dragging mechanics
        self.drag_x = 0
        self.drag_y = 0

        # Create Canvas for the sleek pill HUD
        self.canvas = tk.Canvas(
            self.root,
            width=BUBBLE_WIDTH,
            height=BUBBLE_HEIGHT,
            bg="#010101",
            highlightthickness=0,
            cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw HUD Capsule background
        self._draw_capsule_hud()

        # Siri Orb Animator (center at x=52, y=50)
        self.orb = SiriOrbAnimator(self.canvas, center_x=52, center_y=50, radius=32)

        # Text labels on Canvas
        self.title_id = self.canvas.create_text(
            106, 32,
            text="J.A.R.V.I.S.",
            anchor="w",
            fill="#00f2fe",
            font=("Segoe UI", 11, "bold")
        )

        self.status_id = self.canvas.create_text(
            106, 58,
            text="Say 'Hey Jarvis' or click to talk",
            anchor="w",
            fill="#94a3b8",
            font=("Segoe UI", 9)
        )

        # Close/Dismiss icon
        self.close_btn_id = self.canvas.create_text(
            BUBBLE_WIDTH - 24, 24,
            text="✕",
            anchor="center",
            fill="#64748b",
            font=("Segoe UI", 10, "bold")
        )

        # Bind events
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.root.bind("<Escape>", lambda e: self.hide_bubble())

        # Initialize Voice Engine
        self.voice_controller = None
        self.is_busy = False
        self.auto_hide_timer = None

        # Start IPC Server for single instance communication
        self._start_ipc_server()

        # Start animation loop
        self._animate_orb()

        # Initialize Voice Controller in background thread
        threading.Thread(target=self._init_voice_controller, daemon=True).start()

    def _draw_capsule_hud(self):
        """Draws a smooth rounded pill HUD card with border glow."""
        r = 24  # corner radius
        w = BUBBLE_WIDTH - 6
        h = BUBBLE_HEIGHT - 6
        x0, y0 = 3, 3
        x1, y1 = x0 + w, y0 + h

        points = [
            x0 + r, y0,
            x1 - r, y0,
            x1, y0,
            x1, y0 + r,
            x1, y1 - r,
            x1, y1,
            x1 - r, y1,
            x0 + r, y1,
            x0, y1,
            x0, y1 - r,
            x0, y0 + r,
            x0, y0,
            x0 + r, y0
        ]
        # Smooth polygon capsule
        self.canvas.create_polygon(
            points,
            smooth=True,
            fill="#090e17",
            outline="#0ea5e9",
            width=2,
            tags="hud_card"
        )

    def _animate_orb(self):
        self.orb.draw_frame()
        self.root.after(35, self._animate_orb)

    def set_status(self, title: str, subtitle: str, state: str = "IDLE", mic_level: float = 0.0):
        """Thread-safe UI status update."""
        def update():
            self.canvas.itemconfig(self.title_id, text=title)
            # Truncate subtitle to fit capsule neatly
            display_sub = subtitle if len(subtitle) < 42 else subtitle[:40] + "..."
            self.canvas.itemconfig(self.status_id, text=display_sub)
            self.orb.set_state(state)
            self.orb.set_mic_level(mic_level)
            self.show_bubble()
        self.root.after(0, update)

    def show_bubble(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def hide_bubble(self):
        self.root.withdraw()

    def _on_canvas_click(self, event):
        # Check if clicked close button
        if event.x >= BUBBLE_WIDTH - 36 and event.y <= 36:
            self.hide_bubble()
            return

        # Check if clicked the orb or body to talk
        self.drag_x = event.x
        self.drag_y = event.y

        if not self.is_busy:
            threading.Thread(target=self.trigger_session, daemon=True).start()

    def _on_canvas_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _init_voice_controller(self):
        try:
            self.voice_controller = VoiceController()
            self.set_status("J.A.R.V.I.S.", "Online & listening. Say 'Hey Jarvis'")
        except Exception as e:
            print(f"[Bubble Voice Init Note]: {e}", flush=True)
            self.set_status("J.A.R.V.I.S.", "Ready (Click orb to speak)")

    def trigger_session(self):
        """Executes full Jarvis voice intake, execution, and speech feedback."""
        if self.is_busy:
            return
        self.is_busy = True

        if self.auto_hide_timer:
            self.root.after_cancel(self.auto_hide_timer)
            self.auto_hide_timer = None

        try:
            self.set_status("J.A.R.V.I.S.", "Greeting Sir...", state="GREETING")
            play_chime()

            # 1. Greet
            greeting = "Hello, Sir. How may I assist you?"
            self.set_status("J.A.R.V.I.S.", greeting, state="SPEAKING")
            speak_jarvis(greeting)

            # 2. Listen
            self.set_status("J.A.R.V.I.S.", "Listening for command...", state="LISTENING", mic_level=0.5)
            
            if not self.voice_controller:
                self.voice_controller = VoiceController()

            vc = self.voice_controller
            # Drain stream to clear echo
            time.sleep(0.15)
            vc.ring.drain()
            while vc.stream.get_read_available() > 0:
                vc.stream.read(vc.stream.get_read_available(), exception_on_overflow=False)

            # Voice Activity Detection (VAD) listening loop
            import numpy as np
            ambient_rms = []
            for _ in range(int(SAMPLE_RATE / FRAME_SAMPLES * 0.1)):
                f = vc.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                s = np.frombuffer(f, dtype=np.int16)
                if s.size:
                    ambient_rms.append(float(np.sqrt(np.mean(s.astype(np.float32) ** 2))))

            baseline = np.mean(ambient_rms) if ambient_rms else 100.0
            silence_threshold = max(baseline * 1.6, 250.0)
            silence_duration_ms = 500
            max_seconds = 10

            frames = []
            speech_started = False
            silent_since = None
            start_time = time.monotonic()

            while time.monotonic() - start_time < max_seconds:
                frame = vc.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                frames.append(frame)

                samples = np.frombuffer(frame, dtype=np.int16)
                rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if samples.size else 0.0

                # Dynamic orb sound reactivity
                normalized_level = min(rms / 1200.0, 1.0)
                self.orb.set_mic_level(normalized_level)

                if rms > silence_threshold:
                    speech_started = True
                    silent_since = None
                elif speech_started:
                    if silent_since is None:
                        silent_since = time.monotonic()
                    elif (time.monotonic() - silent_since) * 1000.0 >= silence_duration_ms:
                        break

            play_done_chime()
            pcm = b"".join(frames)

            # 3. Transcribe
            self.set_status("J.A.R.V.I.S.", "Transcribing audio...", state="PROCESSING")
            command = vc.transcribe(pcm)
            clean_cmd = command.replace("Hey Jarvis", "").replace("hey jarvis", "").strip()

            if clean_cmd and len(clean_cmd) > 2 and "hello, sir" not in clean_cmd.lower():
                self.set_status("J.A.R.V.I.S.", f"\"{clean_cmd}\"", state="PROCESSING")

                # 4. Execute command or query agent
                if hasattr(vc, 'agent') and vc.agent is not None:
                    vc.agent.handle_user_query(clean_cmd)
                else:
                    vc.execute(clean_cmd)

                self.set_status("J.A.R.V.I.S.", "Completed directive, Sir.", state="SPEAKING")
            else:
                reply = "Let's hope for next time, Sir."
                self.set_status("J.A.R.V.I.S.", reply, state="SPEAKING")
                speak_jarvis(reply)

        except Exception as err:
            print(f"[Bubble Interaction Error]: {err}", flush=True)
            self.set_status("J.A.R.V.I.S.", "Error processing command", state="IDLE")
        finally:
            self.is_busy = False
            self.set_status("J.A.R.V.I.S.", "Standby. Say 'Hey Jarvis' or click", state="IDLE")
            
            # Schedule subtle idle delay
            self.auto_hide_timer = self.root.after(12000, lambda: self.set_status("J.A.R.V.I.S.", "Ready (Standby)", state="IDLE"))

    def _start_ipc_server(self):
        """Listens on local port 8799 for WAKE triggers from the background daemon."""
        def server_worker():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", IPC_PORT))
                sock.listen(5)
                while True:
                    conn, _ = sock.accept()
                    with conn:
                        data = conn.recv(128).decode("utf-8", errors="ignore")
                        if "WAKE" in data:
                            # Trigger session on voice thread
                            threading.Thread(target=self.trigger_session, daemon=True).start()
            except Exception as e:
                print(f"[Bubble IPC Error]: {e}", flush=True)
            finally:
                sock.close()

        threading.Thread(target=server_worker, daemon=True).start()

    def run(self):
        self.root.mainloop()


def wake_existing_bubble() -> bool:
    """Tries to send a wake command to an already running bubble."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.6)
            s.connect(("127.0.0.1", IPC_PORT))
            s.sendall(b"WAKE\n")
            return True
    except Exception:
        return False


if __name__ == "__main__":
    # If already running, wake the existing bubble and exit
    if wake_existing_bubble():
        sys.exit(0)

    # Launch bubble application
    app = JarvisBubbleApp()
    # Trigger initial intro greeting if launched directly by user
    threading.Thread(target=app.trigger_session, daemon=True).start()
    app.run()
