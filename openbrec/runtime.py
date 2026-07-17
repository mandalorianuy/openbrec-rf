from __future__ import annotations

import hashlib
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.contracts import load_core_schemas, schema_registry
from openbrec.canonical import canonical_hash
from openbrec.semantic import (
    adapter_idempotency,
    event_uuid,
    parse_timestamp,
    validate_event,
)


ACCEPTED_OBSERVATION_TOPIC = "openbrec/core/observations/accepted"
PROCESSED_OBSERVATION_TOPIC = "openbrec/core/observations/processed"
LAB_INCIDENT_ID = "11111111-1111-4111-8111-111111111111"
LAB_DEPLOYMENT_ID = "22222222-2222-4222-8222-222222222222"
LAB_BOOT_ID = "33333333-3333-4333-8333-333333333333"
LAB_SESSION_ID = "44444444-4444-4444-8444-444444444444"


class ContractValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@lru_cache(maxsize=1)
def _observation_validator() -> Draft202012Validator:
    root = Path(__file__).resolve().parents[1]
    schemas = load_core_schemas(root)
    schema = next(
        value for value, path in schemas if path.name == "observation.schema.json"
    )
    return Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )


def validate_observation(payload: Any) -> dict[str, Any]:
    errors = sorted(
        _observation_validator().iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        messages = [
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        ]
        raise ContractValidationError(messages)
    if not isinstance(payload, dict):
        raise ContractValidationError(["/: observation must be an object"])
    return payload


def _timestamp(value) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def observation_to_event(payload: Any) -> dict[str, Any]:
    observation = validate_observation(payload)
    captured = parse_timestamp(observation["window_start"])
    received = parse_timestamp(observation["window_end"])
    retention = received + timedelta(days=1)
    sensor_digest = hashlib.sha256(observation["sensor_id"].encode("utf-8")).hexdigest()
    source_event_id = f"runtime:observation:{observation['observation_id']}"
    configuration = {
        "profile": "lab-sim",
        "adapter": "runtime-api",
        "version": "1.0.0",
    }
    event: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema_ref": "https://openbrec.org/schemas/core/observation/1.0.0",
        "event_type": "observation",
        "event_id": "00000000-0000-5000-8000-000000000000",
        "idempotency_id": "urn:sha256:" + "0" * 64,
        "correlation_id": observation["observation_id"],
        "causation_event_ids": [],
        "incident_id": LAB_INCIDENT_ID,
        "deployment_id": LAB_DEPLOYMENT_ID,
        "source_node_id": f"node-{sensor_digest[:8]}",
        "origin": "adapter",
        "source_event_id": source_event_id,
        "boot_id": LAB_BOOT_ID,
        "session_id": LAB_SESSION_ID,
        "sequence": int(captured.timestamp() * 1_000_000),
        "captured_at": _timestamp(captured),
        "received_at": _timestamp(received),
        "clock_uncertainty_ms": 0,
        "clock_source": "logical",
        "provenance": {
            "schema_version": "1.0.0",
            "artifact_type": "adapter",
            "name": "runtime-api",
            "version": "1.0.0",
            "artifact_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "recorded_at": _timestamp(captured),
            "configuration_sha256": canonical_hash(configuration),
            "capabilities_present": [f"sensor.{observation['sensor_type']}"],
            "capabilities_absent": sorted(observation["capabilities_absent"]),
            "limitations": ["lab-sim synthetic runtime only"],
        },
        "handling_policy": {
            "schema_version": "1.0.0",
            "policy_id": "urn:openbrec:handling:routine:1.0.0",
            "mode": "routine_minimized",
            "retention_until": _timestamp(retention),
            "accepted_at": _timestamp(captured),
            "purpose": "synthetic lab runtime",
            "audit_required": True,
        },
        "retention_policy_id": "urn:openbrec:retention:lab:1.0.0",
        "privacy_flags": {
            "contains_direct_identifier": False,
            "contains_raw_payload": False,
            "life_safety_relevant": False,
        },
        "payload": observation,
    }
    event["idempotency_id"] = adapter_idempotency(event)
    event["event_id"] = event_uuid(event["idempotency_id"])
    validate_event(event, Path(__file__).resolve().parents[1])
    return event
