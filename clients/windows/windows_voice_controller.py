"""Hands-free Windows voice control using openWakeWord and tool calling.

Run with: py clients/windows/windows_voice_controller.py
Required environment variable: OPENAI_API_KEY
Optional: OPENAI_BASE_URL and VOICE_MODEL.
"""

import json
import os
import tempfile
import threading
import time
import wave

from dotenv import load_dotenv

load_dotenv()

import logging
import warnings
warnings.filterwarnings("ignore")
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
logging.getLogger("root").setLevel(logging.ERROR)
logging.basicConfig(level=logging.ERROR)

import numpy as np
import openwakeword
import pyaudio
from openai import OpenAI
from openwakeword.model import Model

from audio_buffer import AudioRingBuffer
from win_tools import WindowsController

SAMPLE_RATE = 16_000
CHANNELS = 1
FRAME_SAMPLES = 1280
BUFFER_SECONDS = 2.0
MAX_BUFFER_FRAMES = int(BUFFER_SECONDS / (FRAME_SAMPLES / SAMPLE_RATE))
COMMAND_SECONDS = 8
WAKE_THRESHOLD = 0.25

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Opens an application, website, or utility. Strip phrases like 'open', 'launch', or 'start'. E.g., pass 'chrome' for 'open chrome', or 'spotify' for 'start spotify'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Short name or binary of the app, e.g. 'notepad', 'chrome', 'spotify', 'calc'"
                    }
                },
                "required": ["app_name"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_volume",
            "description": "Mute or adjust Windows master volume.",
            "parameters": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": ["mute", "up", "down"]}, "amount": {"type": "integer"}},
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "window_management",
            "description": "Minimize, maximize, or close the active window.",
            "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["minimize", "maximize", "close"]}}, "required": ["action"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_shortcut",
            "description": "Press a keyboard shortcut using supported modifier and navigation keys.",
            "parameters": {"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type user-provided text into the active application, up to 500 characters.",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        },
    },
]


JARVIS_PERSONA = (
    "You are J.A.R.V.I.S., the dry-witted, supremely capable British AI from Iron Man. "
    "Manner of speaking:\n"
    "- Address the user as 'Sir' occasionally, but without groveling.\n"
    "- Maintain an unshakeable, calm, polite, and slightly dry British composure.\n"
    "- Use British phrasing (e.g., 'Right away, Sir', 'I have initiated the protocol', 'Running diagnostics now').\n"
    "- Keep responses to 1-2 sharp, articulate sentences."
)


def apply_jarvis_eq(audio_samples: np.ndarray, sample_rate: int = 24000) -> np.ndarray:
    """Applies a high-pass cut and high-mid boost for crisp HUD audio presence."""
    from scipy import signal
    b_hp, a_hp = signal.butter(4, 120 / (0.5 * sample_rate), btype='highpass')
    filtered = signal.lfilter(b_hp, a_hp, audio_samples)
    filtered = filtered * 1.15
    return np.clip(filtered, -1.0, 1.0)


_local_jarvis_engine = None

def get_local_jarvis_engine():
    global _local_jarvis_engine
    if _local_jarvis_engine is None:
        try:
            from local_jarvis_tts import LocalJarvisTTS
            ref = os.path.join(os.path.dirname(__file__), "jarvis_reference.wav")
            if os.path.exists(ref):
                _local_jarvis_engine = LocalJarvisTTS(ref)
        except Exception as e:
            print(f"[Local XTTS Init Note]: {e}", flush=True)
    return _local_jarvis_engine


