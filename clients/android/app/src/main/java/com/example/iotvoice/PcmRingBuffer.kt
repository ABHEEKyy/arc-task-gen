package com.example.iotvoice

import java.util.ArrayDeque

/** Thread-safe 1.5 second PCM pre-roll at 20 ms per frame. */
class PcmRingBuffer(
    private val maxFrames: Int = 75,
) {
    private val frames = ArrayDeque<ByteArray>(maxFrames)
    private val lock = Any()
    private var streaming = false

    /** Returns true when the caller should also forward this frame live. */
    fun append(frame: ByteArray): Boolean = synchronized(lock) {
        if (frames.size == maxFrames) frames.removeFirst()
        frames.addLast(frame.copyOf())
        streaming
    }

    fun beginStream(): List<ByteArray> = synchronized(lock) {
        val buffered = frames.toList()
        frames.clear()
        streaming = true
        buffered
    }

    fun stopStream() = synchronized(lock) {
        streaming = false
        frames.clear()
    }
}
