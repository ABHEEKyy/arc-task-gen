"""Hands-free Windows voice control using openWakeWord and tool calling.

Run with: py clients/windows/windows_voice_controller.py
Required environment variable: OPENAI_API_KEY
Optional: OPENAI_BASE_URL and VOICE_MODEL.
"""

import json
import os
import tempfile
import threading
import wave

import numpy as np
import openwakeword
import pyaudio
from openai import OpenAI
from openwakeword.model import Model

from audio_buffer import AudioRingBuffer
from win_tools import WindowsController

SAMPLE_RATE = 16_000
CHANNELS = 1
FRAME_SAMPLES = 320
BUFFER_SECONDS = 1.5
MAX_BUFFER_FRAMES = int(BUFFER_SECONDS / 0.02)
COMMAND_SECONDS = 4
WAKE_THRESHOLD = 0.6

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


class VoiceController:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY before starting the Windows voice controller.")
        base_url = os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
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
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
            path = file.name
        try:
            with wave.open(path, "wb") as output:
                output.setnchannels(CHANNELS)
                output.setsampwidth(2)
                output.setframerate(SAMPLE_RATE)
                output.writeframes(pcm)
            with open(path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(model=os.getenv("STT_MODEL", "whisper-1"), file=audio_file)
            return response.text.strip()
        finally:
            os.unlink(path)

    def execute(self, text: str) -> None:
        response = self.client.chat.completions.create(
            model=os.getenv("VOICE_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "You control Windows. Ignore leading Hey Jarvis. Use one tool only when the command is explicit; otherwise ask for clarification."},
                {"role": "user", "content": text},
            ],
            tools=TOOLS,
            tool_choice="auto",
        )
        for call in response.choices[0].message.tool_calls or []:
            function = getattr(WindowsController, call.function.name, None)
            if function:
                result = function(**json.loads(call.function.arguments))
                print(f"{call.function.name}: {result}")

    def run(self) -> None:
        openwakeword.utils.download_models()
        model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        print("Ready. Say 'Hey Jarvis' followed by a Windows command.")
        try:
            while not self.stop_event.is_set():
                frame = self.stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                self.ring.append(frame)
                prediction = model.predict(np.frombuffer(frame, dtype=np.int16))
                if prediction.get("hey_jarvis", 0.0) < WAKE_THRESHOLD:
                    continue
                play_chime()
                command = self.transcribe(self.record_command(self.ring.drain()))
                if command:
                    print(f"Command: {command}")
                    self.execute(command)
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()


def play_chime() -> None:
    import winsound

    winsound.Beep(880, 80)


if __name__ == "__main__":
    VoiceController().run()
