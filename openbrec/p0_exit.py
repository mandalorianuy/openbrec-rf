from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRACEABILITY_PATH = Path("docs/governance/p0-traceability.json")
SUPPORT_PATH = Path("docs/governance/p0-support-status.json")
SHORTLIST_PATH = Path("docs/governance/p1a-hardware-shortlist.json")
RESIDUALS_PATH = Path("docs/governance/p0-residual-closure.json")

TASKS = {f"P0-{index:02d}" for index in range(1, 10)}
PROFILES = {"mobile-ad-hoc", "urban-planned", "backbone-heterogeneous"}
BEARERS = {"meshtastic", "meshcore", "reticulum"}
SUPPORT_STATES = {"experimental", "unverified", "unavailable", "deferred"}
RESIDUAL_STATES = {"resolved", "controlled", "planned"}


def _read(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"artifact unreadable: {exc}"]
    if not isinstance(value, dict):
        return None, ["artifact must be a JSON object"]
    return value, []


def validate_traceability(value: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    rows = value.get("requirements")
    if value.get("matrix_version") != "1.0.0":
        errors.append("matrix_version must be 1.0.0")
    if not isinstance(rows, list):
        return [*errors, "requirements must be an array"]
    tasks = {row.get("task") for row in rows if isinstance(row, dict)}
    if tasks != TASKS:
        errors.append("traceability must cover P0-01 through P0-09")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"requirements[{index}] must be an object")
            continue
        if not isinstance(row.get("requirement"), str) or not row["requirement"]:
            errors.append(f"requirements[{index}].requirement is required")
        for field in ("gate", "receipt"):
            field_value = row.get(field)
            if not (
                isinstance(field_value, str)
                and field_value
                or isinstance(field_value, list)
                and field_value
                and all(isinstance(item, str) and item for item in field_value)
            ):
                errors.append(f"requirements[{index}].{field} is required")
        fixtures = row.get("fixtures")
        if not isinstance(fixtures, list) or not fixtures:
            errors.append(f"requirements[{index}].fixtures must not be empty")
        else:
            for fixture in fixtures:
                if not isinstance(fixture, str) or not fixture:
                    errors.append(f"requirements[{index}] has invalid fixture")
                elif not (root / fixture).exists():
                    errors.append(f"traceability fixture not found: {fixture}")
        if row.get("status") != "accepted":
            errors.append(f"requirements[{index}].status must be accepted")
    return errors


def validate_support(
    value: dict[str, Any], shortlist: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    rows = value.get("support_matrix")
    if value.get("support_version") != "1.0.0":
        errors.append("support_version must be 1.0.0")
    if value.get("claim_scope") != "simulation_only":
        errors.append("claim_scope must remain simulation_only")
    if value.get("global_winner") is not None:
        errors.append("global_winner must be null")
    if not isinstance(rows, list):
        return [*errors, "support_matrix must be an array"]
    pairs: set[tuple[Any, Any]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"support_matrix[{index}] must be an object")
            continue
        pair = (row.get("profile"), row.get("bearer"))
        pairs.add(pair)
        if row.get("status") not in SUPPORT_STATES:
            errors.append(f"support_matrix[{index}] has forbidden support state")
        for field in ("version", "commit", "scenario", "evidence", "limitation"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"support_matrix[{index}].{field} is required")
    if pairs != {(profile, bearer) for profile in PROFILES for bearer in BEARERS}:
        errors.append("support matrix must contain every profile/bearer pair exactly once")
    if len(rows) != len(pairs):
        errors.append("support matrix contains duplicate profile/bearer pairs")

    categories = shortlist.get("categories")
    if shortlist.get("shortlist_version") != "1.0.0":
        errors.append("shortlist_version must be 1.0.0")
    if not isinstance(categories, list) or len(categories) < 8:
        return [*errors, "shortlist must contain at least eight categories"]
    seen: set[str] = set()
    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            errors.append(f"categories[{index}] must be an object")
            continue
        name = category.get("category")
        if not isinstance(name, str) or not name or name in seen:
            errors.append(f"categories[{index}] must have a unique category")
        else:
            seen.add(name)
        candidates = category.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1:
            errors.append(f"categories[{index}] must shortlist exactly one unit")
            continue
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            errors.append(f"categories[{index}] candidate must be an object")
            continue
        if candidate.get("support_status") != "unverified":
            errors.append(f"categories[{index}] candidate must remain unverified")
        if candidate.get("disposition") != "shortlisted_no_purchase":
            errors.append(f"categories[{index}] must prohibit automatic purchase")
        if candidate.get("separate_authorization_required") is not True:
            errors.append(f"categories[{index}] requires separate authorization")
        for field in ("candidate_id", "unit", "source", "acceptance_gate"):
            if not isinstance(candidate.get(field), str) or not candidate[field]:
                errors.append(f"categories[{index}] candidate.{field} is required")
    return errors


def validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    expected = {f"P0-R{index:03d}" for index in range(1, 16)}
    if value.get("register_version") != "1.0.0":
        errors.append("register_version must be 1.0.0")
    if not isinstance(rows, list):
        return [*errors, "residuals must be an array"]
    ids = {row.get("id") for row in rows if isinstance(row, dict)}
    if ids != expected or len(rows) != len(ids):
        errors.append("residual closure must cover P0-R001 through P0-R015 once")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        if row.get("state") not in RESIDUAL_STATES:
            errors.append(f"residuals[{index}] has invalid state")
        if row.get("due_task") == "P0-09":
            errors.append(f"residuals[{index}] is still due in P0-09")
        for field in ("owner", "decision", "gate_or_plan", "stop_condition"):
            if not isinstance(row.get(field), str) or not row[field]:
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def run_governance_gate(
    root: Path, gate: str, artifact: Path | None = None
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    default = {
        "p0-traceability": TRACEABILITY_PATH,
        "p0-support-status": SUPPORT_PATH,
        "p0-residuals": RESIDUALS_PATH,
    }[gate]
    path = artifact or root / default
    value, errors = _read(path)
    inputs = [path]
    if value is None:
        return errors, [], {"artifact": str(path)}, inputs
    if gate == "p0-traceability":
        errors.extend(validate_traceability(value, root))
        denominator = len(value.get("requirements", []))
    elif gate == "p0-support-status":
        shortlist_path = root / SHORTLIST_PATH
        shortlist, shortlist_errors = _read(shortlist_path)
        inputs.append(shortlist_path)
        errors.extend(shortlist_errors)
        if shortlist is not None:
            errors.extend(validate_support(value, shortlist))
        denominator = len(value.get("support_matrix", []))
    else:
        errors.extend(validate_residuals(value))
        denominator = len(value.get("residuals", []))
    return (
        errors,
        [],
        {
            "artifact": str(path.relative_to(root)),
            "denominator": denominator,
            "errors": len(errors),
        },
        inputs,
    )
