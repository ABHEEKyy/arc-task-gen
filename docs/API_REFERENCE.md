# Voice Bridge & IoT Gateway API Reference

This document provides the complete API specification for both the **Web Incident Handoff API** (Node/Express, port `8787`) and the **IoT Voice Gateway API** (FastAPI, port `8000`).

---

## Table of Contents

1. [Web Incident Handoff API](#1-web-incident-handoff-api)
   - [GET /api/health](#get-apihealth)
   - [GET /api/incidents](#get-apiincidents)
   - [GET /api/incidents/:id](#get-apiincidentsid)
   - [POST /api/incidents](#post-apiincidents)
   - [PATCH /api/incidents/:id/status](#patch-apiincidentsidstatus)
   - [POST /api/speak](#post-apispeak)
2. [FastAPI IoT Gateway API](#2-fastapi-iot-gateway-api)
   - [GET /health](#get-health)
   - [POST /api/v1/session/token](#post-apiv1sessiontoken)
   - [POST /api/v1/devices](#post-apiv1devices)
3. [Error Handling & Status Codes](#3-error-handling--status-codes)

---

## 1. Web Incident Handoff API

Base URL: `http://localhost:8787`

### GET /api/health
Checks the health of the Express API server.

**Request:**
```http
GET /api/health HTTP/1.1
Host: localhost:8787
```

**Response (200 OK):**
```json
{
  "ok": true,
  "service": "voice-bridge"
}
```

---

### GET /api/incidents
Lists logged incident handoffs. Supports filtering by status and limit.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `status` | string | No | null | Filter by status: `open`, `acknowledged`, `resolved` |
| `limit` | integer | No | `50` | Maximum items to return (max `100`) |

**Request:**
```bash
curl -X GET "http://localhost:8787/api/incidents?status=open&limit=10"
```

**Response (200 OK):**
```json
[
  {
    "id": "c76f6db2-38d7-4c40-9a3c-a63e9c57e2ad",
    "transcript": "Substation 4 transformer oil temperature spiked above 95C. Marcus on site monitoring telemetry. Needs technician dispatch.",
    "issue": "transformer oil temperature spiked above 95C",
    "location": "Substation 4",
    "owner": "Marcus",
    "urgency": "critical",
    "nextStep": "technician dispatch",
    "spokenText": "Critical incident at Substation 4. Transformer oil temperature spiked above 95C. Marcus on site. Next move: technician dispatch.",
    "status": "open",
    "createdAt": "2026-09-08T17:45:00.000Z",
    "updatedAt": "2026-09-08T17:45:00.000Z"
  }
]
```

---

### GET /api/incidents/:id
Retrieves a single incident by its unique UUID.

**Path Parameters:**
- `id`: Incident UUID.

**Request:**
```bash
curl -X GET "http://localhost:8787/api/incidents/c76f6db2-38d7-4c40-9a3c-a63e9c57e2ad"
```

**Response (200 OK):**
```json
{
  "id": "c76f6db2-38d7-4c40-9a3c-a63e9c57e2ad",
  "transcript": "...",
  "issue": "...",
  "location": "...",
  "owner": "...",
  "urgency": "critical",
  "nextStep": "...",
  "spokenText": "...",
  "status": "open",
  "createdAt": "2026-09-08T17:45:00.000Z",
  "updatedAt": "2026-09-08T17:45:00.000Z"
}
```

**Error (404 Not Found):**
```json
{
  "error": "Incident not found."
}
```

---

### POST /api/incidents
Creates a new structured incident record after speech transcription and entity extraction.

**Request Headers:**
- `Content-Type: application/json`

**Body Schema:**
```json
{
  "transcript": "Unstructured speech transcript",
  "issue": "Extracted problem description",
  "location": "Site, room, or asset identifier",
  "owner": "Name of responsible personnel on site",
  "urgency": "critical | high | standard",
  "nextStep": "Recommended next action or dispatch",
  "spokenText": "Formatted text to be vocalized by TTS"
}
```

**Request:**
```bash
curl -X POST "http://localhost:8787/api/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Water pipe leak in Server Room B. Elena is shutting off main valve. Need cleanup team.",
    "issue": "Water pipe leak",
    "location": "Server Room B",
    "owner": "Elena",
    "urgency": "high",
    "nextStep": "dispatch cleanup team",
    "spokenText": "High urgency issue in Server Room B. Water pipe leak reported by Elena. Next action: dispatch cleanup team."
  }'
```

**Response (201 Created):**
```json
{
  "id": "8f889c13-a4f6-455b-b9d9-bbba13d6a2f1",
  "transcript": "Water pipe leak in Server Room B...",
  "issue": "Water pipe leak",
  "location": "Server Room B",
  "owner": "Elena",
  "urgency": "high",
  "nextStep": "dispatch cleanup team",
  "spokenText": "High urgency issue in Server Room B...",
  "status": "open",
  "createdAt": "2026-09-08T18:00:12.345Z",
  "updatedAt": "2026-09-08T18:00:12.345Z"
}
```

---

### PATCH /api/incidents/:id/status
Updates the lifecycle status of an existing incident.

**Path Parameters:**
- `id`: Incident UUID.

**Body Schema:**
```json
{
  "status": "open | acknowledged | resolved"
}
```

**Request:**
```bash
curl -X PATCH "http://localhost:8787/api/incidents/8f889c13-a4f6-455b-b9d9-bbba13d6a2f1/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged"}'
```

**Response (200 OK):**
```json
{
  "id": "8f889c13-a4f6-455b-b9d9-bbba13d6a2f1",
  "status": "acknowledged",
  "updatedAt": "2026-09-08T18:05:00.000Z"
}
```

---

### POST /api/speak
Converts text into audio speech via Rime Labs TTS. The server contacts Rime securely using `RIME_API_KEY` and returns raw audio bytes directly to the client.

**Request Headers:**
- `Content-Type: application/json`

**Body Schema:**
```json
{
  "text": "Text to synthesize into voice."
}
```

**Request:**
```bash
curl -X POST "http://localhost:8787/api/speak" \
  -H "Content-Type: application/json" \
  -d '{"text": "Critical incident at Substation 4. Marcus is on site."}' \
  --output handoff.mp3
```

**Response (200 OK):**
- **Content-Type**: `audio/mpeg` or `audio/wav`
- **Body**: Binary audio stream

---

## 2. FastAPI IoT Gateway API

Base URL: `http://localhost:8000`

### GET /health
Checks FastAPI service availability.

**Request:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Response (200 OK):**
```json
{
  "ok": true,
  "service": "voice-iot-gateway"
}
```

---

### POST /api/v1/session/token
Generates a signed LiveKit WebRTC Access Token (JWT) allowing a client (iOS, Android, Windows) to join a voice room and stream audio.

**Request Headers:**
- `Content-Type: application/json`

**Body Schema:**
```json
{
  "user_id": "string (1-128 chars)",
  "room_name": "string (default: iot-control-room)"
}
```

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/session/token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "operator_42",
    "room_name": "iot-control-room"
  }'
```

**Response (200 OK):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "ws_url": "ws://localhost:7880"
}
```

---

### POST /api/v1/devices
Registers an IoT device with the gateway and associates its MQTT control topic.

**Body Schema:**
```json
{
  "device_id": "string (1-100 chars)",
  "name": "string (1-100 chars)",
  "device_type": "string (e.g., light, thermostat, plug)",
  "mqtt_topic": "string (MQTT telemetry/command root)",
  "room_id": "UUID | null"
}
```

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/devices" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "thermostat_living_room",
    "name": "Main Thermostat",
    "device_type": "climate",
    "mqtt_topic": "home/devices/thermostat_living_room",
    "room_id": null
  }'
```

**Response (200 OK):**
```json
{
  "device_id": "thermostat_living_room",
  "status": "registered",
  "mqtt_topic": "home/devices/thermostat_living_room"
}
```

---

## 3. Error Handling & Status Codes

| Code | Meaning | Common Cause |
| :--- | :--- | :--- |
| `200` | OK | Successful fetch, update, or synthesis |
| `201` | Created | Successful resource creation (Incident) |
| `400` | Bad Request | Missing required body fields or invalid enum value |
| `404` | Not Found | Incident ID not found in data store |
| `502` | Bad Gateway | Upstream TTS provider (Rime) unreachable |
| `503` | Service Unavailable | `LIVEKIT_API_KEY` or `RIME_API_KEY` missing from `.env` |
