from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = Path("schemas/p1a/capability-manifest.schema.json")
DEFAULT_EVIDENCE_DIR = Path("evidence/p1a/p1a-01")
AUTHORIZATION_REQUEST_PATH = Path(
    "docs/governance/p1a-01-asset-authorization-request.json"
)

CATEGORIES = (
    "lorawan_gateway",
    "lorawan_endpoint",
    "meshtastic_node",
    "meshcore_node",
    "rnode",
    "offline_terminal",
    "trimodal_beacon",
    "energy_storage",
    "wired_cell_gateway",
)
CATEGORY_SET = set(CATEGORIES)
FIRMWARE_CATEGORIES = CATEGORY_SET - {"energy_storage"}
CANDIDATE_BY_CATEGORY = {
    category: f"P1A-HW-{index:02d}"
    for index, category in enumerate(CATEGORIES, start=1)
}
PLACEHOLDERS = {
    "example",
    "fake",
    "n/a",
    "na",
    "pending",
    "placeholder",
    "synthetic",
    "tbd",
    "todo",
    "unknown",
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _read_json(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        detail = exc.strerror or type(exc).__name__
        return None, [f"{label} unreadable: {path.name}: {detail}"]
    except json.JSONDecodeError as exc:
        return None, [
            f"{label} invalid JSON: {path.name}: line {exc.lineno} column {exc.colno}"
        ]
    if not isinstance(value, dict):
        return None, [f"{label} must be a JSON object: {path}"]
    return value, []


def _placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() in PLACEHOLDERS


def _validate_authorization_record(
    record: Any, index: int
) -> tuple[list[str], dict[str, Any] | None]:
    prefix = f"authorizations[{index}]"
    if not isinstance(record, dict):
        return [f"{prefix} must be an object"], None
    errors: list[str] = []
    required_strings = (
        "authorization_id",
        "candidate_id",
        "asset_id",
        "category",
        "method",
        "state",
        "authorized_at",
        "authorized_by",
        "custodian",
        "evidence_sha256",
    )
    for field in required_strings:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip() or _placeholder(value):
            errors.append(f"{prefix}.{field} must be an exact non-placeholder string")
    if record.get("category") not in CATEGORY_SET:
        errors.append(f"{prefix}.category is not governed")
    if record.get("method") not in {"existing_asset", "loan", "purchase"}:
        errors.append(f"{prefix}.method is invalid")
    if record.get("state") != "authorized_for_inventory_only":
        errors.append(f"{prefix}.state must be authorized_for_inventory_only")
    scope = record.get("scope")
    if not isinstance(scope, list) or set(scope) != {
        "physical_inspection",
        "custody_registration",
    }:
        errors.append(
            f"{prefix}.scope must authorize only physical_inspection and custody_registration"
        )
    if not SHA256.fullmatch(str(record.get("evidence_sha256", ""))):
        errors.append(f"{prefix}.evidence_sha256 must be a sha256")

    method = record.get("method")
    if method == "purchase":
        purchase = record.get("purchase")
        if not isinstance(purchase, dict) or not all(
            purchase.get(field)
            for field in (
                "budget_owner",
                "maximum_amount",
                "currency",
                "supplier_or_channel",
                "purchase_receipt_sha256",
            )
        ):
            errors.append(f"{prefix}.purchase requires budget and receipt evidence")
    if method == "loan":
        loan = record.get("loan")
        if not isinstance(loan, dict) or not all(
            loan.get(field)
            for field in ("asset_owner", "return_terms", "loan_receipt_sha256")
        ):
            errors.append(f"{prefix}.loan requires owner, return terms and receipt evidence")
    return errors, record


def run_asset_intake(
    root: Path,
    *,
    evidence_dir: Path,
    request_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    """Report missing external evidence without accepting physical claims."""
    request, errors = _read_json(request_path, "asset authorization request")
    inputs = [request_path]
    if request is None:
        return errors, [], {"task": "P1a-01"}, inputs

    rows = request.get("asset_requests")
    if not isinstance(rows, list):
        return (
            [*errors, "asset authorization request must contain asset_requests"],
            [],
            {"task": "P1a-01"},
            inputs,
        )
    requested_by_category = {
        row.get("category"): row for row in rows if isinstance(row, dict)
    }
    if set(requested_by_category) != CATEGORY_SET or len(rows) != len(CATEGORIES):
        errors.append("asset authorization request must cover nine categories exactly once")
    for category, row in requested_by_category.items():
        if (
            category in CANDIDATE_BY_CATEGORY
            and row.get("candidate_id") != CANDIDATE_BY_CATEGORY[category]
        ):
            errors.append(
                f"{category} candidate_id does not match governed category"
            )

    authorization_categories: set[str] = set()
    register_path = evidence_dir / "authorization-register.json"
    if register_path.is_file():
        inputs.append(register_path)
        register, register_errors = _read_json(register_path, "authorization register")
        errors.extend(register_errors)
        records = register.get("authorizations") if register is not None else []
        if not isinstance(records, list):
            errors.append("authorization register authorizations must be an array")
            records = []
        for record in records:
            if not isinstance(record, dict):
                continue
            category = record.get("category")
            if (
                category in CATEGORY_SET
                and record.get("candidate_id") == CANDIDATE_BY_CATEGORY[category]
            ):
                authorization_categories.add(category)

    manifest_categories: set[str] = set()
    manifests_dir = evidence_dir / "manifests"
    manifest_paths = (
        sorted(manifests_dir.glob("*.json")) if manifests_dir.is_dir() else []
    )
    inputs.extend(manifest_paths)
    for path in manifest_paths:
        manifest, manifest_errors = _read_json(path, "capability manifest")
        errors.extend(manifest_errors)
        if manifest is None:
            continue
        category = manifest.get("category")
        if (
            category in CATEGORY_SET
            and manifest.get("candidate_id") == CANDIDATE_BY_CATEGORY[category]
        ):
            manifest_categories.add(category)

    checklist: list[dict[str, Any]] = []
    for category in CATEGORIES:
        request_row = requested_by_category.get(category, {})
        authorization_present = category in authorization_categories
        manifest_present = category in manifest_categories
        missing: list[str] = []
        if not authorization_present:
            missing.append("authorization_record")
        if not manifest_present:
            missing.append("capability_manifest")
        if missing:
            required = request_row.get("required_external_evidence", [])
            if isinstance(required, list):
                missing.extend(item for item in required if isinstance(item, str))
        checklist.append(
            {
                "category": category,
                "candidate_id": CANDIDATE_BY_CATEGORY[category],
                "authorization_present": authorization_present,
                "manifest_present": manifest_present,
                "status": (
                    "submitted_for_gate_review"
                    if authorization_present and manifest_present
                    else "awaiting_external_evidence"
                ),
                "missing_external_evidence": list(dict.fromkeys(missing)),
            }
        )

    ready = sum(row["status"] == "submitted_for_gate_review" for row in checklist)
    summary = {
        "task": "P1a-01",
        "task_status": (
            "ready_for_acceptance_gate"
            if ready == len(CATEGORIES)
            else "blocked_external_evidence"
        ),
        "evidence_dir": str(evidence_dir.relative_to(root)),
        "category_denominator": len(CATEGORIES),
        "categories_ready_for_gate": ready,
        "categories_awaiting_external_evidence": len(CATEGORIES) - ready,
        "accepted_tasks": 0,
        "total_tasks": 8,
        "percent": 0.0,
        "physical_actions_authorized": bool(
            request.get("physical_actions_authorized", False)
        ),
        "purchase_authorized": bool(request.get("purchase_authorized", False)),
        "acceptance_gate": request.get("acceptance_gate"),
        "next_task": "P1a-01",
        "next_task_started": False,
        "category_checklist": checklist,
        "non_progress_notice": (
            "This preflight reports intake readiness only and does not accept P1a-01."
        ),
    }
    return errors, [], summary, inputs


def run_asset_gate(
    root: Path,
    *,
    evidence_dir: Path,
    schema_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    inputs: list[Path] = [schema_path]
    schema, schema_errors = _read_json(schema_path, "capability manifest schema")
    errors.extend(schema_errors)
    validator: Draft202012Validator | None = None
    if schema is not None:
        try:
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
        except Exception as exc:
            errors.append(f"capability manifest schema is invalid: {exc}")

    register_path = evidence_dir / "authorization-register.json"
    register, register_errors = _read_json(register_path, "authorization register")
    errors.extend(register_errors)
    if register_path.is_file():
        inputs.append(register_path)

    authorization_by_id: dict[str, dict[str, Any]] = {}
    if register is not None:
        if register.get("register_version") != "1.0.0":
            errors.append("authorization register_version must be 1.0.0")
        if register.get("task") != "P1a-01":
            errors.append("authorization register task must be P1a-01")
        records = register.get("authorizations")
        if not isinstance(records, list) or len(records) != len(CATEGORIES):
            errors.append("authorization register must contain nine exact authorizations")
            records = records if isinstance(records, list) else []
        for index, raw in enumerate(records):
            record_errors, record = _validate_authorization_record(raw, index)
            errors.extend(record_errors)
            if record is None:
                continue
            identifier = record.get("authorization_id")
            if identifier in authorization_by_id:
                errors.append(f"duplicate authorization_id: {identifier}")
            elif isinstance(identifier, str):
                authorization_by_id[identifier] = record

    manifests_dir = evidence_dir / "manifests"
    manifest_paths = sorted(manifests_dir.glob("*.json")) if manifests_dir.is_dir() else []
    if len(manifest_paths) != len(CATEGORIES):
        errors.append("evidence must contain nine exact manifests")
    inputs.extend(manifest_paths)

    manifests: list[dict[str, Any]] = []
    support_statuses: dict[str, int] = {}
    authorization_mismatches = 0
    for path in manifest_paths:
        manifest, manifest_errors = _read_json(path, "capability manifest")
        errors.extend(manifest_errors)
        if manifest is None:
            continue
        manifests.append(manifest)
        if validator is not None:
            for issue in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
                location = ".".join(str(part) for part in issue.path) or "$"
                errors.append(f"{path.name}:{location}: {issue.message}")

        category = manifest.get("category")
        status = manifest.get("support_status")
        if isinstance(status, str):
            support_statuses[status] = support_statuses.get(status, 0) + 1
        for field in ("manufacturer", "model", "sku", "hardware_revision"):
            if _placeholder(manifest.get(field)):
                errors.append(f"{path.name} has placeholder identity in {field}")
        inspection = manifest.get("physical_inspection")
        if isinstance(inspection, dict) and inspection.get("condition") == "unknown":
            errors.append(f"{path.name} inspection condition cannot remain unknown")
        if category in FIRMWARE_CATEGORIES and not isinstance(
            manifest.get("firmware_pin"), dict
        ):
            errors.append(f"{path.name} requires an immutable firmware pin")

        custody = manifest.get("custody")
        authorization = (
            authorization_by_id.get(custody.get("authorization_id"))
            if isinstance(custody, dict)
            else None
        )
        expected = {
            "asset_id": manifest.get("asset_id"),
            "candidate_id": manifest.get("candidate_id"),
            "category": category,
            "method": custody.get("method") if isinstance(custody, dict) else None,
            "custodian": custody.get("custodian") if isinstance(custody, dict) else None,
        }
        if authorization is None or any(
            authorization.get(field) != value for field, value in expected.items()
        ):
            authorization_mismatches += 1
            errors.append(f"{path.name} authorization does not match manifest")
        if category in CANDIDATE_BY_CATEGORY and manifest.get("candidate_id") != CANDIDATE_BY_CATEGORY[category]:
            errors.append(f"{path.name} candidate_id does not match governed shortlist")

    categories = [manifest.get("category") for manifest in manifests]
    if set(categories) != CATEGORY_SET or len(categories) != len(set(categories)):
        errors.append("manifest categories must match the nine-category denominator exactly once")
    asset_ids = [manifest.get("asset_id") for manifest in manifests]
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("asset_id values must be unique")

    accepted_assets = len(manifests) if not errors else 0
    summary = {
        "task": "P1a-01",
        "evidence_dir": str(evidence_dir.relative_to(root)),
        "category_denominator": len(CATEGORIES),
        "manifest_files": len(manifest_paths),
        "authorization_records": len(authorization_by_id),
        "accepted_assets": accepted_assets,
        "support_statuses": support_statuses,
        "authorization_mismatches": authorization_mismatches,
        "physical_behavior_validated": False,
        "radiated_tx_authorized": False,
    }
    return errors, [], summary, inputs
