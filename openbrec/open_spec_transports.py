from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PLAN_PATH = Path("docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md")
POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path(
    "specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json"
)
DECISION_SCHEMA_PATH = Path("schemas/open-spec/transport-decision.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/transports/decision-examples.json")
SOURCE_REVIEW_PATH = Path(
    "docs/research/2026-07-18-multi-bearer-source-review.json"
)
RESIDUALS_PATH = Path("docs/governance/open-spec-transport-residuals.json")

BEARERS = {
    "lorawan_private",
    "meshtastic",
    "meshcore",
    "reticulum_rnode",
    "carry_bundle",
}
REGULATORY_MODES = {
    "receive_only",
    "conducted_only",
    "jurisdiction_validated",
    "emergency_assumed_risk",
}
OVERLAY_TRUE_FIELDS = (
    "signed_integrity",
    "stable_message_id_across_bearers",
    "deduplicate_before_semantic_acceptance",
    "anti_loop_required",
    "priority_assigned_before_bearer",
    "per_path_receipts",
    "ttl_and_expiry_required",
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
        "accepted_tasks": 3,
        "total_tasks": 8,
        "percent": 37.5,
    }:
        errors.append("open-spec progress must be 3 / 8")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        return [*errors, "open-spec policy must contain eight tasks"]
    if [task.get("status") for task in tasks[:3]] != ["accepted"] * 3:
        errors.append("OS-01 through OS-03 must be accepted")
    if any(task.get("status") != "not_started" for task in tasks[3:]):
        errors.append("OS-04 through OS-08 must remain not_started")
    if tasks[2].get("gate") != "open-spec-transports":
        errors.append("OS-03 must use the open-spec-transports gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("transport profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open transport boundary is required")
    else:
        if boundary.get("requires_single_bearer") is not False:
            errors.append("a single bearer cannot be mandatory")
        if boundary.get("requires_owned_hardware") is not False:
            errors.append("owned hardware cannot gate transport profiles")
        if boundary.get("physical_rf_validation_blocks_spec") is not False:
            errors.append("physical RF validation cannot block the transport specification")
        if boundary.get("protocols_are_replaceable_adapters") is not True:
            errors.append("transport protocols must remain replaceable adapters")

    selection = value.get("selection_policy")
    if not isinstance(selection, dict):
        errors.append("transport selection policy is required")
    else:
        if selection.get("global_winner") is not None:
            errors.append("a universal transport winner is prohibited")
        if selection.get("select_per_mission_and_path") is not True:
            errors.append("transport selection must be per mission and path")
        if len(selection.get("selection_dimensions", [])) < 10:
            errors.append("transport selection dimensions are incomplete")

    overlay = value.get("application_overlay")
    if not isinstance(overlay, dict):
        errors.append("bearer-independent application overlay is required")
    else:
        if overlay.get("envelope_authority") != "openbrec_application":
            errors.append("OpenBREC application must own the envelope")
        for field in OVERLAY_TRUE_FIELDS:
            if overlay.get(field) is not True:
                errors.append(f"application overlay invariant missing: {field}")
        for field in (
            "raw_frame_bridge_allowed",
            "transport_ack_is_semantic_delivery",
            "transport_ack_is_operator_acceptance",
            "bearer_identity_is_actor_identity",
        ):
            if overlay.get(field) is not False:
                errors.append(f"application overlay must keep {field} false")

    modes = value.get("regulatory_modes")
    if not isinstance(modes, list) or {
        row.get("mode") for row in modes if isinstance(row, dict)
    } != REGULATORY_MODES:
        errors.append("all four regulatory decision modes are required")

    profiles = value.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 5:
        return [*errors, "transport profiles must define five open bearers"]
    if {row.get("bearer") for row in profiles if isinstance(row, dict)} != BEARERS:
        errors.append("transport profiles must cover all five bearers exactly")
    for index, row in enumerate(profiles):
        if not isinstance(row, dict):
            errors.append(f"profiles[{index}] must be an object")
            continue
        if row.get("required_for_spec") is not False:
            errors.append(f"profiles[{index}] cannot be required for the spec")
        if row.get("alternatives_allowed") is not True:
            errors.append(f"profiles[{index}] must allow alternatives")
        if row.get("trust_boundary") != "untrusted_transport":
            errors.append(f"profiles[{index}] must be an untrusted transport")
        for field in (
            "preferred_planes",
            "selection_dimensions",
            "failure_modes",
            "protocol_constraints",
        ):
            if not row.get(field):
                errors.append(f"profiles[{index}].{field} must not be empty")
    return errors


def _validate_schema_fixtures(
    schema: dict[str, Any], fixtures: dict[str, Any]
) -> tuple[list[str], int]:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return [f"transport decision schema is invalid: {exc}"], 0
    errors: list[str] = []
    if schema.get("additionalProperties") is not False:
        errors.append("transport decision schema must reject additional properties")
    examples = fixtures.get("examples")
    if not isinstance(examples, list) or len(examples) != 5:
        return [*errors, "transport fixtures must contain five examples"], 0
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    conforming = 0
    bearers: set[str] = set()
    modes: set[str] = set()
    for index, example in enumerate(examples):
        if not isinstance(example, dict):
            errors.append(f"examples[{index}] must be an object")
            continue
        validation_errors = sorted(
            validator.iter_errors(example), key=lambda error: list(error.path)
        )
        if validation_errors:
            errors.extend(
                f"examples[{index}] schema: {error.message}"
                for error in validation_errors
            )
            continue
        conforming += 1
        bearers.add(example["selected_bearer"])
        modes.add(example["regulatory_mode"])
        if example["evidence_level"] not in {"specified", "simulated"}:
            errors.append(f"examples[{index}] cannot claim physical evidence")
        if example["regulatory_mode"] == "emergency_assumed_risk":
            decision = example["assumed_risk_decision"]
            starts = datetime.fromisoformat(decision["starts_at"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(decision["expires_at"].replace("Z", "+00:00"))
            if expires <= starts:
                errors.append(f"examples[{index}] assumed-risk decision must expire after it starts")
    if bearers != BEARERS:
        errors.append("transport fixtures must exercise every bearer")
    if modes != REGULATORY_MODES:
        errors.append("transport fixtures must exercise all regulatory modes")
    return errors, conforming


def _validate_source_review(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("reviewed_at") != "2026-07-18":
        errors.append("transport source review date must be 2026-07-18")
    if value.get("version_policy") != "pin_per_implementation_and_rereview":
        errors.append("transport sources must be re-reviewed per implementation pin")
    sources = value.get("sources")
    if not isinstance(sources, list) or len(sources) < 7:
        return [*errors, "at least seven primary transport source records are required"]
    technologies = {
        row.get("technology") for row in sources if isinstance(row, dict)
    }
    if technologies != {"meshtastic", "meshcore", "reticulum", "lorawan", "carry_bundle"}:
        errors.append("source review must cover all five transport families")
    for index, row in enumerate(sources):
        if not isinstance(row, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        if not str(row.get("official_url", "")).startswith("https://"):
            errors.append(f"sources[{index}] must use an official HTTPS source")
        if not row.get("observations") or not row.get("implementation_action"):
            errors.append(f"sources[{index}] must include observations and action")
        if row.get("proves_field_performance") is not False:
            errors.append(f"sources[{index}] cannot prove field performance")
    return errors


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("task") != "OS-03" or value.get("lane") != "open_spec":
        errors.append("transport residual register must belong to OS-03 open_spec")
    if not isinstance(rows, list) or len(rows) < 9:
        return [*errors, "at least nine transport residuals are required"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        if row.get("state") not in {
            "resolved", "controlled", "planned", "evidence_required"
        }:
            errors.append(f"residuals[{index}] state is invalid")
        if row.get("blocks_open_spec") is not False:
            errors.append(f"residuals[{index}] cannot silently block Open Spec")
        for field in (
            "id", "owner", "risk", "disposition", "gate_or_task", "stop_condition"
        ):
            if not row.get(field):
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def run_open_spec_transport_gate(
    root: Path,
    *,
    profiles_path: Path,
    decision_schema_path: Path,
    fixtures_path: Path,
    source_review_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    plan_path = root / PLAN_PATH
    policy_path = root / POLICY_PATH
    inputs = [
        plan_path, policy_path, profiles_path, decision_schema_path,
        fixtures_path, source_review_path, residuals_path,
    ]
    try:
        plan = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        plan = ""
        errors.append(f"open-spec plan unreadable: {exc.strerror or type(exc).__name__}")
    normalized_plan = " ".join(plan.split())
    for marker in (
        "3 / 8", "OS-03 — aceptada", "OS-04 — no iniciada",
        "sin ganador universal", "emergency_assumed_risk",
    ):
        if marker not in normalized_plan:
            errors.append(f"open-spec plan missing OS-03 boundary: {marker}")

    policy, policy_errors = _read_json(policy_path, "open-spec policy")
    profiles, profile_errors = _read_json(profiles_path, "transport profiles")
    schema, schema_errors = _read_json(decision_schema_path, "transport decision schema")
    fixtures, fixture_errors = _read_json(fixtures_path, "transport fixtures")
    source_review, source_errors = _read_json(source_review_path, "transport source review")
    residuals, residual_errors = _read_json(residuals_path, "transport residuals")
    errors.extend(
        policy_errors + profile_errors + schema_errors + fixture_errors
        + source_errors + residual_errors
    )
    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    conforming = 0
    if schema is not None and fixtures is not None:
        fixture_errors, conforming = _validate_schema_fixtures(schema, fixtures)
        errors.extend(fixture_errors)
    if source_review is not None:
        errors.extend(_validate_source_review(source_review))
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 3,
            "spec_tasks_total": 8,
            "bearer_profiles": len(profiles.get("profiles", [])) if profiles else 0,
            "conforming_examples": conforming,
            "source_records": len(source_review.get("sources", [])) if source_review else 0,
            "global_winner_selected": bool(
                profiles and profiles.get("selection_policy", {}).get("global_winner")
            ),
            "physical_rf_validation_blocks_publication": False,
            "next_task": "OS-04",
            "next_task_started": False,
        },
        inputs,
    )
