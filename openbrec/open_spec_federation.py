from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash

POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path("specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json")
PEER_SCHEMA_PATH = Path("schemas/open-spec/federation-peer-agreement.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/federation/conformance-examples.json")
RESIDUALS_PATH = Path("docs/governance/open-spec-federation-residuals.json")

LEVELS = ["IncidentFederation", "OperationalArea", "ResponseCell", "Deployment", "Site"]
HUB_DENIED_CAPABILITIES = {
    "holds_cell_keys",
    "decrypts_local_content",
    "creates_operator_acceptance",
    "orders_radio_tx",
    "overwrites_source_logs",
}


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
        "accepted_tasks": 6,
        "total_tasks": 8,
        "percent": 75.0,
    }:
        errors.append("open-spec progress must be 6 / 8")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        return [*errors, "open-spec policy must contain eight tasks"]
    if [task.get("status") for task in tasks[:6]] != ["accepted"] * 6:
        errors.append("OS-01 through OS-06 must be accepted")
    if any(task.get("status") != "not_started" for task in tasks[6:]):
        errors.append("OS-07 and OS-08 must remain not_started")
    if tasks[5].get("gate") != "open-spec-federation":
        errors.append("OS-06 must use the open-spec-federation gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("federation profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open federation boundary is required")
    else:
        for field in (
            "central_service_in_critical_path",
            "cloud_in_critical_path",
            "single_incident_wide_lora_mesh",
            "owned_hardware_required",
            "physical_scale_blocks_spec",
        ):
            if boundary.get(field) is not False:
                errors.append(
                    f"{field} must remain false; no central critical path is allowed"
                )
        if boundary.get("local_networks_per_response_cell") is not True:
            errors.append("ResponseCells must use autonomous local networks")

    hierarchy = value.get("hierarchy")
    if (
        not isinstance(hierarchy, list)
        or [row.get("level") for row in hierarchy] != LEVELS
    ):
        errors.append("hierarchy must define the five normative levels in order")
    else:
        for index, row in enumerate(hierarchy):
            for field in (
                "can_operate_without_parent",
                "local_event_log",
                "local_trust_cache",
                "local_policy_cache",
                "distress_preservation",
            ):
                if row.get(field) is not True:
                    errors.append(f"hierarchy[{index}].{field} must be true")
    if value.get("minimum_federable_unit") != "ResponseCell":
        errors.append("ResponseCell must be the minimum federable unit")

    isolation = value.get("team_network_isolation")
    if not isinstance(isolation, dict):
        errors.append("team and network isolation policy is required")
    else:
        for field in ("identity_namespace", "keys", "event_log", "local_broker"):
            if isolation.get(field) != "separate_per_response_cell":
                errors.append(
                    f"team_network_isolation.{field} must be separate per cell"
                )
        if isolation.get("cross_cell_exchange") != "explicit_peer_agreement_only":
            errors.append("cross-cell exchange requires an explicit peer agreement")
        for field in (
            "shared_incident_key_allowed",
            "shared_incident_mqtt_root_allowed",
        ):
            if isolation.get(field) is not False:
                errors.append(f"team_network_isolation.{field} must remain false")

    hubs = value.get("coordination_hubs")
    if not isinstance(hubs, dict):
        errors.append("coordination hub policy is required")
    else:
        if hubs.get("required") is not False:
            errors.append("a coordination hub cannot be required")
        if hubs.get("minimum_redundancy_when_deployed") != 2:
            errors.append("deployed hubs require at least two redundant instances")
        if hubs.get("backhaul_separate_from_local_lora") is not True:
            errors.append("hub backhaul must be separate from local LoRa")
        for field in HUB_DENIED_CAPABILITIES:
            if hubs.get(field) is not False:
                errors.append(f"hub cannot gain authority: {field} must be false")

    trust = value.get("stale_trust_policy")
    if not isinstance(trust, dict):
        errors.append("stale trust policy is required")
    else:
        for field in (
            "local_operation_continues",
            "distress_preserved",
            "existing_local_log_remains_authoritative",
        ):
            if trust.get(field) is not True:
                errors.append(f"stale trust must preserve {field}")
        if set(trust.get("restricted_actions", [])) != {
            "new_sensitive_federation",
            "new_enrollment",
            "remote_policy_change",
        }:
            errors.append(
                "stale trust must restrict federation, enrollment and remote policy"
            )

    reconciliation = value.get("reconciliation_policy")
    if not isinstance(reconciliation, dict):
        errors.append("reconciliation policy is required")
    else:
        for field in (
            "append_only",
            "deterministic",
            "conflicts_visible",
            "human_resolution_pending",
        ):
            if reconciliation.get(field) is not True:
                errors.append(f"reconciliation invariant missing: {field}")
        for field in ("last_write_wins", "source_log_overwrite", "silent_loss"):
            if reconciliation.get(field) is not False:
                errors.append(f"reconciliation must prohibit {field}")

    scale = value.get("scale_reference")
    expected = {
        "sites": 50000,
        "response_cells": 60,
        "operational_areas": 5,
        "coordination_hubs": 2,
    }
    if not isinstance(scale, dict) or any(
        scale.get(key) != number for key, number in expected.items()
    ):
        errors.append("scale reference must retain the governed 50k topology")
    elif (
        scale.get("evidence_scope") != "deterministic_simulation_correctness_only"
        or scale.get("capacity_claim") is not False
        or scale.get("field_readiness_claim") is not False
    ):
        errors.append(
            "50k evidence must not become a capacity or field-readiness claim"
        )
    return errors


def _schema_validator(
    value: dict[str, Any],
) -> tuple[Draft202012Validator | None, list[str]]:
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        return None, [f"peer agreement schema is not valid Draft 2020-12: {exc}"]
    if value.get("additionalProperties") is not False:
        return None, ["peer agreement schema must reject additional properties"]
    return Draft202012Validator(value, format_checker=FormatChecker()), []


def _validate_fixtures(
    schema: dict[str, Any], fixtures: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    validator, schema_errors = _schema_validator(schema)
    errors.extend(schema_errors)
    agreements = fixtures.get("peer_agreements")
    if not isinstance(agreements, list) or len(agreements) < 2:
        errors.append("fixtures require at least two peer agreements")
        agreements = []
    elif validator is not None:
        for index, agreement in enumerate(agreements):
            issues = sorted(
                validator.iter_errors(agreement), key=lambda item: list(item.path)
            )
            errors.extend(
                f"peer_agreements[{index}]: {issue.message}" for issue in issues
            )
            if agreement.get("authority_escalation") is not False:
                errors.append(f"peer_agreements[{index}] cannot escalate authority")
            if agreement.get("raw_payload_allowed") is not False:
                errors.append(f"peer_agreements[{index}] cannot expose raw payloads")

    partitions = fixtures.get("partition_cases")
    if (
        not isinstance(partitions, list)
        or [row.get("isolated_level") for row in partitions] != LEVELS
    ):
        errors.append("partition fixtures must cover all five hierarchy levels")
        partitions = []
    else:
        for index, row in enumerate(partitions):
            if row.get("parent_available") is not False:
                errors.append(f"partition_cases[{index}] must isolate its parent")
            if row.get("local_operations_attempted") != row.get(
                "local_operations_executed"
            ):
                errors.append(f"partition_cases[{index}] blocked local operations")
            if row.get("local_operations_blocked_by_superior") != 0:
                errors.append(f"partition_cases[{index}] depends on a superior")
            if row.get("distress_preserved") is not True:
                errors.append(f"partition_cases[{index}] lost distress")

    hostile = fixtures.get("hostile_hub_cases")
    if not isinstance(hostile, list) or len(hostile) < 5:
        errors.append("fixtures require at least five hostile hub cases")
        hostile = []
    permitted_outcomes = {"rejected", "quarantined_distress_preserved"}
    for index, row in enumerate(hostile):
        if row.get("outcome") not in permitted_outcomes:
            errors.append(f"hostile_hub_cases[{index}] gained authority")

    summary = {
        "peer_agreements": len(agreements),
        "partition_cases": len(partitions),
        "autonomous_levels": sum(
            row.get("local_operations_attempted")
            == row.get("local_operations_executed")
            and row.get("local_operations_blocked_by_superior") == 0
            for row in partitions
        ),
        "local_operations_executed": sum(
            row.get("local_operations_executed", 0) for row in partitions
        ),
        "local_operations_blocked_by_superior": sum(
            row.get("local_operations_blocked_by_superior", 0) for row in partitions
        ),
        "hostile_hub_cases": len(hostile),
        "false_operator_acceptances": sum(
            row.get("action") == "create_operator_acceptance"
            and row.get("outcome") != "rejected"
            for row in hostile
        ),
        "hub_decryptions": sum(
            row.get("action") == "decrypt_local_content"
            and row.get("outcome") != "rejected"
            for row in hostile
        ),
        "hub_tx_orders": sum(
            row.get("action") == "order_radio_tx" and row.get("outcome") != "rejected"
            for row in hostile
        ),
        "forged_cell_events_accepted": sum(
            row.get("action") == "forge_cell_event" and row.get("outcome") != "rejected"
            for row in hostile
        ),
        "unverified_distress_preserved": sum(
            row.get("outcome") == "quarantined_distress_preserved" for row in hostile
        ),
    }
    return errors, summary


def _reconcile(
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    by_identity: dict[tuple[str, str], list[dict[str, Any]]] = {}
    exact_seen: set[str] = set()
    duplicates = 0
    for event in events:
        encoded_hash = canonical_hash(event)
        if encoded_hash in exact_seen:
            duplicates += 1
            continue
        exact_seen.add(encoded_hash)
        by_identity.setdefault((event["source_cell"], event["event_id"]), []).append(
            event
        )

    records: list[dict[str, Any]] = []
    identity_conflicts = 0
    for identity, variants in sorted(by_identity.items()):
        hashes = sorted(canonical_hash(item) for item in variants)
        conflict = len(hashes) > 1
        identity_conflicts += int(conflict)
        records.append(
            {"identity": list(identity), "variant_hashes": hashes, "conflict": conflict}
        )

    semantic: dict[str, set[str]] = {}
    for event in events:
        group = event.get("conflict_group")
        if group:
            semantic.setdefault(group, set()).add(canonical_hash(event.get("payload")))
    semantic_conflicts = sum(len(values) > 1 for values in semantic.values())
    return records, {
        "duplicates_deduplicated": duplicates,
        "visible_conflicts": identity_conflicts + semantic_conflicts,
    }


def _replay_summary(fixtures: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    events = fixtures.get("reconciliation_events")
    if not isinstance(events, list) or len(events) < 6:
        return ["fixtures require reconciliation events"], {}
    hashes: set[str] = set()
    final_stats: dict[str, int] = {}
    projection: list[dict[str, Any]] = []
    for offset in range(10):
        ordered = events[offset % len(events) :] + events[: offset % len(events)]
        if offset % 2:
            ordered = list(reversed(ordered))
        projection, final_stats = _reconcile(ordered)
        hashes.add(canonical_hash(projection))
    errors: list[str] = []
    if len(hashes) != 1:
        errors.append("federation reconciliation is not deterministic")
    if final_stats.get("visible_conflicts", 0) < 3:
        errors.append("reconciliation fixtures must expose at least three conflicts")
    return errors, {
        "reconciliation_inputs": len(events),
        "replay_orders": 10,
        "replay_hashes": len(hashes),
        "replay_sha256": canonical_hash(projection),
        **final_stats,
        "silent_losses": 0,
        "source_log_overwrites": 0,
        "last_write_wins_resolutions": 0,
    }


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("lane") != "open_spec" or value.get("task") != "OS-06":
        errors.append("federation residual register must belong to open-spec OS-06")
    if not isinstance(rows, list) or len(rows) < 10:
        return [*errors, "at least ten federation residuals are required"]
    for index, row in enumerate(rows):
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


def run_open_spec_federation_gate(
    root: Path,
    *,
    profiles_path: Path,
    peer_schema_path: Path,
    fixtures_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    policy_path = root / POLICY_PATH
    inputs = [
        policy_path,
        profiles_path,
        peer_schema_path,
        fixtures_path,
        residuals_path,
        root / "openbrec/open_spec_federation.py",
    ]
    policy, errors = _read_json(policy_path, "open-spec policy")
    profiles, read_errors = _read_json(profiles_path, "federation profiles")
    errors.extend(read_errors)
    schema, read_errors = _read_json(peer_schema_path, "peer agreement schema")
    errors.extend(read_errors)
    fixtures, read_errors = _read_json(fixtures_path, "federation fixtures")
    errors.extend(read_errors)
    residuals, read_errors = _read_json(residuals_path, "federation residuals")
    errors.extend(read_errors)

    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    fixture_summary: dict[str, Any] = {}
    replay_summary: dict[str, Any] = {}
    if schema is not None and fixtures is not None:
        fixture_errors, fixture_summary = _validate_fixtures(schema, fixtures)
        errors.extend(fixture_errors)
        replay_errors, replay_summary = _replay_summary(fixtures)
        errors.extend(replay_errors)
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 6,
            "spec_tasks_total": 8,
            "hierarchy_levels": len(profiles.get("hierarchy", [])) if profiles else 0,
            **fixture_summary,
            **replay_summary,
            "scale_reference_sites": (
                profiles.get("scale_reference", {}).get("sites") if profiles else None
            ),
            "scale_evidence_scope": (
                profiles.get("scale_reference", {}).get("evidence_scope")
                if profiles
                else None
            ),
            "physical_scale_blocks_publication": False,
            "next_task": "OS-07",
            "next_task_started": False,
        },
        inputs,
    )
