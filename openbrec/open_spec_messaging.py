from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash

PLAN_PATH = Path("docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md")
POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path(
    "specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json"
)
CONTENT_SCHEMA_PATH = Path("schemas/open-spec/human-message-content.schema.json")
EVENT_SCHEMA_PATH = Path("schemas/open-spec/human-message-lifecycle-event.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/messaging/interoperability-examples.json")
RESIDUALS_PATH = Path("docs/governance/open-spec-messaging-residuals.json")
P0_CRYPTO_RECEIPT_PATH = Path(
    "evidence/p0/p0-03/human-message-security/p0-03-receipt.json"
)

MESSAGE_TYPES = {"text", "status", "sos", "location"}
SOS_EVENTS = {
    "sos.created",
    "sos.queued",
    "transport.transmitted",
    "transport.relay_observed",
    "gateway.received",
    "operator.seen",
    "operator.accepted",
    "sos.cancel_requested",
    "sos.expired",
    "sos.failed",
}
SECURITY_TRUE_FIELDS = (
    "incident_scoped_identity",
    "actor_device_binding",
    "encrypt_then_sign",
    "all_routing_headers_authenticated",
    "ttl_checked",
    "boot_sequence_monotonic",
    "nonce_reuse_fails_closed",
    "revocation_and_rekey_offline",
    "stable_message_id_across_bearers",
)


