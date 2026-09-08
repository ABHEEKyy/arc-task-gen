"""Dependency-free thread-safe PCM pre-roll buffer."""

import threading
from collections import deque


class AudioRingBuffer:
    """Fixed-size PCM buffer with atomic drain at the WebRTC handoff."""

    def __init__(self, max_frames: int) -> None:
        self._frames: deque[bytes] = deque(maxlen=max_frames)
        self._lock = threading.Lock()
        self._streaming = False

    def append(self, frame: bytes) -> bool:
        with self._lock:
            self._frames.append(frame)
            return self._streaming

    def begin_stream(self) -> list[bytes]:
        """Drain all pre-roll and switch subsequent appends to live delivery."""
        with self._lock:
            frames = list(self._frames)
            self._frames.clear()
            self._streaming = True
            return frames

    def drain(self) -> list[bytes]:
        """Atomically return buffered frames without changing stream state."""
        with self._lock:
            frames = list(self._frames)
            self._frames.clear()
            return frames

    def stop_stream(self) -> None:
        with self._lock:
            self._streaming = False
            self._frames.clear()
