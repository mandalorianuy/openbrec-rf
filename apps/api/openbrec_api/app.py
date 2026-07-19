from __future__ import annotations

import json
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal, Protocol

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Query, status

from openbrec.fusion import FusionError, validate_fusion_result
from openbrec.fusion_store import PostgresFusionStore
from openbrec.runtime import ACCEPTED_OBSERVATION_TOPIC, ContractValidationError
from openbrec.runtime import observation_to_event, validate_observation


class Publisher(Protocol):
    @property
    def ready(self) -> bool: ...

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def publish(self, topic: str, payload: dict[str, Any]) -> None: ...


class FusionReader(Protocol):
    @property
    def ready(self) -> bool: ...

    def connect(self) -> None: ...

    def close(self) -> None: ...

    def list_observations(
        self,
        *,
        zone_id: str | None = None,
        sensor_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def list_fusion_results(
        self,
        *,
        zone_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]: ...

    def get_fusion_result(self, result_id: str) -> dict[str, Any] | None: ...


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


def create_app(
    publisher: Publisher | None = None, reader: FusionReader | None = None
) -> FastAPI:
    selected = publisher or MqttPublisher(
        os.environ.get("OPENBREC_MQTT_HOST", "mqtt"),
        int(os.environ.get("OPENBREC_MQTT_PORT", "1883")),
    )
    selected_reader = reader or PostgresFusionStore.from_environment()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        selected.connect()
        selected_reader.connect()
        yield
        selected_reader.close()
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
            selected.publish(
                ACCEPTED_OBSERVATION_TOPIC, observation_to_event(observation)
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {
            "status": "accepted",
            "observation_id": str(observation["observation_id"]),
        }

    def require_reader() -> FusionReader:
        if not selected_reader.ready:
            raise HTTPException(status_code=503, detail="read model unavailable")
        return selected_reader

    @app.get("/v1/observations")
    def list_observations(
        zone_id: str | None = None,
        sensor_type: Literal["synthetic", "operator", "addon_registered"]
        | None = None,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        store = require_reader()
        items = store.list_observations(
            zone_id=zone_id, sensor_type=sensor_type, limit=limit
        )
        try:
            return {
                "items": [validate_observation(item) for item in items],
            }
        except ContractValidationError as exc:
            raise HTTPException(
                status_code=500, detail="stored observation violates contract"
            ) from exc

    @app.get("/v1/fusion-results")
    def list_fusion_results(
        zone_id: str | None = None,
        state: Literal["indicator", "conflicted", "abstained"] | None = None,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        store = require_reader()
        items = store.list_fusion_results(
            zone_id=zone_id, state=state, limit=limit
        )
        try:
            return {
                "items": [validate_fusion_result(item) for item in items],
            }
        except FusionError as exc:
            raise HTTPException(
                status_code=500, detail="stored fusion result violates contract"
            ) from exc

    @app.get("/v1/fusion-results/{result_id}")
    def get_fusion_result(result_id: str) -> dict[str, Any]:
        store = require_reader()
        result = store.get_fusion_result(result_id)
        if result is None:
            raise HTTPException(status_code=404, detail="fusion result not found")
        try:
            return validate_fusion_result(result)
        except FusionError as exc:
            raise HTTPException(
                status_code=500, detail="stored fusion result violates contract"
            ) from exc

    return app


app = create_app()
