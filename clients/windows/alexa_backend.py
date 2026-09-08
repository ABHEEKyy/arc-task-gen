"""Conversational Windows assistant with streaming Rime speech output.

Run with: py clients/windows/alexa_backend.py
Required environment variables: OPENAI_API_KEY and RIME_API_KEY.
"""

import base64
import io
import json
import os
import queue
import threading
import time
from pathlib import Path

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from websockets.sync.client import connect
from openai import OpenAI

from windows_voice_controller import (
    FRAME_SAMPLES,
    TOOLS,
    WAKE_THRESHOLD,
    VoiceController,
    play_chime,
)
from web_tools import RealtimeTools
from win_tools import WindowsController

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

RIME_TTS_URL = os.getenv("RIME_TTS_URL", "https://users.rime.ai/v1/rime-tts")
RIME_WS_URL = os.getenv(
    "RIME_WS_URL",
    "wss://users-ws.rime.ai/ws3?speaker=celeste&modelId=mistv3&audioFormat=pcm&samplingRate=24000",
)
MAX_HISTORY_MESSAGES = 12
VAD_SILENCE_SECONDS = 1.2
FOLLOW_UP_SECONDS = 6.0
MAX_UTTERANCE_SECONDS = 10.0
VAD_RMS_THRESHOLD = 500.0
REALTIME_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the live web for current events, news, sports, facts, or updates.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current conditions and today's forecast for a city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    },
]


class SpeechOutput:
    """Persistent Rime WebSocket playback with HTTP sentence fallback."""

    def __init__(self) -> None:
        self._token_queue: queue.Queue[str | None] = queue.Queue()
        self._sentence_queue: queue.Queue[str | None] = queue.Queue()
        self._stop_event = threading.Event()
        self._connected = threading.Event()
        self._socket = None
        self._socket_lock = threading.Lock()
        self._fallback_buffer = ""
        self._fallback_lock = threading.Lock()
        self._output_stream = None
        self._output_lock = threading.Lock()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()
        self._connected.wait(timeout=1.0)

    def say_sentence(self, text: str) -> None:
        if text.strip():
            if self._connected.is_set():
                self._token_queue.put(text.strip())
            else:
                self._sentence_queue.put(text.strip())

    def say_token(self, token: str) -> None:
        if not token:
            return
        if self._connected.is_set():
            self._token_queue.put(token)
            return
        with self._fallback_lock:
            self._fallback_buffer += token
            while True:
                boundary = next((index for index, char in enumerate(self._fallback_buffer) if char in ".?!\n"), None)
                if boundary is None:
                    break
                sentence = self._fallback_buffer[: boundary + 1].strip()
                self._fallback_buffer = self._fallback_buffer[boundary + 1 :].lstrip()
                if sentence:
                    self.say_sentence(sentence)

    def flush_tokens(self) -> None:
        if self._connected.is_set():
            self._token_queue.put("")
            return
        with self._fallback_lock:
            if self._fallback_buffer.strip():
                self.say_sentence(self._fallback_buffer.strip())
                self._fallback_buffer = ""

    def interrupt(self) -> None:
        sd.stop()
        self._clear_queue(self._token_queue)
        self._clear_queue(self._sentence_queue)
        with self._fallback_lock:
            self._fallback_buffer = ""
        with self._socket_lock:
            if self._socket is not None:
                try:
                    self._socket.send(json.dumps({"operation": "clear"}))
                except Exception:
                    pass
        with self._output_lock:
            if self._output_stream is not None:
                self._output_stream.abort()
                self._output_stream.close()
                self._output_stream = None

    def close(self) -> None:
        self._stop_event.set()
        self.interrupt()
        self._token_queue.put(None)
        self._sentence_queue.put(None)
        self._worker.join(timeout=2)

    def _run(self) -> None:
        rime_key = os.getenv("RIME_API_KEY")
        if rime_key and rime_key != "your_rime_api_key":
            try:
                self._run_websocket()
                return
            except Exception as error:
                print(f"[TTS Info]: Rime WebSocket unavailable ({error}); using local/HTTP fallback.")
        self._run_http_fallback()

    def _run_websocket(self) -> None:
        with connect(
            RIME_WS_URL,
            additional_headers={"Authorization": f"Bearer {os.environ['RIME_API_KEY']}"},
            open_timeout=5,
        ) as socket:
            with self._socket_lock:
                self._socket = socket
            self._connected.set()
            receiver = threading.Thread(target=self._receive_audio, args=(socket,), daemon=True)
            receiver.start()
            while not self._stop_event.is_set():
                token = self._token_queue.get()
                if token is None:
                    return
                message = {"operation": "flush"} if token == "" else {"text": token}
                socket.send(json.dumps(message))
                self._token_queue.task_done()
            with self._socket_lock:
                self._socket = None

    def _receive_audio(self, socket: object) -> None:
        while not self._stop_event.is_set():
            try:
                message = socket.recv(timeout=1)
            except TimeoutError:
                continue
            except Exception:
                return
            if not isinstance(message, str):
                continue
            payload = json.loads(message)
            encoded = payload.get("audio")
            if encoded:
                self._play_pcm(base64.b64decode(encoded))

    def _run_http_fallback(self) -> None:
        while not self._stop_event.is_set():
            text = self._sentence_queue.get()
            try:
                if text is None:
                    return
                self._speak_http(text)
            finally:
                self._sentence_queue.task_done()

    @staticmethod
    def _clear_queue(items: queue.Queue[str | None]) -> None:
        while True:
            try:
                items.get_nowait()
                items.task_done()
            except queue.Empty:
                return

    def _speak_http(self, text: str) -> None:
        api_key = os.getenv("RIME_API_KEY")
        if api_key and api_key != "your_rime_api_key":
            try:
                response = requests.post(
                    RIME_TTS_URL,
                    json={
                        "text": text,
                        "speaker": os.getenv("RIME_VOICE", "celeste"),
                        "speedAlpha": float(os.getenv("RIME_SPEED_ALPHA", "1.05")),
                        "samplingRate": 24_000,
                    },
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=20,
                )
                response.raise_for_status()
                audio, sample_rate = sf.read(io.BytesIO(response.content), dtype="float32")
                sd.play(audio, sample_rate)
                sd.wait()
                return
            except Exception as e:
                print(f"[Rime Cloud TTS Note]: {e}; using Windows native voice.")

        # Local zero-lag Windows SAPI5 voice
        try:
            from windows_voice_controller import speak_jarvis
            speak_jarvis(text)
        except Exception as e:
            print(f"[Local TTS Error]: {e}")


    def _play_pcm(self, audio: bytes) -> None:
        with self._output_lock:
            if self._output_stream is None:
                self._output_stream = sd.RawOutputStream(samplerate=24_000, channels=1, dtype="int16")
                self._output_stream.start()
            self._output_stream.write(audio)


