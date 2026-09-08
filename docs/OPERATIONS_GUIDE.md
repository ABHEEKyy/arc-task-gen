# Voice Bridge & IoT Assistant Operations Guide

This operational guide details how to launch, operate, monitor, maintain, and troubleshoot every component of the Voice Bridge ecosystem: the Web Incident Handoff app, the Dockerized IoT Voice backend, and the Windows Voice Assistants.

---

## Table of Contents

1. [Environment & Prerequisites](#1-environment--prerequisites)
2. [Operating the Web Incident Handoff System](#2-operating-the-web-incident-handoff-system)
3. [Operating the IoT Voice Stack (Docker Compose)](#3-operating-the-iot-voice-stack-docker-compose)
4. [Operating Windows Desktop Voice Assistants](#4-operating-windows-desktop-voice-assistants)
5. [Database Operations & Migrations](#5-database-operations--migrations)
6. [MQTT Device Telemetry & Command Operations](#6-mqtt-device-telemetry--command-operations)
7. [Health Checks & System Observability](#7-health-checks--system-observability)
8. [Troubleshooting & Runbook](#8-troubleshooting--runbook)

---

## 1. Environment & Prerequisites

### Required Software
- **Node.js**: v18.0+ or v20.0+ (`node -v`, `npm -v`)
- **Python**: v3.10+ or v3.11+ (recommended for LiveKit and audio libraries)
- **Docker & Docker Compose**: v2.20+ (for full IoT infrastructure)
- **Audio I/O**: Functional microphone and speaker/headset (16 kHz / 24 kHz support)
- **Windows (for desktop voice tools)**: Windows 10/11 with PowerShell 5.1+

### API Key Requirements

| Service | Environment Key | Required For | Free Tier / Pricing |
| :--- | :--- | :--- | :--- |
| **Rime Labs** | `RIME_API_KEY` | High-quality streaming neural TTS | Paid / Developer trial |
| **OpenAI** | `OPENAI_API_KEY` | Intent extraction, tool calling & LLM reasoning | Pay-as-you-go |
| **Deepgram** | `DEEPGRAM_API_KEY` | Streaming STT in LiveKit voice agent (`agent.py`) | Free tier available |
| **LiveKit Cloud / Local** | `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | WebRTC room coordination (local dev uses `devkey`/`secret`) | Open-source local / Cloud |

Copy template configuration:
```bash
# Windows PowerShell / CMD
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

---

## 2. Operating the Web Incident Handoff System

The Web Incident Handoff system provides an operator UI for unstructured speech capture, deterministic entity extraction, and instant Rime TTS spoken debriefs.

### 2.1 Starting in Development Mode
```bash
npm install
npm run dev
```
`npm run dev` concurrently boots:
1. **Vite dev server**: Frontend on `http://localhost:5173`
2. **Express API server**: Backend on `http://localhost:8787` (`server.mjs`)

### 2.2 Production Build & Serving
```bash
# Build TypeScript and Vite bundle
npm run build

# Run the production Express server
npm run start
```

### 2.3 Verification & Flow Testing
1. Navigate to `http://localhost:5173`.
2. Ensure browser microphone permissions are granted when prompted.
3. Click **Tap to speak** and dictate an operational report:
   > *"Substation 4 transformer oil temperature spiked above 95 degrees Celsius. Marcus is currently on site monitoring telemetry. Needs immediate technician dispatch."*
4. Stop recording. Within 5–10 seconds, verify:
   - Extracted fields appear:
     - **Location**: `Substation 4`
     - **Issue**: `transformer oil temperature spiked above 95 degrees`
     - **Owner**: `Marcus`
     - **Urgency**: `critical` / `high`
     - **Next move**: `technician dispatch`
   - Spoken audio plays back automatically through Rime TTS.
5. If running headless or without a microphone, click **Use a sample report** to execute the end-to-end extraction and audio transport pipeline.

---

## 3. Operating the IoT Voice Stack (Docker Compose)

The IoT stack manages real-time WebRTC audio rooms, speech-to-text, LLM agent tool dispatch, and MQTT smart device control.

### 3.1 Service Inventory

| Container Name | Service | Default Port(s) | Description |
| :--- | :--- | :--- | :--- |
| `voice-bridge-emqx-1` | **EMQX** | `1883` (MQTT), `18083` (Dashboard) | Distributed MQTT 5.0 broker |
| `voice-bridge-redis-1` | **Redis** | `6379` | State cache and coordination |
| `voice-bridge-postgres-1` | **PostgreSQL** | `5432` | Relational storage for incidents & devices |
| `voice-bridge-livekit-1` | **LiveKit Server** | `7880` (HTTP/WS), `7881` (RTC), `7882/udp` | Real-time WebRTC media server |
| `voice-bridge-api-1` | **FastAPI Gateway** | `8000` | Room token dispenser & device registry |
| `voice-bridge-voice-agent-1` | **Voice Agent** | N/A (Worker) | Python LiveKit worker with Silero VAD & tools |

### 3.2 Starting the Stack
```bash
# Start all services with rebuild
docker compose up --build -d

# Check status of running containers
docker compose ps
```

### 3.3 Viewing Service Logs
```bash
# Tail all container logs
docker compose logs -f

# Tail specific services
docker compose logs -f voice-agent
docker compose logs -f api
docker compose logs -f emqx
```

### 3.4 Stopping and Cleaning Up
```bash
# Stop containers without removing persistent data
docker compose stop

# Tear down containers and networks
docker compose down

# Tear down including database volumes (CAUTION: wipes PostgreSQL data)
docker compose down -v
```

---

## 4. Operating Windows Desktop Voice Assistants

The repository includes two Windows voice modes under `clients/windows/`:
1. **`alexa_backend.py`**: Ambient conversational assistant with multi-turn memory, barge-in, Rime streaming WebSocket audio, web search, and weather.
2. **`windows_voice_controller.py`**: Direct desktop tool executor (app launcher, volume, window manager, keyboard macros).

### 4.1 Dependency Setup
```powershell
py -m pip install -r clients/windows/requirements.txt
```

### 4.2 Running the Ambient Conversational Assistant
```powershell
py clients/windows/alexa_backend.py
```
- **Wake Word**: Speak **"Hey Jarvis"**.
- **Chime**: A double-beep confirms detection.
- **Follow-up Latch**: The assistant listens for follow-up utterances for 6 seconds without needing the wake word.
- **Barge-in**: Say **"Hey Jarvis"** at any point during Rime audio playback to immediately interrupt, truncate speech, and start a new request.
- **PyAutoGUI Failsafe**: Slam the mouse cursor into any corner of the screen to abort simulated keyboard/mouse actions immediately.

### 4.3 Running the Tool Controller
```powershell
py clients/windows/windows_voice_controller.py
```
Supports direct actions such as:
- *"Hey Jarvis, launch calculator"*
- *"Hey Jarvis, volume up"* / *"Hey Jarvis, mute"*
- *"Hey Jarvis, minimize window"*
- *"Hey Jarvis, type Hello World"*

### 4.4 Automated Windows Startup Task

To automatically start `alexa_backend.py` in the background whenever you log into Windows:
```powershell
# Open PowerShell as Administrator
.\clients\windows\install_startup.ps1
```

#### Managing the Scheduled Task:
```powershell
# Start task manually
Start-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant"

# Check status
Get-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant"

# Stop task
Stop-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant"

# Remove task
Unregister-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant" -Confirm:$false
```

---

## 5. Database Operations & Migrations

The PostgreSQL container automatically initializes schema and tables on first boot using [db/schema.sql](file:///c:/Users/ry729/arc-task-gen/db/schema.sql).

### 5.1 Connecting to PostgreSQL
```bash
# Connect via Docker exec
docker compose exec postgres psql -U postgres -d iot_voice

# Or using local psql client
psql "postgresql://postgres:securepassword@localhost:5432/iot_voice"
```

### 5.2 Useful Operational Queries
```sql
-- Check latest reported incidents
SELECT id, issue, location, owner, urgency, status, created_at 
FROM incidents 
ORDER BY created_at DESC 
LIMIT 10;

-- List registered smart devices
SELECT id, name, device_type, mqtt_topic, current_state, updated_at 
FROM devices;

-- Inspect incidents by urgency
SELECT urgency, count(*) 
FROM incidents 
GROUP BY urgency;
```

---

## 6. MQTT Device Telemetry & Command Operations

The voice agent connects to the EMQX broker at `localhost:1883` and listens to device state changes.

### 6.1 EMQX Web Dashboard
- **URL**: `http://localhost:18083`
- **Default Username**: `admin`
- **Default Password**: `public` (Prompted to change on first login)

### 6.2 Testing Device Telemetry via CLI
You can simulate an IoT device publishing telemetry:
```bash
# Using mosquitto_pub or docker exec
docker compose exec emqx emqx_ctl clients list

# Publish test telemetry for living room light
docker compose exec emqx mosquitto_pub \
  -t "home/devices/living_room_light/telemetry" \
  -m '{"state": "on", "brightness": 80, "temperature_c": 22.5}'
```

### 6.3 Listening to Agent Commands
Listen to commands published by the agent when you say *"Turn off the living room light"*:
```bash
docker compose exec emqx mosquitto_sub -t "home/devices/+/set" -v
```

---

## 7. Health Checks & System Observability

### 7.1 Web Prototype API Health
```bash
curl -s http://localhost:8787/api/health | jq
```
Expected output:
```json
{
  "ok": true,
  "service": "voice-bridge"
}
```

### 7.2 FastAPI IoT Gateway Health
```bash
curl -s http://localhost:8000/health | jq
```
Expected output:
```json
{
  "ok": true,
  "service": "voice-iot-gateway"
}
```

### 7.3 Generating LiveKit Room Token
```bash
curl -X POST http://localhost:8000/api/v1/session/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "operator_01", "room_name": "operations-hub"}' | jq
```
Expected output:
```json
{
  "token": "eyJhbGciOi...",
  "ws_url": "ws://localhost:7880"
}
```

---

## 8. Troubleshooting & Runbook

### Issue 1: `PyAudio` / PortAudio cannot find audio input device
- **Symptoms**: `pyaudio.PyAudio().open(...)` raises `OSError: [Errno -9996] Invalid input device`.
- **Cause**: Windows default recording device disabled or microphone permissions blocked.
- **Fix**:
  1. Open Windows **Settings > Privacy & security > Microphone** and ensure **Let apps access your microphone** is **On**.
  2. Verify your default input device in **Control Panel > Sound > Recording**.
  3. Run a quick audio device diagnostic:
     ```python
     import sounddevice as sd
     print(sd.query_devices())
     ```

### Issue 2: LiveKit connection refused (`ECONNREFUSED` or timeout)
- **Symptoms**: `client_windows.py` fails during room connection to `ws://localhost:7880`.
- **Cause**: LiveKit container not started or port `7880` blocked.
- **Fix**:
  1. Check Docker logs: `docker compose logs livekit`.
  2. Ensure LiveKit dev server is running with `--dev` flag.
  3. Verify local port binding: `netstat -ano | findstr 7880`.

### Issue 3: Rime TTS 401 Unauthorized or WebSocket connection drops
- **Symptoms**: `POST /api/speak` fails with `401` or `Rime TTS error: invalid API key`.
- **Cause**: Missing or expired `RIME_API_KEY` in `.env`.
- **Fix**:
  1. Ensure `.env` contains a valid key: `RIME_API_KEY=your_key_here`.
  2. Restart Node server (`npm run dev`) or Python assistant to reload the environment.
  3. Verify Rime WebSocket connectivity using curl or wscat:
     ```bash
     wscat -c "wss://users-ws.rime.ai/ws3?speaker=celeste&modelId=mistv3" -H "Authorization: Bearer YOUR_KEY"
     ```

### Issue 4: PyAutoGUI Failsafe Triggered
- **Symptoms**: Assistant terminates with `pyautogui.FailSafeException`.
- **Cause**: The mouse cursor was moved to the very top-left corner `(0, 0)`.
- **Fix**: This is an intentional safety mechanism preventing erratic mouse movements. Avoid bumping the mouse into screen corners during automated execution.
