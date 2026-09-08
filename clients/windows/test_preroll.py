"""Dependency-free tests for the Windows pre-roll handoff."""

import threading

from audio_buffer import AudioRingBuffer


def test_ring_buffer_keeps_latest_frames() -> None:
    ring = AudioRingBuffer(max_frames=3)
    ring.append(b"one")
    ring.append(b"two")
    ring.append(b"three")
    ring.append(b"four")
    assert ring.begin_stream() == [b"two", b"three", b"four"]


def test_frames_after_handoff_are_marked_live() -> None:
    ring = AudioRingBuffer(max_frames=3)
    ring.append(b"pre-roll")
    assert ring.begin_stream() == [b"pre-roll"]
    assert ring.append(b"live") is True


def test_drain_preserves_sleeping_state() -> None:
    ring = AudioRingBuffer(max_frames=3)
    ring.append(b"pre-roll")
    assert ring.drain() == [b"pre-roll"]
    assert ring.append(b"still sleeping") is False


def test_handoff_is_safe_with_concurrent_capture() -> None:
    ring = AudioRingBuffer(max_frames=75)
    captured = []
    ready = threading.Event()

    def capture() -> None:
        for index in range(100):
            is_live = ring.append(str(index).encode())
            if is_live:
                captured.append(index)
            if index == 49:
                ready.set()

    thread = threading.Thread(target=capture)
    thread.start()
    ready.wait(timeout=1)
    buffered = ring.begin_stream()
    thread.join()

    assert buffered
    assert len(buffered) <= 75
    assert captured == list(range(captured[0], 100)) if captured else True


if __name__ == "__main__":
    test_ring_buffer_keeps_latest_frames()
    test_frames_after_handoff_are_marked_live()
    test_handoff_is_safe_with_concurrent_capture()
    print("Pre-roll tests passed.")
