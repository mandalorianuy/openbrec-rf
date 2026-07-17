from __future__ import annotations

import http.client
import json
import queue
import socket
import threading

import paho.mqtt.client as mqtt

from openbrec.runtime import PROCESSED_OBSERVATION_TOPIC


OBSERVATION = {
    "schema_version": "1.0.0",
    "observation_id": "55555555-5555-4555-8555-555555555555",
    "sensor_id": "synthetic-1",
    "sensor_type": "synthetic",
    "observation_kind": "measurement",
    "window_start": "2026-07-17T12:10:00.000000Z",
    "window_end": "2026-07-17T12:10:01.000000Z",
    "measurements": [{
        "measurement_type": "scalar",
        "metric": "synthetic.level",
        "value": 0.25,
        "unit": "1",
        "uncertainty": 0.1,
        "quality": 0.8,
        "method": "runtime smoke",
    }],
    "quality": 0.8,
    "uncertainty": 0.2,
    "coverage": "synthetic window",
    "capabilities_absent": ["hardware"],
    "limitations": ["not field evidence"],
}


def request(
    host: str, port: int, method: str, path: str, payload: dict | None = None
) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection(host, port, timeout=5)
    body = None if payload is None else json.dumps(payload)
    headers = {} if body is None else {"Content-Type": "application/json"}
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


def main() -> int:
    processed: queue.Queue[dict] = queue.Queue(maxsize=1)
    subscribed = threading.Event()
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="openbrec-runtime-smoke",
        protocol=mqtt.MQTTv5,
    )

    def on_connect(client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            client.subscribe(PROCESSED_OBSERVATION_TOPIC, qos=1)

    def on_subscribe(client, userdata, mid, reason_codes, properties) -> None:
        subscribed.set()

    def on_message(client, userdata, message) -> None:
        processed.put_nowait(json.loads(message.payload.decode("utf-8")))

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect("mqtt", 1883, keepalive=30)
    client.loop_start()
    if not subscribed.wait(timeout=5):
        raise RuntimeError("smoke subscriber not ready")

    valid_status, _ = request("api", 8000, "POST", "/v1/observations", OBSERVATION)
    if valid_status != 202:
        raise RuntimeError(f"valid observation returned HTTP {valid_status}")
    state = processed.get(timeout=10)
    if state.get("observation_id") != OBSERVATION["observation_id"]:
        raise RuntimeError("worker did not process expected observation")

    invalid_status, _ = request(
        "api", 8000, "POST", "/v1/observations", {**OBSERVATION, "quality": 2}
    )
    if invalid_status != 422:
        raise RuntimeError(f"invalid observation returned HTTP {invalid_status}")

    for asset in ("/", "/manifest.webmanifest", "/sw.js"):
        asset_status, _ = request("web", 8080, "GET", asset)
        if asset_status != 200:
            raise RuntimeError(f"PWA asset {asset} returned HTTP {asset_status}")

    try:
        socket.create_connection(("1.1.1.1", 443), timeout=2).close()
    except OSError:
        external_network = "denied"
    else:
        raise RuntimeError("lab-sim unexpectedly has external network access")

    client.disconnect()
    client.loop_stop()
    print(json.dumps({
        "valid_observation": "processed",
        "invalid_observation": "rejected",
        "pwa_shell": "available",
        "external_network": external_network,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
