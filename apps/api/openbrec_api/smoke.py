from __future__ import annotations

import http.client
import json
import os
import queue
import socket
import threading
from pathlib import Path

import paho.mqtt.client as mqtt
import psycopg

from openbrec.runtime import PROCESSED_OBSERVATION_TOPIC


OBSERVATION = {
    "schema_version": "1.0.0",
    "observation_id": "55555555-5555-4555-8555-555555555555",
    "sensor_id": "synthetic-1",
    "sensor_type": "synthetic",
    "observation_kind": "measurement",
    "window_start": "2026-07-17T12:10:00.000000Z",
    "window_end": "2026-07-17T12:10:01.000000Z",
    "measurements": [
        {
            "measurement_type": "scalar",
            "metric": "synthetic.level",
            "value": 0.25,
            "unit": "1",
            "uncertainty": 0.1,
            "quality": 0.8,
            "method": "runtime smoke",
        }
    ],
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


def verify_postgres_durability() -> None:
    password_path = Path(
        os.environ.get(
            "OPENBREC_POSTGRES_PASSWORD_FILE", "/run/secrets/postgres_password"
        )
    )
    try:
        password = password_path.read_text(encoding="utf-8").strip()
    except OSError:
        password = os.environ.get("OPENBREC_POSTGRES_PASSWORD", "")
    if not password:
        raise RuntimeError("PostgreSQL password is unavailable")
    dsn = (
        f"host={os.environ.get('OPENBREC_POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('OPENBREC_POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('OPENBREC_POSTGRES_DB', 'openbrec')} "
        f"user={os.environ.get('OPENBREC_POSTGRES_USER', 'openbrec')} "
        f"password={password} connect_timeout=5"
    )
    with psycopg.connect(dsn) as connection:
        accepted = connection.execute(
            "SELECT COUNT(*) FROM accepted_event_log"
        ).fetchone()[0]
        ingress = connection.execute("SELECT COUNT(*) FROM ingress_units").fetchone()[0]
        physical = sum(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "accepted_event_log",
                "review_quarantine",
                "evidence_vault",
                "rejection_ledger",
            )
        )
    unreconciled = abs(ingress - physical)
    if accepted != 1 or ingress != 1 or unreconciled != 0:
        raise RuntimeError(
            f"PostgreSQL durability mismatch accepted={accepted} ingress={ingress} "
            f"unreconciled={unreconciled}"
        )


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
    if state.get("status") != "durably_processed":
        raise RuntimeError("worker acknowledged before durable disposition")
    if state.get("fusion_state") not in {"indicator", "conflicted", "abstained"}:
        raise RuntimeError("worker did not persist a fusion result")
    verify_postgres_durability()

    observations_status, observations_body = request(
        "api", 8000, "GET", "/v1/observations"
    )
    if observations_status != 200:
        raise RuntimeError(f"observation read returned HTTP {observations_status}")
    observation_ids = [
        item["observation_id"] for item in json.loads(observations_body)["items"]
    ]
    if observation_ids != [OBSERVATION["observation_id"]]:
        raise RuntimeError("read model did not return the ingested observation")
    results_status, results_body = request("api", 8000, "GET", "/v1/fusion-results")
    if results_status != 200:
        raise RuntimeError(f"fusion read returned HTTP {results_status}")
    results = json.loads(results_body)["items"]
    if len(results) != 1 or results[0]["result_id"] != state.get("fusion_result_id"):
        raise RuntimeError("read model did not return the worker fusion result")
    if results[0]["supporting_evidence_ids"] != [OBSERVATION["observation_id"]]:
        raise RuntimeError("fusion result lost its supporting evidence")
    detail_status, _ = request(
        "api", 8000, "GET", f"/v1/fusion-results/{results[0]['result_id']}"
    )
    if detail_status != 200:
        raise RuntimeError(f"fusion detail returned HTTP {detail_status}")

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
    print(
        json.dumps(
            {
                "valid_observation": "processed",
                "invalid_observation": "rejected",
                "fusion_read": "passed",
                "pwa_shell": "available",
                "external_network": external_network,
                "postgres_durable": "passed",
                "unreconciled": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
