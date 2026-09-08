import Foundation

/// Thread-safe 1.5 second PCM pre-roll at 20 ms per frame.
final class PcmRingBuffer {
    private let lock = NSLock()
    private var frames: [Data] = []
    private let maxFrames: Int
    private var streaming = false

    init(maxFrames: Int = 75) {
        self.maxFrames = maxFrames
    }

    /// Returns true when the caller should also forward this frame live.
    @discardableResult
    func append(_ frame: Data) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        if frames.count == maxFrames { frames.removeFirst() }
        frames.append(frame)
        return streaming
    }

    func beginStream() -> [Data] {
        lock.lock()
        defer { lock.unlock() }
        let buffered = frames
        frames.removeAll(keepingCapacity: true)
        streaming = true
        return buffered
    }

    func stopStream() {
        lock.lock()
        defer { lock.unlock() }
        streaming = false
        frames.removeAll(keepingCapacity: true)
    }
}
