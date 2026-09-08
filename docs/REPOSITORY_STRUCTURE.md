# Repository Structure & Directory Map

An exhaustive architectural reference to every file and folder in the **Voice Bridge & Ambient IoT Voice Platform** repository.

---

## 1. Top-Level Directory Tree

```text
arc-task-gen/
│
├── .env.example                     # Reference environment variables for local & cloud stacks
├── .gitignore                       # Ignored build outputs, credentials, and virtualenvs
├── Dockerfile                       # Python multi-stage container build for API and Agent
├── docker-compose.yml               # Multi-container orchestration (EMQX, Redis, Postgres, LiveKit)
├── package.json                     # Node.js workspace definitions, scripts & Vite config
├── package-lock.json                # Locked Node dependency tree
├── tsconfig.json                    # TypeScript compiler configuration (strict mode)
├── vite.config.ts                   # Vite bundler build settings & dev server proxying
├── requirements.txt                 # Backend Python dependencies (LiveKit, FastAPI, Paho MQTT)
├── index.html                       # Single-page application entry point for incident operator UI
│
├── server.mjs                       # Express proxy & local incident file store (Port 8787)
├── server.py                        # FastAPI LiveKit JWT dispenser & IoT device registry (Port 8000)
├── agent.py                         # LiveKit multimodal voice worker with MQTT smart device tools
│
├── src/                             # Web application TypeScript frontend
│   ├── main.ts                      # Frontend audio capture, extraction heuristics & UI render
│   ├── style.css                    # Responsive layout, cards, animations, and status badges
│   └── types.ts                     # TypeScript interfaces for Incidents, Statuses & Payloads
│
├── data/                            # Persistent local storage
│   └── incidents.json               # Flat JSON document store for prototype incident history
│
├── db/                              # Relational database assets
│   └── schema.sql                   # PostgreSQL schema (incidents, devices, rooms, users)
│
├── clients/                         # Native client implementations across platforms
│   ├── android/                     # Native Android Studio project (Kotlin + Porcupine + LiveKit)
│   ├── ios/                         # iOS Swift implementation (AVAudioSession + LiveKit)
│   └── windows/                     # Windows desktop voice assistant ("Hey Jarvis") & OS tools
│       ├── alexa_backend.py         # Conversational assistant (barge-in, Rime WS, web search)
│       ├── windows_voice_controller.py # Direct tool-calling voice executor
│       ├── client_windows.py        # LiveKit WebRTC client with continuous pre-roll buffer
│       ├── audio_buffer.py          # Atomic thread-safe PCM circular ring buffer
│       ├── win_tools.py             # OS automation (apps, volume, windows, keyboard)
│       ├── web_tools.py             # Real-time search (DuckDuckGo) & weather (Open-Meteo)
│       ├── local_jarvis_tts.py      # Offline Coqui XTTS v2 voice cloning engine
│       ├── install_startup.ps1      # Automated Windows Task Scheduler installer
│       ├── test_preroll.py          # Ring buffer unit tests
│       └── requirements.txt         # Windows client Python dependencies
│
└── docs/                            # In-depth architectural & operational documentation
    ├── SYSTEM_ARCHITECTURE.md       # High-level architecture, component topology & state machines
    ├── REPOSITORY_STRUCTURE.md      # This file - deep dive into code files & purpose
    ├── GETTING_STARTED.md           # Step-by-step setup and quick-start guide
    ├── OPERATIONS_GUIDE.md          # Runbook, monitoring, health checks & troubleshooting
    ├── API_REFERENCE.md             # Full endpoint specs for Express & FastAPI
    ├── DESKTOP_VOICE_ASSISTANT_GUIDE.md # Windows "Hey Jarvis" assistant & OS tool guide
    ├── IOT_VOICE_INTEGRATION_GUIDE.md   # LiveKit WebRTC & MQTT smart home guide
    ├── architecture.md              # Original architectural blueprint & acceptance criteria
    ├── client-integration.md        # Mobile & desktop SDK integration matrix
    └── wake-word-state-machine.md   # Zero-loss pre-roll state transition specification
```

---

## 2. Component-by-Component Analysis

