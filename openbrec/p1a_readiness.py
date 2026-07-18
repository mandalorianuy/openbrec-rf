from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PLAN_PATH = Path(
    "docs/superpowers/plans/2026-07-17-openbrec-p1a-bench-conducted-plan.md"
)
POLICY_PATH = Path("config/p1a/authorization-policy.json")
SCHEMA_PATH = Path("schemas/p1a/capability-manifest.schema.json")
RESIDUALS_PATH = Path("docs/governance/p1a-residuals.json")
SHORTLIST_PATH = Path("docs/governance/p1a-hardware-shortlist.json")

TASKS = {f"P1a-{index:02d}" for index in range(1, 9)}
DENIED_ACTIONS = {
    "purchase",
    "loan",
    "hardware_use",
    "conducted_test",
    "human_study",
    "real_capture",
}
REQUIRED_MANIFEST_FIELDS = {
    "asset_id",
    "category",
    "manufacturer",
    "model",
    "sku",
    "hardware_revision",
    "custody",
    "physical_inspection",
    "support_status",
}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"artifact unreadable {path}: {exc}"]
    if not isinstance(value, dict):
        return None, [f"artifact must be a JSON object: {path}"]
    return value, []


def validate_policy(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("policy_version") != "1.0.0":
        errors.append("policy_version must be 1.0.0")
    if value.get("phase") != "P1a":
        errors.append("phase must be P1a")
    if value.get("authority_scope") != "repository_readiness_only":
        errors.append("authority_scope must remain repository_readiness_only")
    if value.get("automatic_purchase") is not False:
        errors.append("automatic_purchase must be false")
    if value.get("progress") != {
        "accepted_tasks": 0,
        "total_tasks": 8,
        "percent": 0.0,
    }:
        errors.append("readiness progress must remain 0 / 8")
    tasks = value.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
    else:
        task_ids = {task.get("id") for task in tasks if isinstance(task, dict)}
        if task_ids != TASKS or len(tasks) != len(task_ids):
            errors.append("tasks must cover P1a-01 through P1a-08 exactly once")
        for index, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"tasks[{index}] must be an object")
                continue
            if task.get("status") != "not_started":
                errors.append(f"tasks[{index}] must remain not_started")
            for field in ("owner", "depends_on", "evidence_dir"):
                if not task.get(field):
                    errors.append(f"tasks[{index}].{field} is required")
    actions = value.get("actions")
    if not isinstance(actions, dict):
        return [*errors, "actions must be an object"]
    for action in sorted(DENIED_ACTIONS):
        record = actions.get(action)
        if not isinstance(record, dict):
            errors.append(f"{action} policy is required")
            continue
        if record.get("state") != "not_authorized":
            errors.append(f"{action} must remain not_authorized")
        if record.get("authorization_required") is not True:
            errors.append(f"{action} must require authorization")
        evidence = record.get("required_evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{action} required_evidence must not be empty")
    radiated = actions.get("radiated_tx")
    if not isinstance(radiated, dict) or radiated.get("state") != "prohibited_in_p1a":
        errors.append("radiated_tx must remain prohibited_in_p1a")
    return errors


def validate_manifest_schema(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:  # jsonschema exposes several schema exception types
        errors.append(f"capability manifest schema is invalid: {exc}")
        return errors
    required = value.get("required")
    if not isinstance(required, list) or not REQUIRED_MANIFEST_FIELDS.issubset(required):
        errors.append("capability manifest is missing exact identity/custody fields")
    support = value.get("properties", {}).get("support_status", {})
    if support.get("enum") != ["unverified"]:
        errors.append("capability manifest support_status must only allow unverified")
    if value.get("additionalProperties") is not False:
        errors.append("capability manifest must reject additional properties")
    return errors


def validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("register_version") != "1.0.0":
        errors.append("residual register_version must be 1.0.0")
    if not isinstance(rows, list) or len(rows) < 8:
        return [*errors, "at least eight readiness residuals are required"]
    identifiers: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            errors.append(f"residuals[{index}] must have a unique id")
        else:
            identifiers.add(identifier)
        if row.get("state") not in {"controlled", "planned", "blocked"}:
            errors.append(f"residuals[{index}] has invalid state")
        for field in ("owner", "risk", "gate_or_task", "stop_condition"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def validate_shortlist(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    categories = value.get("categories")
    if value.get("purchase_authorized") is not False:
        errors.append("shortlist purchase_authorized must remain false")
    if not isinstance(categories, list) or len(categories) != 9:
        return [*errors, "shortlist must preserve nine categories"]
    for index, category in enumerate(categories):
        candidates = category.get("candidates") if isinstance(category, dict) else None
        if not isinstance(candidates, list) or len(candidates) != 1:
            errors.append(f"shortlist category {index} must have exactly one candidate")
            continue
        candidate = candidates[0]
        if candidate.get("support_status") != "unverified":
            errors.append(f"shortlist category {index} must remain unverified")
        if candidate.get("disposition") != "shortlisted_no_purchase":
            errors.append(f"shortlist category {index} must prohibit purchase")
    return errors


def run_readiness_gate(
    root: Path,
    *,
    policy_path: Path,
    schema_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    inputs = [root / PLAN_PATH, policy_path, schema_path, residuals_path, root / SHORTLIST_PATH]
    errors: list[str] = []
    try:
        plan = (root / PLAN_PATH).read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"plan unreadable: {exc}")
        plan = ""
    for marker in (
        "Estado: aprobado para secuenciación",
        "0 / 8",
        "P1a-01 no iniciada",
        "compra/préstamo no autorizado",
        "TX radiado prohibido",
    ):
        if marker not in plan:
            errors.append(f"plan missing required boundary: {marker}")

    policy, policy_errors = _read_json(policy_path)
    schema, schema_errors = _read_json(schema_path)
    residuals, residual_errors = _read_json(residuals_path)
    shortlist, shortlist_errors = _read_json(root / SHORTLIST_PATH)
    errors.extend(policy_errors + schema_errors + residual_errors + shortlist_errors)
    if policy is not None:
        errors.extend(validate_policy(policy))
    if schema is not None:
        errors.extend(validate_manifest_schema(schema))
    if residuals is not None:
        errors.extend(validate_residuals(residuals))
    if shortlist is not None:
        errors.extend(validate_shortlist(shortlist))

    return (
        errors,
        [],
        {
            "plan": str(PLAN_PATH),
            "planned_tasks": 8,
            "accepted_tasks": 0,
            "physical_actions_authorized": 0,
            "radiated_tx": "prohibited_in_p1a",
            "residuals": len(residuals.get("residuals", [])) if residuals else 0,
        },
        inputs,
    )
