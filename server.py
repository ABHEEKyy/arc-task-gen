"""Client token dispenser and device registration API."""

import os
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from livekit import api
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="Voice IoT Gateway", version="1.0.0")

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")


class SessionRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    room_name: str = Field(default="iot-control-room", min_length=1, max_length=128)


class DeviceRegistration(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    device_type: str = Field(min_length=1, max_length=50)
    mqtt_topic: str = Field(min_length=1, max_length=255)
    room_id: UUID | None = None


@app.get("/health")
def health() -> dict[str, bool | str]:
    return {"ok": True, "service": "voice-iot-gateway"}


@app.post("/api/v1/session/token")
def create_voice_token(payload: SessionRequest) -> dict[str, str]:
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=503, detail="LiveKit credentials are not configured")
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(payload.user_id)
        .with_name(f"User-{payload.user_id}")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=payload.room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return {"token": token.to_jwt(), "ws_url": LIVEKIT_URL}


@app.post("/api/v1/devices")
def register_device(device: DeviceRegistration) -> dict[str, str | None]:
    """Return the normalized registration; persist through PostgreSQL in production."""
    return {"device_id": device.device_id, "status": "registered", "mqtt_topic": device.mqtt_topic}
