from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

from openbrec.runtime import ACCEPTED_OBSERVATION_TOPIC, ContractValidationError
from openbrec.runtime import PROCESSED_OBSERVATION_TOPIC, validate_observation

__all__ = ["ContractValidationError", "process_observation", "run_worker"]


def process_observation(
    payload: Any, *, worker_id: str = "fusion-worker-1"
) -> dict[str, str]:
    observation = validate_observation(payload)
    return {
        "status": "processed",
        "worker_id": worker_id,
        "observation_id": str(observation["observation_id"]),
    }


async def run_worker() -> None:
    host = os.environ.get("OPENBREC_MQTT_HOST", "mqtt")
    port = int(os.environ.get("OPENBREC_MQTT_PORT", "1883"))
    worker_id = os.environ.get("OPENBREC_WORKER_ID", "fusion-worker-1")
    ready_file = Path(os.environ.get("OPENBREC_READY_FILE", "/tmp/openbrec-worker-ready"))
    connected = asyncio.Event()
    loop = asyncio.get_running_loop()
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=worker_id,
        protocol=mqtt.MQTTv5,
    )

    def on_connect(client, userdata, flags, reason_code, properties) -> None:
        if reason_code != 0:
            return
        client.subscribe(ACCEPTED_OBSERVATION_TOPIC, qos=1)
        ready_file.write_text("ready\n", encoding="utf-8")
        loop.call_soon_threadsafe(connected.set)

    def on_message(client, userdata, message) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            processed = process_observation(payload, worker_id=worker_id)
        except (UnicodeDecodeError, json.JSONDecodeError, ContractValidationError):
            return
        client.publish(
            PROCESSED_OBSERVATION_TOPIC,
            json.dumps(processed, separators=(",", ":"), sort_keys=True),
            qos=1,
            retain=False,
        )

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=30)
    client.loop_start()
    try:
        await asyncio.wait_for(connected.wait(), timeout=10)
        await asyncio.Event().wait()
    finally:
        ready_file.unlink(missing_ok=True)
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    asyncio.run(run_worker())
