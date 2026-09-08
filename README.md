# Voice Bridge

Voice Bridge is a voice-native incident handoff prototype. It solves one hard problem: a person can report an operational issue in messy natural language, and the next operator receives a concise, structured brief spoken aloud by Rime.

## Acceptance test

1. Add `RIME_API_KEY` to `.env` using `.env.example` as a guide.
2. Start the app with `npm run dev`.
3. Click **Tap to speak** and say one unstructured report containing a location, issue, person on site, and urgency.
4. Stop recording. Within 10 seconds, the app must show the extracted location, issue, owner, and next move, then play the concise handoff using Rime-generated speech.
5. Click **Play spoken handoff** to replay the Rime audio without rerecording.

The `Use a sample report` path lets you test the orchestration and Rime transport when microphone permissions or browser speech recognition are unavailable.

## Run

```bash
npm install
copy .env.example .env
npm run dev
```

Open `http://localhost:5173`. The Rime API key stays server-side in `server.mjs`; it is never shipped to the browser.

## Stack

- Vite + TypeScript frontend
- Browser Web Speech API for live microphone transcription
- Local deterministic incident extraction for a predictable prototype
- Node/Express proxy
- Rime TTS for the primary spoken output

## Backend contract

The prototype now persists captured handoffs in `data/incidents.json` and exposes:

- `GET /api/health`
- `GET /api/incidents?status=open&limit=50`
- `GET /api/incidents/:id`
- `POST /api/incidents`
- `PATCH /api/incidents/:id/status`
- `POST /api/speak`

See [docs/architecture.md](docs/architecture.md) for the production architecture and [db/schema.sql](db/schema.sql) for the PostgreSQL schema.

## IoT voice backend

The requested split backend is scaffolded alongside the web demo:

- `agent.py`: LiveKit voice worker with Silero VAD, Deepgram STT, LLM function tools, MQTT commands/telemetry, and Rime TTS.
- `server.py`: FastAPI token dispenser and device registration API for iOS, Android, and Windows clients.
- `docker-compose.yml`: EMQX, Redis, PostgreSQL, LiveKit, API, and voice-agent services.
- `requirements.txt`: Python service dependencies.

Run the infrastructure with `docker compose up --build` after copying `.env.example` to `.env`. The LiveKit dev server uses `devkey` and `secret` locally; replace them before deployment. See [docs/client-integration.md](docs/client-integration.md) for platform SDK guidance.

### Windows voice control

The optional desktop controller listens locally for **Hey Jarvis**, captures the
command with the PCM pre-roll buffer, transcribes it, and routes it to a small
allowlisted set of Windows actions: launching common apps or URLs, volume,
window state, keyboard shortcuts, and typing. Install the Windows dependencies,
set `OPENAI_API_KEY`, then run:

```powershell
py -m pip install -r clients/windows/requirements.txt
py clients/windows/windows_voice_controller.py
```

Keep the PyAutoGUI failsafe enabled. Move the mouse to a screen corner to abort
an active desktop action.

For conversational answers with bounded multi-turn memory, sentence-level Rime
playback, audio ducking, and wake-word barge-in, set `RIME_API_KEY` and run:

```powershell
py clients/windows/alexa_backend.py
```

Say **Hey Jarvis** followed by a question or an allowed Windows action. A new
wake word stops current Rime playback and clears queued sentences.

The conversational controller also has live web tools. It uses DuckDuckGo for
current facts, news, and updates, and Open-Meteo for structured city weather;
neither requires an API key. Install the added dependency with the Windows
requirements, then ask **Hey Jarvis, what's the weather in Tokyo?** or **Hey
Jarvis, search for today's technology news.**

Rime responses use a persistent WebSocket and forward streamed LLM tokens
directly to PCM playback. If the WebSocket is unavailable, the controller falls
back to sentence-sized HTTP TTS. Saying **Hey Jarvis** during playback sends a
clear command to Rime and stops local audio immediately.

The listener is autonomous: it stays dormant with local wake-word detection,
captures each utterance until 1.2 seconds of silence, and remains latched for
six seconds after a reply so follow-up questions do not need the wake word.
After that idle window it returns to dormant listening automatically.

You normally start the listener once per Windows session. To launch it
automatically when you sign in, install the scheduled task once from an
elevated PowerShell prompt:

```powershell
py -m pip install -r clients/windows/requirements.txt
.\clients\windows\install_startup.ps1
```

After that, just say **Hey Jarvis**. The assistant must still have
`OPENAI_API_KEY` and `RIME_API_KEY` in the repository `.env` file.
