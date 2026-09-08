# IoT Voice Agent & LiveKit Integration Guide

This guide details the real-time IoT Voice Agent architecture, connecting mobile/desktop client microphones to an AI agent via LiveKit WebRTC, executing MQTT device commands, and returning high-fidelity Rime TTS audio.

---

## Table of Contents

1. [Architecture & Component Breakdown](#1-architecture--component-breakdown)
2. [End-to-End Voice Flow](#2-end-to-end-voice-flow)
3. [MQTT Device Telemetry & Command Protocol](#3-mqtt-device-telemetry--command-protocol)
4. [FastAPI Gateway & Token Provisioning](#4-fastapi-gateway--token-provisioning)
5. [LiveKit Voice Agent Worker (`agent.py`)](#5-livekit-voice-agent-worker-agentpy)
6. [Cross-Platform Client Implementations](#6-cross-platform-client-implementations)
   - [Android (Kotlin)](#61-android-kotlin)
   - [iOS (Swift)](#62-ios-swift)
   - [Windows (Python / PyAudio)](#63-windows-python--pyaudio)
7. [Production Hardening & Scalability](#7-production-hardening--scalability)

---

## 1. Architecture & Component Breakdown

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                    Edge Clients                             │
  │     [Android]             [iOS]             [Windows]       │
  │  (Porcupine Wake)    (Porcupine Wake)    (openWakeWord)     │
  └───────────────┬───────────────────┬───────────────────┬─────┘
                  │ 1. Request JWT    │                   │
                  ▼                   ▼                   ▼
           ┌─────────────────────────────────────────────────┐
           │        FastAPI Gateway (:8000)                  │
           │  • POST /api/v1/session/token                   │
           │  • POST /api/v1/devices                         │
           └─────────────────┬───────────────────────────────┘
                             │ Returns WebRTC room credentials
                             ▼
           ┌─────────────────────────────────────────────────┐
           │        LiveKit Media Server (:7880)             │
           │  • WebRTC Audio Track Ingestion                 │
           │  • Low-latency bidirectional media stream       │
           └─────────────────┬───────────────────────────────┘
                             │ Subscribes to audio track
                             ▼
           ┌─────────────────────────────────────────────────┐
           │        LiveKit Voice Agent (`agent.py`)         │
           │  • Silero VAD (Voice Activity Detection)        │
           │  • Deepgram STT (Speech-to-Text)                │
           │  • OpenAI LLM (Function Tool Calling)           │
           │  • Rime TTS (Spoken voice synthesis)            │
           └─────────────────┬───────────────────────────────┘
                             │ Publishes commands & receives telemetry
                             ▼
           ┌─────────────────────────────────────────────────┐
           │            EMQX MQTT Broker (:1883)             │
           │  • home/devices/+/set                           │
           │  • home/devices/+/telemetry                     │
           └─────────────────┬───────────────────────────────┘
                             │
                             ▼
                    [Smart Home IoT Devices]
```

---

## 2. End-to-End Voice Flow

1. **Local Wake Detection**: Client runs local wake engine (`"Hey Jarvis"` or `"Porcupine"`) while idle. No audio leaves device.
2. **Pre-roll Preservation**: 1.5 seconds of PCM audio prior to wake trigger is preserved in a circular ring buffer.
3. **Session Handshake**: Client requests a token from FastAPI (`POST /api/v1/session/token`), connects to LiveKit Room, and attaches local mic track.
4. **Buffered Audio Flush**: Ring buffer audio is flushed into the LiveKit audio track so the initial user utterance is never clipped.
5. **Speech Processing**:
   - **Silero VAD** identifies voice chunks.
   - **Deepgram** streams transcription into LLM context.
   - **OpenAI LLM** detects tool invocation (`set_device_state` or `get_device_status`).
6. **Action Dispatch**: The agent publishes an MQTT packet to the broker.
7. **Spoken Response**: Rime TTS synthesizes natural speech which is streamed back across the LiveKit room to the client speaker.

---

## 3. MQTT Device Telemetry & Command Protocol

### 3.1 Device Command Topic: `home/devices/{device_id}/set`
Published by the voice agent when user requests a device change.

**Payload Format:**
```json
{
  "state": "on | off | set_level | set_temperature",
  "value": 72
}
```

*Examples:*
- Turning off hallway lights:
  ```json
  {"state": "off"}
  ```
- Setting AC temperature:
  ```json
  {"state": "set_temperature", "value": 72}
  ```

### 3.2 Device Telemetry Topic: `home/devices/{device_id}/telemetry`
Published by physical IoT devices / smart hub; cached in-memory by `agent.py`.

**Payload Format:**
```json
{
  "state": "on",
  "temperature_c": 21.8,
  "humidity": 45,
  "battery": 98
}
```

---

## 4. FastAPI Gateway & Token Provisioning

Implemented in [server.py](file:///c:/Users/ry729/arc-task-gen/server.py).

### Token Request Example
```bash
curl -X POST http://localhost:8000/api/v1/session/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "technician_1", "room_name": "hub-north"}'
```

The gateway signs a JWT with `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET`, granting:
- `room_join: true`
- `can_publish: true` (microphone)
- `can_subscribe: true` (agent voice)

---

## 5. LiveKit Voice Agent Worker (`agent.py`)

The agent worker runs as an autonomous LiveKit worker process:

```bash
# Run agent locally
python agent.py start

# Run with dev reload
python agent.py dev
```

### AI Callable Functions:
- `set_device_state(device_id: str, state: str, value: int = 0) -> str`
- `get_device_status(device_id: str) -> str`

---

## 6. Cross-Platform Client Implementations

### 6.1 Android (Kotlin)
- **Directory**: `clients/android/`
- **Key Files**:
  - `PcmRingBuffer.kt`: Thread-safe pre-roll circular buffer.
  - `MainActivity.kt`: UI and room coordination.
- **Wake-Word**: Picovoice Porcupine.
- **Network**: Connects to host via `http://10.0.2.2:8000` (Android Emulator) or host LAN IP.

### 6.2 iOS (Swift)
- **Directory**: `clients/ios/`
- **Key Files**:
  - `PcmRingBuffer.swift`: Swift implementation of circular byte buffer.
  - `VoiceOrchestrator.swift`: Manages `AVAudioSession` ownership handoff with a 75ms release window to avoid audio engine collision.

### 6.3 Windows (Python / PyAudio)
- **File**: `clients/windows/client_windows.py`
- **Audio Capture**: PyAudio with WASAPI driver support at 16 kHz mono.
- **Wake Engine**: openWakeWord ONNX model.

---

## 7. Production Hardening & Scalability

1. **Persistent Device Registry**: Connect FastAPI `POST /api/v1/devices` to PostgreSQL (`devices` table in `db/schema.sql`).
2. **TLS / Mutual Auth**: Enable TLS on LiveKit (`wss://`) and EMQX (`8883` with client certificates).
3. **Audio Object Storage**: Store audio briefings and session logs in S3/R2 with short-lived presigned URLs.
