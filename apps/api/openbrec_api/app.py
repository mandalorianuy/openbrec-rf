from __future__ import annotations

import json
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, status

from openbrec.runtime import ACCEPTED_OBSERVATION_TOPIC, ContractValidationError
from openbrec.runtime import validate_observation


class Publisher(Protocol):
    @property
    def ready(self) -> bool: ...

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...


class RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict[str, Any]]] = []

    @property
    def ready(self) -> bool:
        return True

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.messages.append((topic, payload))


class MqttPublisher:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._connected = threading.Event()
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="openbrec-api",
            protocol=mqtt.MQTTv5,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    @property
    def ready(self) -> bool:
        return self._connected.is_set()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            self._connected.set()

    def _on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ) -> None:
        self._connected.clear()

    def connect(self) -> None:
        self._client.connect(self.host, self.port, keepalive=30)
        self._client.loop_start()
        if not self._connected.wait(timeout=10):
            raise RuntimeError("MQTT readiness timeout")

    def close(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if not self.ready:
            raise RuntimeError("MQTT publisher is not ready")
        info = self._client.publish(
            topic,
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            qos=1,
            retain=False,
        )
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            raise RuntimeError("MQTT publish was not acknowledged")


def create_app(publisher: Publisher | None = None) -> FastAPI:
    selected = publisher or MqttPublisher(
        os.environ.get("OPENBREC_MQTT_HOST", "mqtt"),
        int(os.environ.get("OPENBREC_MQTT_PORT", "1883")),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        selected.connect()
        yield
        selected.close()

    app = FastAPI(title="OpenBREC RF M0 API", version="0.1.0", lifespan=lifespan)

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readiness() -> dict[str, str]:
        if not selected.ready:
            raise HTTPException(status_code=503, detail="event bus unavailable")
        return {"status": "ready"}

    @app.post("/v1/observations", status_code=status.HTTP_202_ACCEPTED)
    def ingest(payload: dict[str, Any]) -> dict[str, str]:
        try:
            observation = validate_observation(payload)
        except ContractValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors) from exc
        try:
            selected.publish(ACCEPTED_OBSERVATION_TOPIC, observation)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "status": "accepted",
            "observation_id": str(observation["observation_id"]),
        }

    return app


app = create_app()
