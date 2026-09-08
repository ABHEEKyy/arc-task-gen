# Getting Started Guide

A complete, beginner-to-advanced walkthrough for setting up, running, and developing on the **Voice Bridge & Ambient IoT Voice Platform**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Initial Configuration](#2-initial-configuration)
3. [Track 1: Web Incident Handoff App](#3-track-1-web-incident-handoff-app)
4. [Track 2: Windows Ambient Assistant ("Hey Jarvis")](#4-track-2-windows-ambient-assistant-hey-jarvis)
5. [Track 3: Full IoT Backend (Docker Compose)](#5-track-3-full-iot-backend-docker-compose)
6. [Verification & Acceptance Checklist](#6-verification--acceptance-checklist)
7. [FAQ & Common Questions](#7-faq--common-questions)

---

## 1. Prerequisites

Before starting, ensure your workstation meets the following requirements:

### Software & Runtimes
- **Node.js**: `v18.0.0` or newer (`node -v`)
- **Python**: `3.10`, `3.11`, or `3.12` 64-bit (`py --version`)
- **Git**: For source version control
- **Docker Desktop** (Optional, for full IoT stack): Running Linux containers

### Hardware
- Working microphone (USB headset or built-in mic)
- Audio output speakers or headphones
- Recommended: Windows 10/11 for native OS tools

---

## 2. Initial Configuration

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ABHEEKyy/arc-task-gen.git
   cd arc-task-gen
   ```

2. **Create your `.env` configuration**:
   ```bash
   # On Windows (PowerShell / CMD):
   copy .env.example .env

   # On macOS / Linux:
   cp .env.example .env
   ```

3. **Obtain API Keys**:
   Open `.env` in your code editor and populate your keys:
   - **`RIME_API_KEY`**: Obtain from [Rime Labs](https://rime.ai/) for neural voice synthesis.
   - **`OPENAI_API_KEY`**: Obtain from [OpenAI Platform](https://platform.openai.com/) for tool calling and reasoning.
   - **`DEEPGRAM_API_KEY`** (Optional, for LiveKit agent): Obtain from [Deepgram](https://deepgram.com/).

---

## 3. Track 1: Web Incident Handoff App

The Web Incident Handoff application runs locally in seconds with minimal overhead:

### 3.1 Install and Start
```bash
# Install npm dependencies
npm install

# Start Vite frontend and Express server concurrently
npm run dev
```

### 3.2 Testing the Application
1. Open your browser to **`http://localhost:5173`**.
2. Allow microphone permissions when prompted.
3. Click **Tap to speak** and dictate a test incident:
   > *"Substation 4 transformer oil temperature spiked above 95 degrees. Marcus on site monitoring telemetry. Needs technician dispatch."*
4. Click **Stop recording**.
5. The interface will extract:
   - **Location**: `Substation 4`
   - **Issue**: `transformer oil temperature spiked above 95 degrees`
   - **Owner**: `Marcus`
   - **Next move**: `technician dispatch`
6. Rime TTS will vocalize the operational handoff through your speakers.
7. Click **Play spoken handoff** to replay the briefing audio at any time.

---

## 4. Track 2: Windows Ambient Assistant ("Hey Jarvis")

Run an always-listening, zero-loss desktop assistant with OS control and live web search.

### 4.1 Install Python Client Requirements
```powershell
py -m pip install -r clients/windows/requirements.txt
```

### 4.2 Start the Conversational Assistant
```powershell
py clients/windows/alexa_backend.py
```

### 4.3 Conversational Workflow
1. Say clearly: **"Hey Jarvis"**.
2. A double chime sound confirms wake detection.
3. Ask a question or command:
   - *"What's the weather like in Tokyo right now?"*
   - *"Search for the latest technology headlines."*
   - *"Launch calculator and mute the volume."*
4. **Barge-In**: While Jarvis is speaking, say **"Hey Jarvis"** at any time to instantly cut playback and speak a new query.
5. **Follow-Up Latching**: After Jarvis replies, you have 6 seconds to ask a follow-up question without repeating the wake word.

### 4.4 Install as a Startup Service
To have Jarvis start automatically when you log in:
```powershell
# Run PowerShell as Administrator
.\clients\windows\install_startup.ps1
```

---

## 5. Track 3: Full IoT Backend (Docker Compose)

The full IoT backend connects LiveKit WebRTC, an EMQX MQTT broker, Redis, and a PostgreSQL database.

```bash
# Build and launch all background containers
docker compose up --build -d

# Check container status
docker compose ps
```

### Endpoints Available:
- **EMQX Dashboard**: [http://localhost:18083](http://localhost:18083) (User: `admin`, Pass: `public`)
- **FastAPI Gateway**: [http://localhost:8000](http://localhost:8000) (Interactive Swagger docs at `/docs`)
- **LiveKit Server**: `ws://localhost:7880`
- **PostgreSQL**: `localhost:5432` (`iot_voice` database)

---

## 6. Verification & Acceptance Checklist

| Check | Command / Action | Expected Result |
| :--- | :--- | :--- |
| **Express Health** | `curl http://localhost:8787/api/health` | `{"ok": true, "service": "voice-bridge"}` |
| **FastAPI Health** | `curl http://localhost:8000/health` | `{"ok": true, "service": "voice-iot-gateway"}` |
| **Pre-roll Buffer Tests** | `py clients/windows/test_preroll.py` | `Pre-roll tests passed.` |
| **Audio I/O Diagnostic** | `py -c "import sounddevice as sd; print(sd.query_devices())"` | Lists available input/output sound cards |

---

## 7. FAQ & Common Questions

**Q: Do I need an OpenAI API key to test the web frontend?**  
A: No! The web incident frontend uses local deterministic rule extraction. Only `RIME_API_KEY` is required for the voice debrief.

**Q: Does DuckDuckGo or Open-Meteo require an API key?**  
A: No, both the web search and weather lookup tools operate completely key-free.

**Q: How do I abort an unintended Windows voice action?**  
A: Simply push your mouse cursor into any corner of the screen. PyAutoGUI's built-in failsafe will instantly abort execution.
