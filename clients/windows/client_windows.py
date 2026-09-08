"""Windows zero-loss wake-word gatekeeper for the Voice IoT backend.

The microphone never stops between sleeping and listening. A thread-safe 1.5s
PCM ring buffer bridges wake detection and the LiveKit ICE/DTLS handshake.

Install: pip install -r clients/windows/requirements.txt
"""

import asyncio
import os
import queue
import threading

import numpy as np
import openwakeword
import pyaudio
import requests
from livekit import rtc
from openwakeword.model import Model

from audio_buffer import AudioRingBuffer

API_URL = os.getenv("VOICE_API_URL", "http://localhost:8000")
SAMPLE_RATE = 16_000
CHANNELS = 1
FRAME_SAMPLES = 320  # 20 ms at 16 kHz
FRAME_BYTES = FRAME_SAMPLES * 2
BUFFER_SECONDS = 1.5
MAX_BUFFER_FRAMES = int(BUFFER_SECONDS / 0.02)
WAKE_THRESHOLD = 0.6


class ContinuousCapture:
    """Owns PyAudio, wake detection, pre-roll, and post-handoff delivery."""

    def __init__(self) -> None:
        self.ring = AudioRingBuffer(MAX_BUFFER_FRAMES)
        self.live_frames: queue.Queue[bytes] = queue.Queue()
        self.wake_event = threading.Event()
        self.stop_event = threading.Event()
        self._wake_armed = True
        self._wake_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._audio: pyaudio.PyAudio | None = None
        self._stream = None

    def start(self) -> None:
        openwakeword.utils.download_models()
        model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=FRAME_SAMPLES,
        )
        self._thread = threading.Thread(target=self._capture_loop, args=(model,), daemon=True)
        self._thread.start()

    def _capture_loop(self, model: Model) -> None:
        while not self.stop_event.is_set():
            try:
                data = self._stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                if len(data) != FRAME_BYTES:
                    continue
                is_streaming = self.ring.append(data)
                if is_streaming:
                    self.publish_live(data)
                prediction = model.predict(np.frombuffer(data, dtype=np.int16))
                with self._wake_lock:
                    should_trigger = self._wake_armed and prediction.get("hey_jarvis", 0.0) >= WAKE_THRESHOLD
                    if should_trigger:
                        self._wake_armed = False
                if should_trigger:
                    play_chime()
                    self.wake_event.set()
            except Exception as error:
                print(f"Mic capture error: {error}")
                self.stop_event.set()

    def begin_live_delivery(self) -> list[bytes]:
        """Atomically choose the handoff point, preventing a gap or duplicate frame."""
        return self.ring.begin_stream()

    def publish_live(self, frame: bytes) -> None:
        self.live_frames.put_nowait(frame)

    def reset_to_sleeping(self) -> None:
        self.ring.stop_stream()
        while not self.live_frames.empty():
            self.live_frames.get_nowait()
        with self._wake_lock:
            self._wake_armed = True
        self.wake_event.clear()

    def close(self) -> None:
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio:
            self._audio.terminate()


def play_chime() -> None:
    import winsound

    winsound.Beep(880, 80)


def frame_from_pcm(data: bytes) -> rtc.AudioFrame:
    return rtc.AudioFrame(
        data=data,
        sample_rate=SAMPLE_RATE,
        num_channels=CHANNELS,
        samples_per_channel=FRAME_SAMPLES,
    )


def fetch_session() -> tuple[str, str]:
    response = requests.post(
        f"{API_URL}/api/v1/session/token",
        json={"user_id": "windows-device", "room_name": "iot-control-room"},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["ws_url"], payload["token"]


async def publish_audio_session(capture: ContinuousCapture) -> None:
    ws_url, token = await asyncio.to_thread(fetch_session)
    room = rtc.Room()
    source = rtc.AudioSource(SAMPLE_RATE, CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track("agent-mic", source)
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    try:
        await room.connect(ws_url, token)
        await room.local_participant.publish_track(track, options)

        # Drain after ICE/DTLS and publication. This contains command words
        # spoken while the connection was being established.
        buffered_frames = capture.begin_live_delivery()
        for frame_bytes in buffered_frames:
            await source.capture_frame(frame_from_pcm(frame_bytes))
        print(f"Flushed {len(buffered_frames)} frames ({len(buffered_frames) * 20}ms).")

        while not capture.stop_event.is_set():
            try:
                frame_bytes = await asyncio.to_thread(capture.live_frames.get, True, 0.5)
            except queue.Empty:
                continue
            await source.capture_frame(frame_from_pcm(frame_bytes))
    finally:
        capture.reset_to_sleeping()
        await room.disconnect()


async def main() -> None:
    capture = ContinuousCapture()
    capture.start()
    try:
        while not capture.stop_event.is_set():
            await asyncio.to_thread(capture.wake_event.wait)
            if capture.stop_event.is_set():
                break
            try:
                await publish_audio_session(capture)
            except Exception as error:
                print(f"Voice session failed: {error}")
                capture.reset_to_sleeping()
            print("Returning to local wake-word detection.")
    finally:
        capture.close()


if __name__ == "__main__":
    asyncio.run(main())