def _read_json(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [
            f"{label} unreadable: {path.name}: {exc.strerror or type(exc).__name__}"
        ]
    except json.JSONDecodeError as exc:
        return None, [
            f"{label} invalid JSON: {path.name}: line {exc.lineno} column {exc.colno}"
        ]
    if not isinstance(value, dict):
        return None, [f"{label} must be an object"]
    return value, []


def _validate_policy(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("progress") != {
        "accepted_tasks": 5,
        "total_tasks": 8,
        "percent": 62.5,
    }:
        errors.append("open-spec progress must be 5 / 8")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        return [*errors, "open-spec policy must contain eight tasks"]
    if [task.get("status") for task in tasks[:5]] != ["accepted"] * 5:
        errors.append("OS-01 through OS-05 must be accepted")
    if any(task.get("status") != "not_started" for task in tasks[5:]):
        errors.append("OS-06 through OS-08 must remain not_started")
    if tasks[3].get("gate") != "open-spec-messaging":
        errors.append("OS-04 must use the open-spec-messaging gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("messaging profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open messaging boundary is required")
    else:
        if boundary.get("requires_specific_bearer") is not False:
            errors.append("a specific bearer cannot be mandatory")
        if boundary.get("requires_owned_hardware") is not False:
            errors.append("owned hardware cannot gate messaging profiles")
        if boundary.get("physical_delivery_blocks_spec") is not False:
            errors.append("physical delivery cannot block the messaging specification")
        if boundary.get("cloud_dependency_allowed_in_critical_path") is not False:
            errors.append("cloud cannot enter the critical messaging path")

    rows = value.get("message_profiles")
    if not isinstance(rows, list) or len(rows) != 4:
        errors.append("messaging profiles must define four message types")
    elif {
        row.get("message_type") for row in rows if isinstance(row, dict)
    } != MESSAGE_TYPES:
        errors.append("messaging profiles must cover text, status, SOS and location")
    else:
        for index, row in enumerate(rows):
            if row.get("alternatives_allowed") is not True:
                errors.append(f"message_profiles[{index}] must allow alternatives")
            for field in ("content_contract", "acceptance_criteria", "limitations"):
                if not row.get(field):
                    errors.append(
                        f"message_profiles[{index}].{field} must not be empty"
                    )

    security = value.get("application_security")
    if not isinstance(security, dict):
        errors.append("application security policy is required")
    else:
        if security.get("trust_boundary") != "untrusted_transport":
            errors.append("all bearers must remain untrusted transports")
        for field in SECURITY_TRUE_FIELDS:
            if security.get(field) is not True:
                errors.append(f"application security invariant missing: {field}")
        for field in (
            "bearer_id_is_actor_identity",
            "transport_ack_is_delivery",
            "transport_ack_is_operator_acceptance",
        ):
            if security.get(field) is not False:
                errors.append(f"application security must keep {field} false")
        if security.get("p0_crypto_evidence_ref") != str(P0_CRYPTO_RECEIPT_PATH):
            errors.append("P0 cryptographic evidence reference is missing")

    distress = value.get("distress_policy")
    if not isinstance(distress, dict):
        errors.append("distress policy is required")
    else:
        if set(distress.get("event_types", [])) != SOS_EVENTS:
            errors.append("distress lifecycle event types are incomplete")
        for field in (
            "append_only",
            "cancel_adds_event_never_erases",
            "late_event_never_regresses_terminal_state",
            "operator_acceptance_requires_gateway_seen_and_authorized_signature",
        ):
            if distress.get(field) is not True:
                errors.append(f"distress invariant missing: {field}")
        if distress.get("gateway_received_means_rescue") is not False:
            errors.append("gateway receipt cannot guarantee rescue")
        if distress.get("operator_accepted_means_rescue") is not False:
            errors.append("operator acceptance cannot guarantee rescue")
        if distress.get("transport_may_set_derived_state") is not False:
            errors.append("transport cannot set derived distress state")

    preservation = value.get("life_safety_preservation")
    if not isinstance(preservation, dict):
        errors.append("life-safety preservation policy is required")
    else:
        for field in (
            "possible_distress_is_never_silently_discarded",
            "access_control_required",
            "audit_required",
            "retention_review_required",
        ):
            if preservation.get(field) is not True:
                errors.append(f"life-safety preservation invariant missing: {field}")
        if preservation.get("unverified_distress_becomes_authenticated") is not False:
            errors.append("unverified distress cannot become authenticated")
        if (
            preservation.get("privacy_minimization_may_destroy_possible_distress")
            is not False
        ):
            errors.append("privacy minimization cannot destroy possible distress")
        if set(preservation.get("allowed_destinations", [])) != {
            "EvidenceVault",
            "ReviewQuarantine",
        }:
            errors.append("possible distress must route to vault or quarantine")
    return errors


def _validate_schemas_and_fixtures(
    content_schema: dict[str, Any],
    event_schema: dict[str, Any],
    fixtures: dict[str, Any],
) -> tuple[list[str], int]:
    errors: list[str] = []
    for label, schema in (("content", content_schema), ("event", event_schema)):
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"human message {label} schema is invalid: {exc}")
        if schema.get("additionalProperties") is not False:
            errors.append(
                f"human message {label} schema must reject additional properties"
            )
    if errors:
        return errors, 0
    contents = fixtures.get("contents")
    replay = fixtures.get("sos_replay")
    if not isinstance(contents, list) or len(contents) != 4:
        return ["messaging fixtures must contain four contents"], 0
    if not isinstance(replay, dict) or not isinstance(replay.get("events"), list):
        return ["messaging fixtures must contain an SOS replay"], 0
    content_validator = Draft202012Validator(
        content_schema, format_checker=FormatChecker()
    )
    event_validator = Draft202012Validator(event_schema, format_checker=FormatChecker())
    conforming = 0
    types: set[str] = set()
    for index, content in enumerate(contents):
        validation = sorted(
            content_validator.iter_errors(content), key=lambda error: list(error.path)
        )
        if validation:
            errors.extend(
                f"contents[{index}] schema: {error.message}" for error in validation
            )
        else:
            conforming += 1
            types.add(content["message_type"])
    if types != MESSAGE_TYPES:
        errors.append("messaging fixtures must exercise all four content types")
    for index, event in enumerate(replay["events"]):
        validation = sorted(
            event_validator.iter_errors(event), key=lambda error: list(error.path)
        )
        errors.extend(
            f"events[{index}] schema: {error.message}" for error in validation
        )
    false_attempt = replay.get("false_acceptance_attempt", {}).get("event")
    if isinstance(false_attempt, dict):
        errors.extend(
            f"false_acceptance_attempt schema: {error.message}"
            for error in event_validator.iter_errors(false_attempt)
        )
    else:
        errors.append("false acceptance attempt is required")
    if fixtures.get("evidence_level") != "simulated":
        errors.append("Open Spec messaging fixtures must remain simulated")
    return errors, conforming


def _reduce_sos(events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda row: (row["occurred_at"], row["event_id"]))
    seen_ids: set[str] = set()
    by_type: dict[str, list[str]] = {}
    projection = {
        "message_id": ordered[0]["message_id"],
        "technical_state": "not_received",
        "human_state": "not_seen",
        "operational_state": "not_accepted",
        "lifecycle_state": "active",
        "event_ids": [],
        "false_operator_acceptances": 0,
    }
    for event in ordered:
        if event["event_id"] in seen_ids:
            continue
        if event["message_id"] != projection["message_id"]:
            raise ValueError("SOS replay mixes message IDs")
        if event["verification"] != "verified":
            continue
        if any(cause not in seen_ids for cause in event["causation_event_ids"]):
            raise ValueError("SOS causation references unavailable history")
        event_type = event["event_type"]
        if event_type == "operator.accepted":
            gateway_ids = set(by_type.get("gateway.received", []))
            seen_event_ids = set(by_type.get("operator.seen", []))
            causes = set(event["causation_event_ids"])
            authorized = (
                event["actor_type"] == "operator"
                and event["actor_role"] == "distress_operator"
                and bool(gateway_ids & causes)
                and bool(seen_event_ids & causes)
            )
            if not authorized:
                projection["false_operator_acceptances"] += 1
                continue
            projection["operational_state"] = "accepted"
        elif event_type == "gateway.received":
            projection["technical_state"] = "gateway_received"
        elif event_type == "operator.seen":
            projection["human_state"] = "seen"
        elif event_type == "sos.cancel_requested":
            projection["lifecycle_state"] = "cancel_requested"
        elif event_type in {"sos.expired", "sos.failed"}:
            projection["lifecycle_state"] = event_type.removeprefix("sos.")
        seen_ids.add(event["event_id"])
        by_type.setdefault(event_type, []).append(event["event_id"])
        projection["event_ids"].append(event["event_id"])
    return projection


def _replay_summary(fixtures: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    replay = fixtures["sos_replay"]
    events = replay["events"]
    orders = []
    for offset in range(5):
        orders.append(events[offset:] + events[:offset])
        reversed_events = list(reversed(events))
        orders.append(reversed_events[offset:] + reversed_events[:offset])
    projections = [_reduce_sos(order) for order in orders]
    hashes = {canonical_hash(projection) for projection in projections}
    projection = projections[0]
    false_attempt = replay["false_acceptance_attempt"]
    false_projection = _reduce_sos([false_attempt["event"]])
    rejected = false_projection["false_operator_acceptances"]
    if false_attempt.get("expected_disposition") != "ReviewQuarantine":
        errors.append("false operator acceptance must be preserved in ReviewQuarantine")
    cases = replay.get("unverified_distress", [])
    preserved = sum(
        row.get("preserved") is True
        and row.get("destination") in {"EvidenceVault", "ReviewQuarantine"}
        for row in cases
    )
    authenticated = sum(row.get("authenticated") is True for row in cases)
    if len(hashes) != 1:
        errors.append("SOS semantic replay is not deterministic")
    if projection["false_operator_acceptances"] != 0:
        errors.append("valid SOS replay contains false operator acceptance")
    if rejected != 1:
        errors.append("false operator acceptance was not rejected")
    if preserved != len(cases) or authenticated:
        errors.append(
            "unverified distress preservation is incomplete or falsely authenticated"
        )
    return errors, {
        "replay_orders": len(orders),
        "replay_hashes": len(hashes),
        "replay_sha256": next(iter(hashes)) if hashes else None,
        "technical_state": projection["technical_state"],
        "human_state": projection["human_state"],
        "operational_state": projection["operational_state"],
        "false_operator_acceptances": projection["false_operator_acceptances"],
        "rejected_false_acceptances": rejected,
        "cancel_events_preserved": sum(
            event["event_type"] == "sos.cancel_requested" for event in events
        ),
        "unverified_distress_cases": len(cases),
        "unverified_distress_preserved": preserved,
        "unverified_distress_authenticated": authenticated,
        "silent_discards": len(cases) - preserved,
    }


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("task") != "OS-04" or value.get("lane") != "open_spec":
        errors.append("messaging residual register must belong to OS-04 open_spec")
    if not isinstance(rows, list) or len(rows) < 10:
        return [*errors, "at least ten messaging residuals are required"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        if row.get("state") not in {
            "resolved",
            "controlled",
            "planned",
            "evidence_required",
        }:
            errors.append(f"residuals[{index}] state is invalid")
        if row.get("blocks_open_spec") is not False:
            errors.append(f"residuals[{index}] cannot silently block Open Spec")
        for field in (
            "id",
            "owner",
            "risk",
            "disposition",
            "gate_or_task",
            "stop_condition",
        ):
            if not row.get(field):
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def run_open_spec_messaging_gate(
    root: Path,
    *,
    profiles_path: Path,
    content_schema_path: Path,
    event_schema_path: Path,
    fixtures_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    plan_path = root / PLAN_PATH
    policy_path = root / POLICY_PATH
    p0_receipt_path = root / P0_CRYPTO_RECEIPT_PATH
    inputs = [
        plan_path,
        policy_path,
        profiles_path,
        content_schema_path,
        event_schema_path,
        fixtures_path,
        residuals_path,
        p0_receipt_path,
    ]
    try:
        plan = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        plan = ""
        errors.append(
            f"open-spec plan unreadable: {exc.strerror or type(exc).__name__}"
        )
    normalized_plan = " ".join(plan.split())
    for marker in (
        "5 / 8",
        "OS-04 — aceptada",
        "OS-05 — aceptada",
        "OS-06 — no iniciada",
        "texto breve, estado, SOS y ubicación",
        "unverified_distress",
    ):
        if marker not in normalized_plan:
            errors.append(f"open-spec plan missing OS-04 boundary: {marker}")

    policy, policy_errors = _read_json(policy_path, "open-spec policy")
    profiles, profile_errors = _read_json(profiles_path, "messaging profiles")
    content_schema, content_errors = _read_json(
        content_schema_path, "message content schema"
    )
    event_schema, event_errors = _read_json(
        event_schema_path, "message lifecycle schema"
    )
    fixtures, fixture_errors = _read_json(fixtures_path, "messaging fixtures")
    residuals, residual_errors = _read_json(residuals_path, "messaging residuals")
    p0_receipt, p0_errors = _read_json(p0_receipt_path, "P0 crypto receipt")
    errors.extend(
        policy_errors
        + profile_errors
        + content_errors
        + event_errors
        + fixture_errors
        + residual_errors
        + p0_errors
    )
    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    conforming = 0
    replay_summary: dict[str, Any] = {}
    if content_schema is not None and event_schema is not None and fixtures is not None:
        schema_errors, conforming = _validate_schemas_and_fixtures(
            content_schema, event_schema, fixtures
        )
        errors.extend(schema_errors)
        if not schema_errors:
            replay_errors, replay_summary = _replay_summary(fixtures)
            errors.extend(replay_errors)
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))
    if p0_receipt is not None:
        if p0_receipt.get("result") != "passed" or p0_receipt.get("dirty") is not False:
            errors.append(
                "P0 application cryptography evidence must be clean and passed"
            )

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 5,
            "spec_tasks_total": 8,
            "message_profiles": (
                len(profiles.get("message_profiles", [])) if profiles else 0
            ),
            "conforming_contents": conforming,
            **replay_summary,
            "physical_delivery_blocks_publication": False,
            "next_task": "OS-06",
            "next_task_started": False,
        },
        inputs,
    )
