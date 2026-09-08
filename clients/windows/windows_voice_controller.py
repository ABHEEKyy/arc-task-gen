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
BUFFER_SECONDS = 1.5
MAX_BUFFER_FRAMES = int(BUFFER_SECONDS / (FRAME_SAMPLES / SAMPLE_RATE))
COMMAND_SECONDS = 6
WAKE_THRESHOLD = 0.65

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Launch calculator, notepad, paint, explorer, or an http(s) URL.",
            "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]},
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
    """TTS router: Local XTTS v2 -> ElevenLabs -> Rime TTS -> Fallback"""
    # 0. Try Local Coqui XTTS v2 if jarvis_reference.wav is present
    local_engine = get_local_jarvis_engine()
    if local_engine and getattr(local_engine, 'model', None) is not None:
        try:
            local_engine.speak_stream(text)
            return
        except Exception as e:
            print(f"[Local XTTS Error]: {e}", flush=True)

    api_key = os.getenv("RIME_API_KEY")
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    jarvis_voice_id = os.getenv("ELEVENLABS_JARVIS_VOICE_ID")
    
    # 1. Try ElevenLabs voice clone if credentials set
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
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                audio_data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                eq_audio = apply_jarvis_eq(audio_data, sr)
                sd.play(eq_audio, sr)
                sd.wait()
                return
        except Exception as e:
            print(f"[ElevenLabs TTS Error]: {e}", flush=True)

    # 2. Rime TTS with Spencer British Voice
    if api_key:
        try:
            import requests, io
            import soundfile as sf
            import sounddevice as sd
            rime_url = os.getenv("RIME_TTS_URL", "https://users.rime.ai/v1/rime-tts")
            res = requests.post(
                rime_url,
                json={
                    "text": text,
                    "speaker": "spencer",
                    "speedAlpha": 0.95,
                    "samplingRate": 24000,
                    "modelId": "mistv3"
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if res.status_code == 200:
                audio_data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                eq_audio = apply_jarvis_eq(audio_data, sr)
                sd.play(eq_audio, sr)
                sd.wait()
                return
        except Exception as e:
            print(f"[Rime TTS Error]: {e}", flush=True)

    # 3. Windows Native SAPI5 Speech Fallback
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # Set male voice if available
        voices = engine.getProperty('voices')
        for v in voices:
            if 'david' in v.name.lower() or 'male' in v.name.lower() or 'george' in v.name.lower():
                engine.setProperty('voice', v.id)
                break
        engine.setProperty('rate', 160)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[Native TTS Error]: {e}", flush=True)


class VoiceController:
    def __init__(self) -> None:
        from google import genai
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("Set GEMINI_API_KEY before starting the Windows voice controller.")
        self.gclient = genai.Client(api_key=gemini_key)
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
            response = self.gclient.models.generate_content(
                model="gemini-flash-latest",
                contents=[
                    types.Part.from_bytes(data=audio_data, mime_type="audio/wav"),
                    "Transcribe the audio accurately into English text. Output ONLY the raw transcribed text."
                ]
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
        finally:
            if os.path.exists(path):
                os.unlink(path)


    def execute(self, text: str) -> None:
        win = WindowsController()
        text_lower = text.lower()
        print(f">> Executing command logic for: '{text}'", flush=True)
        
        # 1. Execute action immediately (Zero Lag)
        if any(w in text_lower for w in ["notepad", "netpad", "note pad", "notes"]):
            win.launch_application("notepad")
        elif any(w in text_lower for w in ["calculator", "calc", "calculate"]):
            win.launch_application("calculator")
        elif any(w in text_lower for w in ["paint", "mspaint", "draw"]):
            win.launch_application("paint")
        elif any(w in text_lower for w in ["explorer", "file explorer", "my computer", "files"]):
            win.launch_application("explorer")
        elif "volume up" in text_lower or "increase volume" in text_lower or "louder" in text_lower:
            win.system_volume("up", 10)
        elif "volume down" in text_lower or "decrease volume" in text_lower or "quieter" in text_lower:
            win.system_volume("down", 10)
        elif "mute" in text_lower or "unmute" in text_lower:
            win.system_volume("mute")
        elif "close" in text_lower or "shut" in text_lower:
            win.window_management("close")
        elif "minimize" in text_lower:
            win.window_management("minimize")
        elif "maximize" in text_lower:
            win.window_management("maximize")

        # 2. Concurrently speak sign-off
        reply = "It was a pleasure helping, Sir."
        print(f"[Jarvis]: {reply}", flush=True)
        speak_jarvis(reply)

    def run(self) -> None:
        openwakeword.utils.download_models()
        model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print("\n==========================================", flush=True)
        print("Listening... Say 'Hey Jarvis' to activate!", flush=True)
        print("==========================================\n", flush=True)
        try:
            while not self.stop_event.is_set():
                frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                self.ring.append(frame)
                prediction = model.predict(np.frombuffer(frame, dtype=np.int16))
                score = prediction.get("hey_jarvis", 0.0)
                if score < WAKE_THRESHOLD:
                    continue
                print(f"\n>> [Wake Word Detected! (score: {score:.2f})]", flush=True)
                play_chime()
                
                # 1. Greet with Hello in British Voice (Microphone stream paused during speech)
                greeting = "Hello, Sir. How may I assist you?"
                print(f"[Jarvis]: {greeting}", flush=True)
                speak_jarvis(greeting)

                # 2. Wait up to 35 seconds for user command with fast 400ms VAD
                print(">> Listening for your command (up to 35 seconds)...", flush=True)
                # Flush microphone buffer completely so greeting audio is not processed as a user command
                self.ring.drain()
                
                max_seconds = 35
                silence_threshold_rms = 450.0
                silence_duration_ms = 400  # 400ms sub-second reaction time
                
                frames = []
                speech_started = False
                silent_since = None
                start_time = time.monotonic()
                
                while time.monotonic() - start_time < max_seconds:
                    if self.stop_event.is_set():
                        break
                    frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                    frames.append(frame)
                    
                    # Calculate audio volume (RMS)
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
                
                if clean_command and len(clean_command) > 2 and "hello, sir" not in clean_command.lower() and "pleasure helping" not in clean_command.lower():
                    print(f">> Transcribed Command: \"{clean_command}\"", flush=True)
                    self.execute(clean_command)
                else:
                    timeout_msg = "Let's hope for next time, Sir."
                    print(f"[Jarvis]: {timeout_msg}", flush=True)
                    speak_jarvis(timeout_msg)
                
                # Drain audio buffer before returning to sleep state to avoid self-re-triggering
                self.ring.drain()
                print("\nListening again for 'Hey Jarvis'...\n", flush=True)
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


def play_chime() -> None:
    import winsound

    winsound.Beep(880, 100)


def play_done_chime() -> None:
    import winsound

    winsound.Beep(440, 100)


if __name__ == "__main__":
    VoiceController().run()
