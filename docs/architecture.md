# Voice Bridge Architecture

## Product contract

Voice Bridge handles the handoff between a person who sees an operational incident and the operator who must act on it. The source is messy speech; the durable record is a structured incident; the primary confirmation is Rime-generated audio.

## Current prototype

- **Frontend:** Vite + TypeScript, using the browser Web Speech API for microphone transcription.
- **API:** Express REST endpoints under `/api`.
- **Prototype persistence:** `data/incidents.json`, intentionally dependency-free for local demos.
- **Speech:** Rime TTS is called only by the server through `POST /api/speak`.
- **Security boundary:** `RIME_API_KEY` is server-only and never enters browser bundles.

## Production replacement

Replace the JSON repository functions in `server.mjs` with PostgreSQL queries from `db/schema.sql`. Store generated audio in S3-compatible object storage and return a short-lived signed URL instead of holding audio in process memory. Add JWT or managed authentication before exposing the API outside a trusted network.

## REST API

- `GET /api/health` returns service status.
- `GET /api/incidents?status=open&limit=50` lists newest incidents.
- `GET /api/incidents/:id` returns one incident.
- `POST /api/incidents` creates a structured incident and persists the spoken handoff text.
- `PATCH /api/incidents/:id/status` changes status to `open`, `acknowledged`, or `resolved`.
- `POST /api/speak` turns text into Rime audio. This is the voice transport boundary.

## Third-party integrations

- **Rime:** primary spoken output.
- **Browser Web Speech API:** input transcription in the prototype; replace with a server-side streaming recognizer for consistent mobile support.
- **PostgreSQL:** durable incident records in production.
- **S3/R2:** generated audio retention in production.
- **FCM/APNs/OneSignal:** optional push notification when an incident is assigned or escalates.

## Acceptance test

A user speaks one natural-language report containing a location, issue, owner, and urgency. The app creates one incident, displays all four extracted facts, and Rime plays a concise next-action handoff within 10 seconds.
