# Windows Voice Assistant & Desktop Controller Guide

The Windows desktop client provides an ambient, hands-free assistant with local wake-word gating, zero-loss audio buffering, real-time web tools, and deep OS automation.

---

## Table of Contents

1. [Architecture & Audio Pipeline](#1-architecture--audio-pipeline)
2. [Operating Modes: Conversational vs. Direct Controller](#2-operating-modes-conversational-vs-direct-controller)
3. [Function Calling & Automation Tools](#3-function-calling--automation-tools)
4. [Real-Time Web Tools](#4-real-time-web-tools)
5. [Voice Synthesis (Rime Streaming vs. Local XTTS v2)](#5-voice-synthesis-rime-streaming-vs-local-xtts-v2)
6. [Barge-in, Ducking & Conversational Turn-Taking](#6-barge-in-ducking--conversational-turn-taking)
7. [Installation & Windows Startup Service](#7-installation--windows-startup-service)
8. [Safety Failsafes & Security](#8-safety-failsafes--security)

---

## 1. Architecture & Audio Pipeline

Traditional voice assistants suffer from latency during wake-word handoff or cut off the initial syllable spoken by the user. This client solves this with an atomic circular PCM buffer.

```text
[Continuous Mic Input (16kHz PCM)]
                │
                ▼
   ┌───────────────────────────┐
   │ 1.5s Audio Ring Buffer    │ ◄── Always holds the latest 75 frames (20ms each)
   └────────────┬──────────────┘
                │
                ▼
   ┌───────────────────────────┐
   │ openWakeWord ("Hey Jarvis")│
   └────────────┬──────────────┘
                │
       [Wake Word Detected]
                │
   ┌────────────┴───────────────────────────┐
   ▼                                        ▼
Atomic Drain of Pre-Roll Buffer      Trigger local chime (sounddevice)
   │                                        │
   └────────────────────┬───────────────────┘
                        ▼
            [VAD Utterance Collector]
         (Captures speech until 1.2s silence)
                        │
                        ▼
         [OpenAI Tool-Calling Reasoner]
         (Chooses Windows tool or Web search)
                        │
                        ▼
      [Rime Streaming WebSocket Audio (24kHz)]
           (Immediate playback via PCM)
```

---

## 2. Operating Modes: Conversational vs. Direct Controller

### Mode A: Conversational Assistant (`alexa_backend.py`)
- **Recommended for general ambient use.**
- **Features**:
  - Full multi-turn conversational memory (bounded to last 12 turns).
  - Wake-word latch: After Jarvis replies, it remains latched for **6 seconds** to accept follow-up prompts without needing the wake word.
  - Streaming Rime WebSocket: Starts playing sentences before the LLM has even completed generation.
  - Barge-in capability: Wake-word stops TTS playback immediately.
- **Run command**:
  ```powershell
  py clients/windows/alexa_backend.py
  ```

### Mode B: Direct Desktop Voice Controller (`windows_voice_controller.py`)
- **Lightweight, command-oriented mode.**
- **Features**:
  - Dedicated to rapid, low-overhead execution of Windows desktop tasks.
  - Directly maps voice commands to PyAutoGUI and system shortcuts.
- **Run command**:
  ```powershell
  py clients/windows/windows_voice_controller.py
  ```

---

## 3. Function Calling & Automation Tools

The assistant exposes an allowlisted set of OS control functions located in [clients/windows/win_tools.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/win_tools.py):

### 3.1 Application Launching
- **Function**: `launch_application(app_name: str)`
- **Allowlisted applications**:
  - `calculator` / `calc` (`calc.exe`)
  - `notepad` (`notepad.exe`)
  - `paint` (`mspaint.exe`)
  - `explorer` / `file explorer` (`explorer.exe`)
  - Any valid `http://`, `https://`, or `mailto:` URL
- **Sample Voice Commands**:
  - *"Hey Jarvis, launch calculator."*
  - *"Hey Jarvis, open https://github.com."*

### 3.2 System Volume Control
- **Function**: `system_volume(action: str, amount: int = 10)`
- **Actions**: `mute`, `up`, `down`
- **Sample Voice Commands**:
  - *"Hey Jarvis, turn the volume down."*
  - *"Hey Jarvis, mute audio."*

### 3.3 Window Management
- **Function**: `window_management(action: str)`
- **Actions**:
  - `minimize`: Sends `Alt + Space`, then `N`
  - `maximize`: Sends `Alt + Space`, then `X`
  - `close`: Sends `Alt + F4`
- **Sample Voice Commands**:
  - *"Hey Jarvis, minimize this window."*
  - *"Hey Jarvis, close the window."*

### 3.4 Keyboard Shortcuts & Typing
- **Functions**: `keyboard_shortcut(keys: list[str])`, `type_text(text: str)`
- **Supported keys**: `alt`, `ctrl`, `shift`, `win`, `tab`, `enter`, `escape`, `space`, `backspace`, `delete`
- **Safety Limit**: Text input is restricted to a maximum of 500 characters.
- **Sample Voice Commands**:
  - *"Hey Jarvis, press control tab."*
  - *"Hey Jarvis, type Welcome to Voice Bridge."*

---

## 4. Real-Time Web Tools

Defined in [clients/windows/web_tools.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/web_tools.py), these tools require **no API keys**:

### 4.1 Live Web Search
- **Backend**: DuckDuckGo Python client (`ddgs`).
- **Function**: `web_search(query: str)`
- **Output**: Returns top 3 cleaned news/fact snippets (without exposing raw URLs into voice output).
- **Sample Prompts**:
  - *"Hey Jarvis, search for the latest SpaceX launch news."*
  - *"Hey Jarvis, what were the major headlines today?"*

### 4.2 Live Weather Lookups
- **Backend**: Open-Meteo Geocoding + Weather API.
- **Function**: `get_weather(city: str)`
- **Output**: Resolves coordinates, fetches current temperature (°C/°F), wind speed, and WMO weather condition code (e.g., clear sky, rain showers, overcast).
- **Sample Prompts**:
  - *"Hey Jarvis, what's the weather in Tokyo right now?"*
  - *"Hey Jarvis, will it rain today in San Francisco?"*

---

## 5. Voice Synthesis (Rime Streaming vs. Local XTTS v2)

### Option 1: Rime Neural Streaming TTS (Default)
- **Protocol**: WebSocket streaming (`wss://users-ws.rime.ai/ws3`).
- **Voice / Speaker**: `celeste` or `rex` (configured in `.env`).
- **Format**: 24 kHz raw PCM.
- **Latency**: Under 250ms time-to-first-audio chunk.

### Option 2: Local Coqui XTTS v2 Offline Voice Cloning
For air-gapped environments or custom voice personalities (e.g., Paul Bettany / Marvel J.A.R.V.I.S.):
- Implementation: [clients/windows/local_jarvis_tts.py](file:///c:/Users/ry729/arc-task-gen/clients/windows/local_jarvis_tts.py).
- Drop a reference voice file named `jarvis_reference.wav` into the workspace root.
- Uses CUDA GPU acceleration to stream synthesized audio chunks through `sounddevice`.

---

## 6. Barge-in, Ducking & Conversational Turn-Taking

### Wake-Word Barge-In
If Jarvis is reading a lengthy response and you say **"Hey Jarvis"**:
1. The background openWakeWord listener flags a detection event.
2. The active audio playback stream is stopped instantly (`sd.stop()`).
3. Sentences queued for TTS are cleared immediately.
4. The chime plays, and your new query is recorded.

### Multi-turn Follow-Up Latch
```text
[Operator speaks: "What time is it in London?"]
                     │
         [Jarvis replies with London time]
                     │
  ┌──────────────────┴───────────────────┐
  │ Latch Timer: 6.0 seconds             │
  │ Status: LATCHED                      │
  └──────────────────┬───────────────────┘
                     │
   Operator asks: "What about New York?"
  (No "Hey Jarvis" wake word needed)
```

---

## 7. Installation & Windows Startup Service

To automatically launch the assistant whenever you sign in to Windows:

```powershell
# Open PowerShell (Run as Administrator if restricted by UAC)
cd c:\Users\ry729\arc-task-gen
.\clients\windows\install_startup.ps1
```

The script registers a Scheduled Task named **"Jarvis Ambient Voice Assistant"** that:
- Executes at user logon (`-AtLogOn`).
- Sets execution time limit to indefinite (`[TimeSpan]::Zero`).
- Sets working directory to the project repository so `.env` is loaded cleanly.

To stop or remove the task:
```powershell
# Stop running instance
Stop-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant"

# Permanently uninstall task
Unregister-ScheduledTask -TaskName "Jarvis Ambient Voice Assistant" -Confirm:$false
```

---

## 8. Safety Failsafes & Security

1. **PyAutoGUI Failsafe**: Enabled (`pyautogui.FAILSAFE = True`). Slamming your mouse cursor into any corner of the primary display immediately raises `FailSafeException` and halts automated cursor/keyboard events.
2. **Application Whitelist**: The assistant cannot execute arbitrary binaries or shell commands via voice. Only explicit entries in `ALLOWED_APPS` and validated HTTP/HTTPS URLs are allowed.
3. **Character Boundary**: `type_text` rejects any input greater than 500 characters to prevent accidental buffer stuffing.