def speak_jarvis(text: str) -> None:
    """Instant TTS router: Local XTTS v2 (jarvis_reference.wav) -> ElevenLabs -> British Male PyTTSX3"""
    # 1. Local XTTS v2 Voice Cloning from jarvis_reference.wav (Paul Bettany / JARVIS)
    engine = get_local_jarvis_engine()
    if engine and engine.model is not None:
        try:
            print(f"[Jarvis Voice Cloned]: Speaking via jarvis_reference.wav...", flush=True)
            engine.speak_stream(text)
            return
        except Exception as ex:
            print(f"[Local Voice Clone Note]: {ex}", flush=True)

    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    jarvis_voice_id = os.getenv("ELEVENLABS_JARVIS_VOICE_ID")
    
    # 2. ElevenLabs API (if credentials set)
    if eleven_key and jarvis_voice_id:
        try:
            import requests, io
            import soundfile as sf
            import sounddevice as sd
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{jarvis_voice_id}/stream"
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.65, "similarity_boost": 0.85, "style": 0.15}
            }
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                audio_data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                eq_audio = apply_jarvis_eq(audio_data, sr)
                sd.play(eq_audio, sr)
                sd.wait()
                return
        except Exception:
            pass

    # 3. Fallback: Male British Voice (pyttsx3) - strictly avoiding female Siri-like voices
    try:
        import pyttsx3
        py_engine = pyttsx3.init()
        voices = py_engine.getProperty('voices')
        selected_voice = False
        for v in voices:
            v_name = v.name.lower()
            if ('george' in v_name or 'david' in v_name or 'daniel' in v_name or 'uk' in v_name or 'british' in v_name or 'male' in v_name) and 'female' not in v_name and 'siri' not in v_name:
                py_engine.setProperty('voice', v.id)
                selected_voice = True
                break
        if not selected_voice and voices:
            for v in voices:
                if 'female' not in v.name.lower() and 'siri' not in v.name.lower():
                    py_engine.setProperty('voice', v.id)
                    break
        py_engine.setProperty('rate', 165)
        py_engine.say(text)
        py_engine.runAndWait()
        return
    except Exception as e:
        print(f"[Native Speech Note]: {e}", flush=True)




