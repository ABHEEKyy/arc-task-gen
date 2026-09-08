# Voice Bridge & Ambient IoT Voice Platform

[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?logo=vite)](https://vitejs.dev/)
[![LiveKit](https://img.shields.io/badge/LiveKit-WebRTC-success)](https://livekit.io/)
[![Rime](https://img.shields.io/badge/Rime-Neural_TTS-orange)](https://rime.ai/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)

**Voice Bridge** is an enterprise-grade, voice-native platform spanning two synchronized domains:
1. **Operational Incident Handoff System**: Ingests unstructured spoken frontline reports, extracts deterministic incident metadata (location, issue, owner, urgency, next action), and returns crisp, synthesized operational briefs spoken aloud via **Rime Neural TTS**.
2. **Ambient IoT Voice Agent & Desktop Controller ("Hey Jarvis")**: An always-listening, zero-loss wake-word assistant backed by **LiveKit WebRTC**, **openWakeWord**, **Silero VAD**, **Deepgram STT**, **OpenAI LLM**, and **MQTT 5.0**, controlling physical smart devices and native Windows OS functions with barge-in support and live web tools.

---

## 📑 Table of Contents

- [System Architecture](#-system-architecture)
- [Repository Structure](#-repository-structure)
- [Comprehensive Documentation Suite](#-comprehensive-documentation-suite)
- [Quick Start](#-quick-start)
  - [1. Web Incident Handoff Prototype](#1-web-incident-handoff-prototype)
  - [2. Windows Ambient Voice Assistant ("Hey Jarvis")](#2-windows-ambient-voice-assistant-hey-jarvis)
  - [3. Full IoT Infrastructure (Docker Compose)](#3-full-iot-infrastructure-docker-compose)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [API & Service Contract](#-api--service-contract)
- [Windows Voice Assistant Capabilities](#-windows-voice-assistant-capabilities)
- [Client Integration & SDKs](#-client-integration--sdks)
- [Verification & Testing](#-verification--testing)
- [Security & Production Hardening](#-security--production-hardening)

---

## 🏛 System Architecture

```text
                               ┌─────────────────────────────┐
                               │     Operator Frontline      │
                               │  (Browser Speech / Mobile)  │
                               └──────────────┬──────────────┘
                                              │ Unstructured Speech
                                              ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   VOICE BRIDGE PLATFORM                                │
 │                                                                                        │
 │  ┌───────────────────────┐         ┌───────────────────────┐         ┌──────────────┐  │
 │  │   Vite + TypeScript   │ ◄─────► │   Express API Proxy   │ ◄─────► │   Rime TTS   │  │
 │  │   Operator Dashboard  │         │     (server.mjs)      │         │ (Spoken Handoff)│
 │  └───────────────────────┘         └───────────┬───────────┘         └──────────────┘  │
 │                                                │                                       │
 │                                                ▼                                       │
 │                                     ┌───────────────────────┐                          │
 │                                     │  data/incidents.json  │                          │
 │                                     │ (or PostgreSQL DB)    │                          │
 │                                     └───────────────────────┘                          │
 └────────────────────────────────────────────────────────────────────────────────────────┘

 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                           AMBIENT IOT & DESKTOP VOICE AGENT                            │
 │                                                                                        │
 │  ┌───────────────────────┐         ┌───────────────────────┐         ┌──────────────┐  │
 │  │ Native Clients        │         │   FastAPI Gateway     │         │   LiveKit    │  │
 │  │ • Windows Controller  │ ◄─────► │     (server.py)       │ ◄─────► │ Media Server │  │
 │  │ • iOS / Android App   │         │ (Token Dispenser/Dev) │         │   (WebRTC)   │  │
 │  └───────────┬───────────┘         └───────────────────────┘         └───────┬──────┘  │
 │              │                                                               │         │
 │              │ 1.5s Circular PCM Pre-Roll                                    ▼         │
 │              ▼                                                       ┌──────────────┐  │
 │  ┌───────────────────────┐                                           │ Voice Agent  │  │
 │  │ openWakeWord Engine   │                                           │  (agent.py)  │  │
 │  │  ("Hey Jarvis")       │                                           └───────┬──────┘  │
 │  └───────────────────────┘                                                   │         │
 │              │                                                               │         │
 │              ▼                                                               ▼         │
 │  ┌───────────────────────┐         ┌───────────────────────┐         ┌──────────────┐  │
 │  │ Win Tools Automation  │         │   EMQX MQTT Broker    │ ◄─────► │ Smart Home   │  │
 │  │ • Apps / Volume / Win │         │  home/devices/+/set   │         │ IoT Hardware │  │
 │  │ • Web Search / Weather│         │  home/devices/+/telem │         │  (Sensors)   │  │
 │  └───────────────────────┘         └───────────────────────┘         └──────────────┘  │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Repository Structure

```text
arc-task-gen/
├── .env.example                     # Environment configuration template
├── Dockerfile                       # Container image definition for Python services
├── docker-compose.yml               # Multi-service stack (EMQX, Redis, Postgres, LiveKit)
├── package.json                     # Node.js dependencies & run scripts
├── requirements.txt                 # Backend Python dependencies
├── server.mjs                       # Express proxy & incident persistence server
├── server.py                        # FastAPI LiveKit token dispenser & device registry
├── agent.py                         # LiveKit multimodal voice agent with MQTT tools
├── index.html                       # Operator web interface entry point
├── src/                             # Web application TypeScript source
│   ├── main.ts                      # Audio capture, local extraction & UI orchestration
│   ├── style.css                    # Modern reactive stylesheet
│   └── types.ts                     # Incident and payload type definitions
├── clients/                         # Native client implementations
│   ├── android/                     # Android Studio project (Porcupine + LiveKit Kotlin)
│   ├── ios/                         # iOS Swift package (AVAudioSession handoff + LiveKit)
│   └── windows/                     # Windows desktop voice assistant & automation suite
│       ├── alexa_backend.py         # Conversational assistant (barge-in, Rime WS, web tools)
│       ├── windows_voice_controller.py # Direct tool-calling voice executor
│       ├── client_windows.py        # LiveKit WebRTC client with continuous pre-roll buffer
│       ├── audio_buffer.py          # Atomic thread-safe PCM ring buffer
│       ├── win_tools.py             # OS automation (apps, volume, windows, keyboard)
│       ├── web_tools.py             # Real-time search (DuckDuckGo) & weather (Open-Meteo)
│       ├── local_jarvis_tts.py      # Offline Coqui XTTS v2 voice cloning engine
│       ├── install_startup.ps1      # Automated Windows Task Scheduler installer
│       ├── test_preroll.py          # Ring buffer unit tests
│       └── requirements.txt         # Windows client Python dependencies
├── db/
│   └── schema.sql                   # PostgreSQL schema for incidents, users, rooms, devices
├── data/
│   └── incidents.json               # Zero-dependency local JSON data store
└── docs/                            # Deep architectural & operational documentation
    ├── OPERATIONS_GUIDE.md          # Comprehensive runbook, monitoring & operations manual
    ├── API_REFERENCE.md             # Full endpoint specs for Express & FastAPI
    ├── DESKTOP_VOICE_ASSISTANT_GUIDE.md # Windows "Hey Jarvis" assistant & OS tool guide
    ├── IOT_VOICE_INTEGRATION_GUIDE.md   # LiveKit WebRTC & MQTT smart home guide
    ├── architecture.md              # Production transition & security boundary
    ├── client-integration.md        # Mobile & desktop SDK integration matrix
    └── wake-word-state-machine.md   # Zero-loss pre-roll state transition specification
```

---

## 📚 Comprehensive Documentation Suite

| Guide | Target Audience | Summary |
| :--- | :--- | :--- |
| 🏛 [System Architecture](docs/SYSTEM_ARCHITECTURE.md) | Architects & System Engineers | End-to-end component topology, dataflows & state machines |
| 📂 [Repository Structure](docs/REPOSITORY_STRUCTURE.md) | All Developers | Comprehensive walkthrough of every file and directory |
| 🚀 [Getting Started Guide](docs/GETTING_STARTED.md) | New Users & Developers | Step-by-step installation, running tracks & FAQs |
| 📖 [Operations Guide](docs/OPERATIONS_GUIDE.md) | DevOps / SRE / Operators | Runbooks, deployment, container lifecycle, monitoring, troubleshooting |
| 🔌 [API Reference](docs/API_REFERENCE.md) | Frontend & Backend Engineers | Full request/response schemas, curl examples, error codes |
| 🖥 [Desktop Assistant Guide](docs/DESKTOP_VOICE_ASSISTANT_GUIDE.md) | Desktop Users & Developers | Windows controller, wake-word gating, barge-in, web tools |
| 📡 [IoT Voice Integration Guide](docs/IOT_VOICE_INTEGRATION_GUIDE.md) | Systems & IoT Engineers | LiveKit WebRTC audio pipeline, MQTT topics, mobile clients |
| 📜 [Terms & Conditions](TERMS_AND_CONDITIONS.md) | Legal, Compliance & Users | Audio privacy, acceptable use, AI disclaimers, liability |
| 🔒 [Security Policy](SECURITY.md) | Security Researchers & Teams | Vulnerability disclosure, threat model, credential hygiene |
| 🤝 [Contributing Guidelines](CONTRIBUTING.md) | Open Source Contributors | Branching conventions, code styles, testing checklists |
| 🏗 [Architecture Map](docs/architecture.md) | Architects | System contracts, storage boundaries, database scaling |
| 📱 [Client Integration](docs/client-integration.md) | Mobile Developers | Android Studio & iOS Swift SDK setup |
| ⏱ [Wake-Word State Machine](docs/wake-word-state-machine.md) | Audio Engineers | Atomic pre-roll buffer lifecycle & zero audio clipping |

---

## 🚀 Quick Start

### 1. Web Incident Handoff Prototype

The Web Incident Handoff system runs locally using Node.js and the Express backend:

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
copy .env.example .env
# Open .env and insert your RIME_API_KEY

# 3. Start development server (Vite + Express)
npm run dev
```

- Open `http://localhost:5173` in your browser.
- Click **Tap to speak** and dictate an operational issue:
  > *"Substation 4 transformer oil temperature spiked above 95 degrees. Marcus on site monitoring telemetry. Needs technician dispatch."*
- Click **Stop recording**. In <10 seconds, the structured incident is displayed and Rime plays the spoken brief aloud.

---

### 2. Windows Ambient Voice Assistant ("Hey Jarvis")

For a hands-free desktop voice assistant with multi-turn memory, barge-in, streaming Rime audio, live web search, and OS automation:

```powershell
# 1. Install Windows client requirements
py -m pip install -r clients/windows/requirements.txt

# 2. Ensure OPENAI_API_KEY and RIME_API_KEY are configured in .env
# 3. Launch conversational assistant
py clients/windows/alexa_backend.py
```

- **Say:** *"Hey Jarvis"* $\rightarrow$ wait for the double chime $\rightarrow$ ask any question or command.
- **Example:** *"Hey Jarvis, what's the weather in Tokyo?"*
- **Example:** *"Hey Jarvis, launch calculator and turn the volume down."*
- **Auto-Startup**: Run `.\clients\windows\install_startup.ps1` from an elevated PowerShell to run automatically on Windows sign-in.

---

### 3. Full IoT Infrastructure (Docker Compose)

To spin up the complete distributed cloud/edge backend:

```bash
# 1. Start all services in the background
docker compose up --build -d

# 2. Verify containers are healthy
docker compose ps
```

Services initialized:
- **EMQX Broker**: `localhost:1883` (Dashboard: `http://localhost:18083`)
- **Redis Cache**: `localhost:6379`
- **PostgreSQL**: `localhost:5432` (Auto-initializes `db/schema.sql`)
- **LiveKit Server**: `localhost:7880`
- **FastAPI Gateway**: `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
- **Voice Agent Worker**: Listens to LiveKit rooms and issues MQTT commands

---

## ⚙️ Configuration & Environment Variables

All settings are managed via `.env` in the root directory (see [.env.example](.env.example)):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `RIME_API_KEY` | `""` | **Required**: Rime Labs API key for neural speech synthesis |
| `OPENAI_API_KEY` | `""` | **Required**: OpenAI key for conversational reasoning & tool dispatch |
| `RIME_SPEAKER` | `rex` | Default Rime voice speaker ID (e.g., `rex`, `celeste`) |
| `RIME_MODEL` | `mist` | Rime model identifier (`mist`, `mistv3`) |
| `PORT` | `8787` | Port for Express incident proxy server |
| `LIVEKIT_URL` | `ws://localhost:7880` | LiveKit media server WebSocket URL |
| `LIVEKIT_API_KEY` | `devkey` | LiveKit room authentication key |
| `LIVEKIT_API_SECRET` | `secret` | LiveKit room authentication secret |
| `DEEPGRAM_API_KEY` | `""` | Deepgram API key for LiveKit agent streaming STT |
| `MQTT_HOST` | `localhost` | EMQX MQTT broker hostname |
| `MQTT_PORT` | `1883` | EMQX MQTT broker port |
| `POSTGRES_DSN` | `postgresql://...` | Connection URI for persistent incident & device data |

---

## 📡 API & Service Contract

### Web Incident Handoff API (`:8787`)
- `GET /api/health` — Service readiness probe.
- `GET /api/incidents?status=open&limit=50` — Query logged operational incidents.
- `GET /api/incidents/:id` — Fetch incident details.
- `POST /api/incidents` — Create structured incident from transcript.
- `PATCH /api/incidents/:id/status` — Transition incident status (`open` $\rightarrow$ `acknowledged` $\rightarrow$ `resolved`).
- `POST /api/speak` — Secure server-side Rime TTS speech synthesis.

### IoT Voice Gateway API (`:8000`)
- `GET /health` — Gateway status check.
- `POST /api/v1/session/token` — Dispense signed LiveKit WebRTC tokens.
- `POST /api/v1/devices` — Register smart devices with MQTT topics.

*(See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for full request/response schemas and curl examples.)*

---

## 💻 Windows Voice Assistant Capabilities

The Windows assistant under `clients/windows/` features:

1. **Zero-Loss Audio Pre-Roll**: An atomic 1.5-second rolling PCM buffer ensures the initial syllable of your voice command is never lost during wake-word trigger.
2. **Streaming WebSocket Audio**: Audio tokens from Rime stream directly to your speakers in real-time, eliminating conversational delay.
3. **Barge-In Interruptibility**: Speaking *"Hey Jarvis"* while the assistant is talking cuts the audio output instantly and queues the new command.
4. **Follow-Up Latching**: Remains active for 6 seconds after speaking; answer follow-up queries without repeating the wake phrase.
5. **Tool Calling & Automation**:
   - **Apps**: Launch calculator, notepad, paint, file explorer, or whitelisted web URLs.
   - **System Volume**: Master volume up, down, or mute via Windows Core Audio.
   - **Window Controls**: Minimize, maximize, or close active windows.
   - **Web Tools**: Live DuckDuckGo search summaries and Open-Meteo current city weather (no API keys required).
6. **Safety Failsafe**: Built-in PyAutoGUI failsafe—slam the cursor into any screen corner to immediately abort active automation.

---

## 🧪 Verification & Testing

### Test 1: Pre-roll Buffer Unit Tests
Verify thread safety, atomic draining, and live marking of the circular audio buffer:
```powershell
py clients/windows/test_preroll.py
# Output: Pre-roll tests passed.
```

### Test 2: Service Health Checks
```bash
# Check Web API
curl http://localhost:8787/api/health

# Check FastAPI Gateway
curl http://localhost:8000/health
```

### Test 3: Audio Device Verification
Check detected microphone and playback devices:
```powershell
py -c "import sounddevice as sd; print(sd.query_devices())"
```

---

## 🔒 Security & Production Hardening

- **API Key Isolation**: `RIME_API_KEY`, `OPENAI_API_KEY`, and `DEEPGRAM_API_KEY` are strictly server-side; they are never sent to web clients.
- **Database Transition**: Move from `data/incidents.json` to PostgreSQL by running `db/schema.sql` against production clusters.
- **Audio Lifecycle**: In production, configure TTS endpoints to persist audio buffers into S3/Cloudflare R2 and return time-limited presigned URLs.
- **Local Gating**: The local wake detector sleeps entirely on-device; idle ambient room audio is never streamed to third-party cloud services.