class AudioDucker:
    """Temporarily lowers active Windows audio sessions while listening."""

    def __init__(self) -> None:
        self._levels: list[tuple[object, float]] = []

    def duck(self, level: float = 0.2) -> None:
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        except ImportError:
            print("Audio ducking unavailable; install pycaw.")
            return
        self._levels.clear()
        for session in AudioUtilities.GetAllSessions():
            if not session.Process:
                continue
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            current = float(volume.GetMasterVolume())
            self._levels.append((volume, current))
            volume.SetMasterVolume(level, None)

    def restore(self) -> None:
        for volume, level in self._levels:
            volume.SetMasterVolume(level, None)
        self._levels.clear()


class ConversationalController(VoiceController):
    def __init__(self) -> None:
        super().__init__()
        if not os.getenv("RIME_API_KEY"):
            print("RIME_API_KEY is not set; replies will be printed instead of spoken.")
        self.history: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "You are a concise, natural Windows voice assistant. Answer general questions and use desktop tools when needed. "
                    "Ignore the leading Hey Jarvis wake phrase. Never use markdown. Keep spoken answers to two or three sentences."
                ),
            }
        ]
        self.output = SpeechOutput()
        self.ducker = AudioDucker()

    def record_until_silence(self, initial_frames: list[bytes], wait_seconds: float) -> bytes:
        """Capture one utterance until speech ends, without a fixed-duration wait."""
        frames = list(initial_frames)
        # Pre-roll includes the wake phrase and must not satisfy command VAD.
        started = False
        silent_since = None
        deadline = time.monotonic() + MAX_UTTERANCE_SECONDS
        wait_deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
            frames.append(frame)
            self.ring.append(frame)
            loud = self._rms(frame) > VAD_RMS_THRESHOLD
            if loud:
                started = True
                silent_since = None
                continue
            if not started:
                if time.monotonic() >= wait_deadline:
                    return b""
                continue
            silent_since = silent_since or time.monotonic()
            if time.monotonic() - silent_since >= VAD_SILENCE_SECONDS:
                break
        return b"".join(frames)

    @staticmethod
    def _rms(frame: bytes) -> float:
        samples = np.frombuffer(frame, dtype=np.int16)
        return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if samples.size else 0.0

    def execute_turn(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})
        self.history = [self.history[0]] + self.history[-MAX_HISTORY_MESSAGES:]
        
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.history if msg.get("content")])
        try:
            response = self.gclient.models.generate_content(
                model="gemini-3.6-flash",
                contents=f"You are J.A.R.V.I.S., a helpful Windows voice assistant. Keep spoken answers concise (1-2 sentences). Prompt: {prompt}"
            )
            reply = response.text or ""
            print(f"Assistant: {reply}")
            self.history.append({"role": "assistant", "content": reply})
            self.output.say_sentence(reply)
        except Exception as e:
            print(f"Gemini execution error: {e}")

    def run(self) -> None:
        import openwakeword
        from openwakeword.model import Model

        openwakeword.utils.download_models()
        model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print("J.A.R.V.I.S. ambient listener online. Speak into your microphone to activate!")
        try:
            while not self.stop_event.is_set():
                # Dormant: local wake-word + Voice Activity Detection runs here.
                frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                self.ring.append(frame)
                pcm = np.frombuffer(frame, dtype=np.int16)
                rms = float(np.sqrt(np.mean(pcm.astype(np.float32)**2)))
                prediction = model.predict(pcm)
                score = prediction.get("hey_jarvis", 0.0)
                if score < WAKE_THRESHOLD and rms < 1200.0:
                    continue
                print(f"[Detected Voice! RMS={rms:.0f}, Score={score:.4f}] Listening...")
                self.output.interrupt()
                self.ducker.duck()
                play_chime()
                try:
                    active = True
                    first_turn = True
                    while active and not self.stop_event.is_set():
                        # Active listening: first turn includes the wake-word pre-roll;
                        # follow-ups get a six-second conversational latch.
                        initial_frames = self.ring.drain() if first_turn else []
                        audio = self.record_until_silence(initial_frames, FOLLOW_UP_SECONDS)
                        first_turn = False
                        if not audio:
                            break
                        command = self.transcribe(audio)
                        if not command:
                            break
                        print(f"User: {command}")
                        self.execute_turn(command)
                        play_chime(frequency=600, duration=0.08)
                finally:
                    self.ducker.restore()
        finally:
            self.output.close()
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


if __name__ == "__main__":
    ConversationalController().run()
