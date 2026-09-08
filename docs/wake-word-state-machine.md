# Wake-word state machine

The client keeps the microphone local until a wake word is detected. LiveKit is disconnected while sleeping, so idle audio never leaves the device.

```text
SLEEPING --wake word--> TRIGGERED --room connected--> LISTENING
LISTENING --agent finished, disconnect, timeout, or error--> SLEEPING
```

## Required transitions

- **SLEEPING:** local 16 kHz PCM capture, wake-word model, 1-second rolling pre-roll buffer, LiveKit disconnected.
- **TRIGGERED:** stop the wake-word engine, play a local chime, request a short-lived token, connect LiveKit, and publish the microphone track.
- **LISTENING:** receive the agent's Rime audio track, let backend VAD detect turn completion, and disconnect after completion or inactivity.
- **RESET:** stop the LiveKit mic, disconnect the room, wait for audio resources to release, clear the pre-roll buffer, and restart the local detector.

The pre-roll buffer is deliberately client-local. It can be sent as an initial audio segment only after the LiveKit session is authenticated; it is never uploaded during SLEEPING.

The concrete buffers are implemented in `clients/windows/client_windows.py`, `clients/android/app/src/main/java/com/example/iotvoice/PcmRingBuffer.kt`, and `clients/ios/PcmRingBuffer.swift`. All use a 1.5 second default and make the drain plus streaming transition atomic.

## Zero-loss tuning

- Audio format is 16 kHz, mono, signed 16-bit PCM.
- Capture frames are 320 samples, or 20 ms each.
- The default pre-roll is 75 frames, or 1.5 seconds.
- The wake phrase may be present in the drained audio. The agent prompt ignores leading `Computer` and `Hey Jarvis` trigger words.
- Do not stop and recreate the native microphone during handoff. Android should keep `AudioRecord` alive; iOS should keep its input tap alive while the custom LiveKit source consumes the same PCM frames.
- If a platform's network path regularly exceeds 1.5 seconds, increase the buffer to 2 seconds only after measuring stale-audio and memory impact.

## Security and reliability rules

- Store Picovoice keys in native secure storage or build-time secrets, never in this repository.
- Fetch LiveKit JWTs from `POST /api/v1/session/token` immediately after wake detection.
- Never embed LiveKit API secrets or MQTT credentials in clients.
- Use a timeout and error path that always returns to SLEEPING.
- Keep the local chime independent of the network round trip.