### 2.1 Web Frontend (`index.html`, `src/`)
- **[index.html](file:///c:/Users/ry729/arc-task-gen/index.html)**: Clean HTML5 semantic layout featuring an incident recording panel, live speech status indicator, extracted entity card, and past incident history table.
- **[src/main.ts](file:///c:/Users/ry729/arc-task-gen/src/main.ts)**:
  - Connects to Web Speech API (`SpeechRecognition`).
  - Contains deterministic extraction heuristics: parses freeform speech into `location`, `issue`, `owner`, `urgency`, and `nextStep`.
  - Dispatches `POST /api/incidents` and `POST /api/speak`.
  - Manages audio decoding and HTML5 Audio buffer playback.
- **[src/style.css](file:///c:/Users/ry729/arc-task-gen/src/style.css)**: Modern CSS with CSS custom properties, responsive grid, glassmorphic cards, and pulse recording states.
- **[src/types.ts](file:///c:/Users/ry729/arc-task-gen/src/types.ts)**: Defines `Incident`, `Urgency` (`critical` | `high` | `standard`), and `IncidentStatus` (`open` | `acknowledged` | `resolved`).

---

### 2.2 Server & Backend Gateways
- **[server.mjs](file:///c:/Users/ry729/arc-task-gen/server.mjs)**:
  - Node.js / Express microservice on port `8787`.
  - Serves REST endpoints for incident CRUD.
  - Implements the server-to-server Rime TTS proxy, safeguarding `RIME_API_KEY`.
  - Manages atomic writes to `data/incidents.json`.
- **[server.py](file:///c:/Users/ry729/arc-task-gen/server.py)**:
  - FastAPI asynchronous gateway on port `8000`.
  - Mints LiveKit JWT room access tokens for mobile and desktop clients (`/api/v1/session/token`).
  - Provides IoT device registration endpoint (`/api/v1/devices`).
- **[agent.py](file:///c:/Users/ry729/arc-task-gen/agent.py)**:
  - LiveKit Voice Agent worker process.
  - Connects to EMQX broker on MQTT port `1883`.
  - Listens to device telemetry on `home/devices/+/telemetry`.
  - Registers LLM function call tools: `set_device_state` and `get_device_status`.
  - Bridges Silero VAD, Deepgram STT, and Rime TTS directly into the WebRTC audio room.

---

### 2.3 Desktop Voice Assistant (`clients/windows/`)
- **[alexa_backend.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/alexa_backend.py)**:
  - The primary conversational assistant.
  - Features bounded 12-turn dialogue memory.
  - Connects to Rime WebSocket streaming endpoint (`wss://users-ws.rime.ai/ws3`).
  - Implements real-time barge-in cancellation and 6-second multi-turn follow-up latching.
- **[windows_voice_controller.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/windows_voice_controller.py)**:
  - Direct execution controller for OS macros.
  - Uses PyAudio 16 kHz stream with openWakeWord `hey_jarvis` model.
- **[audio_buffer.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/audio_buffer.py)**:
  - `AudioRingBuffer`: Thread-safe circular deque holding 1.5 seconds of PCM audio frames.
  - Transitions atomically from pre-roll sleep mode to live streaming mode.
- **[win_tools.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/win_tools.py)**:
  - PyAutoGUI and OS wrappers.
  - Controls window states (minimize, maximize, close), master volume, and keyboard shortcuts.
- **[web_tools.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/web_tools.py)**:
  - DuckDuckGo zero-config search (`DDGS`).
  - Open-Meteo REST API geocoding and weather lookup.
- **[install_startup.ps1](file:///c:/Users/ry729/arc-task-gen/clients/windows/install_startup.ps1)**:
  - Automated PowerShell script registering Jarvis as an ambient Windows Scheduled Task at user logon.
- **[test_preroll.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/test_preroll.py)**:
  - Standalone unit test suite validating circular buffer boundaries and concurrent thread safety.

---

### 2.4 Mobile Clients (`clients/android/`, `clients/ios/`)
- **[clients/android/](file:///c:/Users/ry729/arc-task-gen/clients/android)**:
  - Gradle Kotlin project using LiveKit Android SDK.
  - Uses `PcmRingBuffer.kt` to prevent audio dropouts during wake transitions.
- **[clients/ios/](file:///c:/Users/ry729/arc-task-gen/clients/ios)**:
  - Swift package managing `AVAudioSession` ownership transfer.
  - Preserves 75ms release window to avoid collision between Picovoice and LiveKit audio engines.

---

### 2.5 Database & Infrastructure (`db/`, `docker-compose.yml`)
- **[db/schema.sql](file:///c:/Users/ry729/arc-task-gen/db/schema.sql)**:
  - Defines custom PostgreSQL enums: `incident_urgency` and `incident_status`.
  - Tables: `incidents`, `users`, `rooms`, and `devices`.
  - Includes composite indexes on `(status, created_at desc)` and `location`.
- **[docker-compose.yml](file:///c:/Users/ry729/arc-task-gen/docker-compose.yml)**:
  - Coordinates EMQX 5.8, Redis 7, PostgreSQL 16, LiveKit Server, FastAPI, and Voice Agent.
