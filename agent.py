"""LiveKit voice agent with MQTT device tools and Rime speech output."""

import asyncio
import json
import os
from typing import Any

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import deepgram, rime, silero

load_dotenv()

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if MQTT_USER:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
telemetry_cache: dict[str, dict[str, Any]] = {}


def on_telemetry(_client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
    device_id = message.topic.removeprefix("home/devices/").removesuffix("/telemetry")
    try:
        telemetry_cache[device_id] = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError:
        telemetry_cache[device_id] = {"raw": message.payload.decode("utf-8")}


mqtt_client.on_message = on_telemetry
mqtt_client.connect(MQTT_HOST, MQTT_PORT)
mqtt_client.subscribe("home/devices/+/telemetry", qos=1)
mqtt_client.loop_start()


def publish_command(device_id: str, state: str, value: int | float | None = None) -> None:
    payload: dict[str, Any] = {"state": state}
    if value is not None:
        payload["value"] = value
    result = mqtt_client.publish(
        f"home/devices/{device_id}/set", json.dumps(payload), qos=1
    )
    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"MQTT publish failed with code {result.rc}")


class IoTController(llm.FunctionContext):
    @llm.ai_callable(description="Control a smart home device or appliance immediately.")
    def set_device_state(
        self,
        device_id: str,
        state: str,
        value: int = 0,
    ) -> str:
        """state is on, off, set_level, or set_temperature."""
        allowed_states = {"on", "off", "set_level", "set_temperature"}
        if state not in allowed_states:
            return f"Unsupported state {state}."
        publish_command(device_id, state, value if state not in {"on", "off"} else None)
        return f"Set {device_id} to {state} {value if state not in {'on', 'off'} else ''}".strip()

    @llm.ai_callable(description="Query the current state or telemetry for a smart home device.")
    async def get_device_status(self, device_id: str) -> str:
        """Read the latest telemetry reported by the MQTT device hub."""
        await asyncio.sleep(0)
        state = telemetry_cache.get(device_id)
        if not state:
            return f"No recent telemetry is available for {device_id}."
        return f"{device_id} reports {json.dumps(state, separators=(',', ':'))}."


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    rime_tts = rime.TTS(
        model=os.getenv("RIME_MODEL", "mistv3"),
        voice=os.getenv("RIME_VOICE", "celeste"),
        speed_alpha=float(os.getenv("RIME_SPEED_ALPHA", "1.05")),
    )
    instructions = (
        "You are an ambient, fast smart-home voice controller. "
        "The leading wake phrase such as Computer or Hey Jarvis is a trigger, not part of the command; ignore it. "
        "Use device tools immediately. Confirm actions in under 10 words. "
        "Never use markdown, emojis, or lists. Ask one short clarification when a device is ambiguous."
    )
    agent = MultimodalAgent(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model=os.getenv("DEEPGRAM_MODEL", "nova-2")),
        tts=rime_tts,
        fnc_ctx=IoTController(),
        instructions=instructions,
    )
    agent.start(ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
