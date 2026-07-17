from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import load_core_schemas, schema_registry


EVENT_NAMESPACE = uuid.NAMESPACE_URL


class SemanticValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def event_uuid(idempotency_id: str) -> str:
    return str(uuid.uuid5(EVENT_NAMESPACE, "https://openbrec.org/event/" + idempotency_id))


def adapter_idempotency(event: dict[str, Any]) -> str:
    recipe = {
        "source_namespace": f"urn:openbrec:adapter:{event['provenance']['name']}",
        "source_event_id": event["source_event_id"],
        "boot_id": event["boot_id"],
        "sequence": event["sequence"],
        "schema_ref": event["schema_ref"],
    }
    return "urn:sha256:" + canonical_hash(recipe)


def validate_event(event: Any, repository_root: Path) -> dict[str, Any]:
    schemas = load_core_schemas(repository_root)
    registry = schema_registry(schemas)
    schema = next(
        item for item, path in schemas if path.name == "domain-event.schema.json"
    )
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    errors = [
        f"schema /{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
        for error in validator.iter_errors(event)
    ]
    if not isinstance(event, dict):
        raise SemanticValidationError(errors or ["event must be an object"])
    if errors:
        raise SemanticValidationError(sorted(errors))

    if event["causation_event_ids"] != sorted(event["causation_event_ids"]):
        errors.append("causation_event_ids must be lexicographically ordered")
    if parse_timestamp(event["captured_at"]) > parse_timestamp(event["received_at"]):
        errors.append("captured_at must not be after received_at")
    policy = event["handling_policy"]
    if parse_timestamp(policy["accepted_at"]) >= parse_timestamp(
        policy["retention_until"]
    ):
        errors.append("handling accepted_at must be before retention_until")
    if parse_timestamp(event["received_at"]) > parse_timestamp(
        policy["retention_until"]
    ):
        errors.append("event received after retention_until")
    payload = event["payload"]
    if "window_start" in payload and "window_end" in payload:
        if parse_timestamp(payload["window_start"]) >= parse_timestamp(
            payload["window_end"]
        ):
            errors.append("window_start must be before window_end")
    if event["origin"] == "adapter":
        expected_idempotency = adapter_idempotency(event)
        if event["idempotency_id"] != expected_idempotency:
            errors.append("adapter idempotency recipe mismatch")
    if event["event_id"] != event_uuid(event["idempotency_id"]):
        errors.append("event_id does not match UUIDv5 idempotency recipe")
    if errors:
        raise SemanticValidationError(sorted(errors))
    return event


def validate_event_set(
    events: list[dict[str, Any]], repository_root: Path
) -> list[dict[str, Any]]:
    by_idempotency: dict[str, bytes] = {}
    unique: list[dict[str, Any]] = []
    sequence_seen: dict[tuple[str, str], int] = {}
    for event in events:
        validate_event(event, repository_root)
        from openbrec.canonical import canonicalize

        raw = canonicalize(event)
        previous = by_idempotency.get(event["idempotency_id"])
        if previous is not None:
            if previous != raw:
                raise SemanticValidationError(["idempotency collision"])
            continue
        by_idempotency[event["idempotency_id"]] = raw
        unique.append(event)

    ordered = sorted(
        unique,
        key=lambda event: (
            event["captured_at"],
            event.get("source_node_id", ""),
            event["boot_id"],
            event["sequence"],
            event["event_id"],
        ),
    )
    for event in ordered:
        key = (event.get("source_node_id", ""), event["boot_id"])
        previous = sequence_seen.get(key)
        if previous is not None and event["sequence"] <= previous:
            raise SemanticValidationError(["sequence is repeated or regressive"])
        sequence_seen[key] = event["sequence"]
    return ordered