class VoiceController:
    def __init__(self) -> None:
        from google import genai
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key or gemini_key == "your_gemini_api_key":
            raise RuntimeError("Please set your GEMINI_API_KEY in .env before running Jarvis (obtain a free key from https://aistudio.google.com/).")
        self.gclient = genai.Client(api_key=gemini_key)

        try:
            from jarvis_agent import JarvisAgent
            self.agent = JarvisAgent(speak_jarvis)
        except Exception as e:
            print(f"[Jarvis Agent Init Warning]: {e}", flush=True)
            self.agent = None
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SAMPLES,
        )
        self.ring = AudioRingBuffer(MAX_BUFFER_FRAMES)
        self.stop_event = threading.Event()

    def record_command(self, initial_frames: list[bytes]) -> bytes:
        frames = initial_frames[-MAX_BUFFER_FRAMES:]
        for _ in range(int(SAMPLE_RATE / FRAME_SAMPLES * COMMAND_SECONDS)):
            frames.append(self.stream.read(FRAME_SAMPLES, exception_on_overflow=False))
        return b"".join(frames)

    def transcribe(self, pcm: bytes) -> str:
        from google.genai import types
        if len(pcm) < SAMPLE_RATE * 0.3:  # skip transcription if recorded sound is under 300ms
            return ""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
            path = file.name
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(CHANNELS)
                output.setsampwidth(2)
                output.setframerate(SAMPLE_RATE)
                output.writeframes(pcm)
            with open(path, "rb") as audio_file:
                audio_data = audio_file.read()

            last_err = None

            # 1. Try SpeechRecognition for instant STT
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(path) as source:
                    audio_source = r.record(source)
                    text = r.recognize_google(audio_source)
                    if text and len(text.strip()) > 1:
                        print(f">> [Recognized Voice]: '{text.strip()}'", flush=True)
                        return text.strip()
            except Exception as e:
                last_err = e

            # 2. Try Gemini Speech STT
            try:
                response = self.gclient.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=[
                        types.Part.from_bytes(data=audio_data, mime_type="audio/wav"),
                        "Transcribe the audio accurately into English text. Output ONLY the raw transcribed text. If there is no audible human voice, output nothing."
                    ]
                )
                if response and response.text:
                    return (response.text or "").strip()
            except Exception as ex:
                last_err = ex

            # 3. Try local faster-whisper if available
            try:
                from faster_whisper import WhisperModel
                if not hasattr(self, '_fw_model'):
                    self._fw_model = WhisperModel("tiny", device="cpu", compute_type="int8")
                segments, _ = self._fw_model.transcribe(path)
                fw_text = " ".join([seg.text for seg in segments]).strip()
                if fw_text:
                    print(f">> [Local Faster-Whisper Used]: '{fw_text}'", flush=True)
                    return fw_text
            except Exception as e:
                last_err = e

            # 4. Fallback to free Google Speech Recognition
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(path) as source:
                    audio_source = r.record(source)
                    text = r.recognize_google(audio_source)
                    if text:
                        print(f">> [Fallback Local Transcriber Used]: '{text}'", flush=True)
                        return text
            except Exception as sr_err:
                last_err = sr_err

            if last_err:
                print(f"Transcription model error: {last_err}")
            return ""
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
        finally:
            if os.path.exists(path):
                os.unlink(path)


    def execute(self, text: str) -> None:
        win = WindowsController()
        text_lower = text.lower().strip()
        print(f">> Executing command logic for: '{text}'", flush=True)
        
        # 1. Immediate action execution
        executed = False
        from win_advanced_tools import SystemController

        if any(w in text_lower for w in ["kill", "terminate", "stop process", "close process"]):
            for kw in ["kill ", "terminate ", "stop process ", "close process "]:
                if kw in text_lower:
                    proc_name = text_lower.split(kw, 1)[1].strip()
                    res = SystemController.terminate_process(proc_name)
                    print(f"[Jarvis Action]: {res}", flush=True)
                    executed = True
                    break
        elif any(w in text_lower for w in ["system status", "telemetry", "cpu usage", "ram usage", "how is the system"]):
            res = SystemController.get_system_telemetry()
            print(f"[Jarvis Telemetry]: {res}", flush=True)
            speak_jarvis(res)
            return
        elif " on " in text_lower and any(b in text_lower for b in ["chrome", "edge", "brave", "firefox"]):
            # Browser targeted site launch e.g. "open youtube on chrome"
            parts = text_lower.replace("open ", "").replace("launch ", "").split(" on ", 1)
            site, browser = parts[0].strip(), parts[1].strip()
            res = SystemController.open_website(site, browser)
            print(f"[Jarvis Action]: {res}", flush=True)
            executed = True
        elif any(w in text_lower for w in ["open ", "launch ", "start "]):
            # Extract target app name after action verb
            for verb in ["open ", "launch ", "start "]:
                if verb in text_lower:
                    target_app = text_lower.split(verb, 1)[1].strip()
                    res = win.launch_application(target_app)
                    print(f"[Jarvis Action]: {res}", flush=True)
                    executed = True
                    break
        elif any(w in text_lower for w in ["sleep", "go to sleep", "goodnight", "turn off", "shutdown"]):
            reply = "Going to sleep mode. Goodnight, Sir."
            print(f"[Jarvis]: {reply}", flush=True)
            speak_jarvis(reply)
            return
        elif any(w in text_lower for w in ["notepad", "netpad", "note pad", "notes"]):
            win.launch_application("notepad")
            executed = True
        elif any(w in text_lower for w in ["calculator", "calc", "calculate"]):
            win.launch_application("calculator")
            executed = True
        elif any(w in text_lower for w in ["paint", "mspaint", "draw"]):
            win.launch_application("paint")
            executed = True
        elif any(w in text_lower for w in ["explorer", "file explorer", "my computer", "files"]):
            win.launch_application("explorer")
            executed = True
        elif "volume up" in text_lower or "increase volume" in text_lower or "louder" in text_lower:
            win.system_volume("up", 10)
            executed = True
        elif "volume down" in text_lower or "decrease volume" in text_lower or "quieter" in text_lower:
            win.system_volume("down", 10)
            executed = True
        elif "mute" in text_lower or "unmute" in text_lower:
            win.system_volume("mute")
            executed = True
        elif "close" in text_lower or "shut" in text_lower:
            win.window_management("close")
            executed = True
        elif "minimize" in text_lower:
            win.window_management("minimize")
            executed = True
        elif "maximize" in text_lower:
            win.window_management("maximize")
            executed = True
        elif not executed:
            res = win.launch_application(text_lower)
            print(f"[Jarvis Action]: {res}", flush=True)

    def run(self) -> None:
        openwakeword.utils.download_models()
        # Load available pretrained models (hey_jarvis and custom jarvis if available)
        models_to_load = ["hey_jarvis"]
        for path in openwakeword.get_pretrained_model_paths():
            if "jarvis" in os.path.basename(path).lower() and os.path.basename(path) not in models_to_load:
                models_to_load.append(path)

        # Set process priority to BELOW_NORMAL to prevent CPU micro-stutter in games/browsers
        try:
            import psutil
            psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass

        model = Model(wakeword_models=models_to_load)
        print("\n==========================================", flush=True)
        print("Jarvis Ready! Say 'Hello Jarvis' to give commands!", flush=True)
        print("==========================================\n", flush=True)
        try:
            while not self.stop_event.is_set():
                frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                self.ring.append(frame)
                prediction = model.predict(np.frombuffer(frame, dtype=np.int16))
                
                # Check maximum score across loaded jarvis models
                score = max([v for k, v in prediction.items() if "jarvis" in k.lower()], default=0.0)
                if score > 0.15 and score < WAKE_THRESHOLD:
                    print(f"[Mic Signal Detected] Score: {score:.2f} (Needs >= {WAKE_THRESHOLD})", flush=True)
                if score < WAKE_THRESHOLD:
                    time.sleep(0.002)
                    continue
                print(f"\n>> [Wake Word Detected! (score: {score:.2f})]", flush=True)
                play_chime()
                
                # 1. Greet with Hello in British Voice (Microphone stream paused during speech)
                greeting = "Hello, Sir. How may I assist you?"
                print(f"[Jarvis]: {greeting}", flush=True)
                speak_jarvis(greeting)

                # 2. Wait for user command with dynamic ambient noise sampling and VAD
                print(">> Listening for your command...", flush=True)
                
                # Drain stream to clear speaker echo from greeting
                time.sleep(0.2)
                self.ring.drain()
                while self.stream.get_read_available() > 0:
                    self.stream.read(self.stream.get_read_available(), exception_on_overflow=False)
                
                # Sample ambient noise baseline over 100ms
                ambient_rms = []
                for _ in range(int(SAMPLE_RATE / FRAME_SAMPLES * 0.1)):
                    f = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                    s = np.frombuffer(f, dtype=np.int16)
                    if s.size:
                        ambient_rms.append(float(np.sqrt(np.mean(s.astype(np.float32) ** 2))))
                
                baseline = np.mean(ambient_rms) if ambient_rms else 100.0
                silence_threshold_rms = max(baseline * 1.2, 120.0)
                silence_duration_ms = 350  # 350ms instant pause reaction time
                max_seconds = 8
                
                frames = []
                speech_started = False
                silent_since = None
                start_time = time.monotonic()
                
                while time.monotonic() - start_time < max_seconds:
                    if self.stop_event.is_set():
                        break
                    frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                    frames.append(frame)
                    
                    samples = np.frombuffer(frame, dtype=np.int16)
                    rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if samples.size else 0.0
                    
                    if rms > silence_threshold_rms:
                        speech_started = True
                        silent_since = None
                    elif speech_started:
                        if silent_since is None:
                            silent_since = time.monotonic()
                        elif (time.monotonic() - silent_since) * 1000.0 >= silence_duration_ms:
                            print(f">> Speech completed ({(time.monotonic() - start_time)*1000:.0f}ms)", flush=True)
                            break

                pcm = b"".join(frames)
                play_done_chime()
                
                # 3. Transcribe and execute or timeout
                command = self.transcribe(pcm)
                clean_command = command.replace("Hey Jarvis", "").replace("hey jarvis", "").strip()
                
                if "siri" in clean_command.lower():
                    print("[Jarvis]: Yielding control to Siri, Sir.", flush=True)
                    import sys, subprocess
                    if sys.platform == "darwin":
                        try:
                            # Trigger native macOS Siri via AppleScript shortcut
                            subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 49 using {fn}'], capture_output=True)
                        except Exception:
                            pass
                elif clean_command and len(clean_command) > 2 and "hello, sir" not in clean_command.lower() and "pleasure helping" not in clean_command.lower():
                    print(f">> Transcribed Command: \"{clean_command}\"", flush=True)
                    # Always execute system action (like launching apps, volume control, window management)
                    self.execute(clean_command)
                    # Also pass to agent for conversational reply if agent exists
                    if hasattr(self, 'agent') and self.agent is not None:
                        import threading
                        threading.Thread(target=self.agent.handle_user_query, args=(clean_command,), daemon=True).start()
                else:
                    timeout_msg = "Let's hope for next time, Sir."
                    print(f"[Jarvis]: {timeout_msg}", flush=True)
                    speak_jarvis(timeout_msg)
                
                # Drain audio buffer and reset wake model state to avoid self-re-triggering
                self.ring.drain()
                while self.stream.get_read_available() > 0:
                    self.stream.read(self.stream.get_read_available(), exception_on_overflow=False)
                if hasattr(model, "reset"):
                    model.reset()
                time.sleep(1.5)
                print("\nListening again for 'Hey Jarvis'...\n", flush=True)
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


