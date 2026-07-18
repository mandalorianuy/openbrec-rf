from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PLAN_PATH = Path("docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md")
POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path(
    "specs/openbrec/1.0.0-draft.1/reference-capability-profiles.json"
)
CLAIM_SCHEMA_PATH = Path("schemas/open-spec/evidence-claim.schema.json")
DISPOSITION_PATH = Path("docs/governance/p1a-01-spec-disposition.json")
RESIDUALS_PATH = Path("docs/governance/open-spec-residuals.json")

CATEGORIES = {
    "lorawan_gateway",
    "lorawan_endpoint",
    "meshtastic_node",
    "meshcore_node",
    "rnode",
    "offline_terminal",
    "trimodal_beacon",
    "energy_storage",
    "wired_cell_gateway",
}
EVIDENCE_LEVELS = [
    "unverified",
    "specified",
    "simulated",
    "lab_validated",
    "field_validated",
]


def _read_json(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"{label} unreadable: {path.name}: {exc.strerror or type(exc).__name__}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label} invalid JSON: {path.name}: line {exc.lineno} column {exc.colno}"]
    if not isinstance(value, dict):
        return None, [f"{label} must be an object"]
    return value, []


def _validate_policy(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("governance_version") != "1.0.0":
        errors.append("governance_version must be 1.0.0")
    if value.get("main_lane") != "open_spec":
        errors.append("main_lane must be open_spec")
    if value.get("progress") != {
        "accepted_tasks": 1,
        "total_tasks": 8,
        "percent": 12.5,
    }:
        errors.append("open-spec progress must be 1 / 8")
    publication = value.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication policy is required")
    else:
        if publication.get("requires_owned_hardware") is not False:
            errors.append("owned hardware cannot block open-spec publication")
        if publication.get("requires_physical_evidence") is not False:
            errors.append("physical evidence cannot block open-spec publication")
        if publication.get("requires_normative_contracts") is not True:
            errors.append("normative contracts must gate open-spec publication")
        if publication.get("requires_open_alternatives") is not True:
            errors.append("open alternatives must gate open-spec publication")
    physical_claims = value.get("physical_claims")
    if not isinstance(physical_claims, dict) or physical_claims.get(
        "require_evidence_pack"
    ) is not True:
        errors.append("physical claims must require an evidence pack")
    lane = value.get("physical_validation_lane")
    if not isinstance(lane, dict):
        errors.append("physical_validation_lane is required")
    else:
        if lane.get("optional") is not True or lane.get("blocks_open_spec") is not False:
            errors.append("physical validation lane must be optional and nonblocking")
        if lane.get("progress", {}).get("accepted_tasks") != 0:
            errors.append("physical validation lane must remain 0 / 8")
    if value.get("evidence_levels") != EVIDENCE_LEVELS:
        errors.append("evidence levels are incomplete or out of order")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or [task.get("id") for task in tasks if isinstance(task, dict)] != [
        f"OS-{index:02d}" for index in range(1, 9)
    ]:
        errors.append("tasks must cover OS-01 through OS-08 in order")
    elif tasks[0].get("status") != "accepted" or any(
        task.get("status") != "not_started" for task in tasks[1:]
    ):
        errors.append("only OS-01 may be accepted")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("profile_set_version must be 1.0.0-draft.1")
    profiles = value.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 9:
        return [*errors, "reference profiles must contain nine roles"]
    categories = [profile.get("category") for profile in profiles if isinstance(profile, dict)]
    identifiers = [profile.get("profile_id") for profile in profiles if isinstance(profile, dict)]
    if set(categories) != CATEGORIES or len(categories) != len(set(categories)):
        errors.append("reference profiles must cover nine categories exactly once")
    if len(identifiers) != len(set(identifiers)) or any(not identifier for identifier in identifiers):
        errors.append("reference profile IDs must be unique")
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profiles[{index}] must be an object")
            continue
        if profile.get("hardware_required_for_spec") is not False:
            errors.append(f"profiles[{index}] cannot require hardware for the spec")
        if profile.get("alternatives_allowed") is not True:
            errors.append(f"profiles[{index}] must allow alternatives")
        if profile.get("default_evidence_level") != "unverified":
            errors.append(f"profiles[{index}] must default to unverified")
        for field in ("minimum_capabilities", "reference_candidates", "acceptance_criteria"):
            if not isinstance(profile.get(field), list) or not profile[field]:
                errors.append(f"profiles[{index}].{field} must not be empty")
    return errors


def _validate_claim_schema(value: dict[str, Any]) -> list[str]:
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        return [f"evidence claim schema is invalid: {exc}"]
    errors: list[str] = []
    levels = value.get("properties", {}).get("evidence_level", {}).get("enum")
    if levels != EVIDENCE_LEVELS:
        errors.append("evidence claim schema levels do not match governance")
    if "physical_evidence" not in value.get("properties", {}):
        errors.append("evidence claim schema must define physical_evidence")
    if value.get("additionalProperties") is not False:
        errors.append("evidence claim schema must reject additional properties")
    return errors


def _validate_disposition(root: Path, value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("decision") != "preserved_as_optional_validation_lane":
        errors.append("P1a disposition must preserve the optional validation lane")
    if value.get("blocks_open_spec") is not False:
        errors.append("P1a disposition cannot block open spec")
    if value.get("physical_validation_status") != "blocked_external_evidence":
        errors.append("P1a physical status must remain explicit")
    paths = value.get("preserved_artifacts")
    if not isinstance(paths, list) or not paths:
        errors.append("P1a disposition must list preserved artifacts")
    else:
        for path in paths:
            if not isinstance(path, str) or not (root / path).is_file():
                errors.append(f"preserved P1a artifact missing: {path}")
    return errors


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("lane") != "open_spec":
        errors.append("residual lane must be open_spec")
    if not isinstance(rows, list) or len(rows) < 3:
        return [*errors, "at least three open-spec residuals are required"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        if row.get("state") not in {"controlled", "planned"}:
            errors.append(f"residuals[{index}] state is invalid")
        if row.get("blocks_publication") is not False:
            errors.append(f"residuals[{index}] cannot silently block publication")
        for field in ("id", "owner", "risk", "gate_or_task", "stop_condition"):
            if not row.get(field):
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def run_open_spec_gate(
    root: Path,
    *,
    policy_path: Path,
    profiles_path: Path,
    claim_schema_path: Path,
    disposition_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    inputs = [
        root / PLAN_PATH,
        policy_path,
        profiles_path,
        claim_schema_path,
        disposition_path,
        root / RESIDUALS_PATH,
    ]
    try:
        plan = (root / PLAN_PATH).read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"open-spec plan unreadable: {exc.strerror or type(exc).__name__}")
        plan = ""
    for marker in (
        "Autoridad principal: Open Spec",
        "1 / 8",
        "OS-01 — aceptada",
        "OS-02 — no iniciada",
        "P1a es un carril opcional",
    ):
        if marker not in plan:
            errors.append(f"open-spec plan missing boundary: {marker}")

    policy, policy_errors = _read_json(policy_path, "open-spec policy")
    profiles, profile_errors = _read_json(profiles_path, "reference profiles")
    claim_schema, schema_errors = _read_json(claim_schema_path, "evidence claim schema")
    disposition, disposition_errors = _read_json(disposition_path, "P1a disposition")
    residuals, residual_errors = _read_json(root / RESIDUALS_PATH, "open-spec residuals")
    errors.extend(policy_errors + profile_errors + schema_errors + disposition_errors + residual_errors)
    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    if claim_schema is not None:
        errors.extend(_validate_claim_schema(claim_schema))
    if disposition is not None:
        errors.extend(_validate_disposition(root, disposition))
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 1,
            "spec_tasks_total": 8,
            "reference_profiles": len(profiles.get("profiles", [])) if profiles else 0,
            "physical_validation_tasks_accepted": 0,
            "physical_evidence_blocks_publication": False,
            "next_task": "OS-02",
            "next_task_started": False,
        },
        inputs,
    )
