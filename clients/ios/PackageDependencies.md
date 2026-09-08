# iOS dependencies

Add these Swift packages in Xcode:

- `https://github.com/Picovoice/porcupine.git`
- `https://github.com/livekit/client-sdk-swift.git`

Request microphone permission with `NSMicrophoneUsageDescription`. Keep the Picovoice access key in the app's secure configuration; never commit it. The orchestrator intentionally stops Porcupine and yields 75 ms before activating WebRTC's `AVAudioSession`.