def play_chime(frequency: int = 880, duration: float = 0.1) -> None:
    """Plays a crisp tone or futuristic wake chime."""
    try:
        import sounddevice as sd
        import numpy as np
        sr = 44100
        if frequency == 880 and duration == 0.1:
            # 880Hz -> 1320Hz ascending sci-fi chime
            t1 = np.linspace(0, 0.1, int(sr * 0.1), False)
            t2 = np.linspace(0, 0.15, int(sr * 0.15), False)
            tone1 = np.sin(2 * np.pi * 880 * t1) * 0.6
            tone2 = np.sin(2 * np.pi * 1320 * t2) * 0.7
            audio = np.concatenate([tone1, tone2]).astype(np.float32)
        else:
            t = np.linspace(0, duration, int(sr * duration), False)
            audio = (np.sin(2 * np.pi * frequency * t) * 0.5).astype(np.float32)
        sd.play(audio, sr)
        sd.wait()
    except Exception:
        try:
            import winsound
            winsound.Beep(int(frequency), int(duration * 1000))
        except Exception:
            pass



def play_done_chime() -> None:
    """Plays a descending tone indicating speech listening is finished."""
    try:
        import sounddevice as sd
        import numpy as np
        sr = 44100
        t1 = np.linspace(0, 0.12, int(sr * 0.12), False)
        tone = np.sin(2 * np.pi * 587 * t1) * 0.5
        sd.play(tone.astype(np.float32), sr)
        sd.wait()
    except Exception:
        import winsound
        winsound.Beep(587, 150)


def ensure_single_instance() -> object:
    """Enforce that only a single instance of the Jarvis Voice Controller terminal runs."""
    import ctypes
    import sys
    if not hasattr(ctypes, "windll"):
        return None
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "JarvisVoiceController_SingleInstance_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[Single Instance]: J.A.R.V.I.S. terminal is already running. Bringing active window to front...", flush=True)
        hwnd = ctypes.windll.user32.FindWindowW(None, "J.A.R.V.I.S. Conversational Terminal")
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        sys.exit(0)
    return mutex


if __name__ == "__main__":
    _mutex = ensure_single_instance()
    VoiceController().run()

