from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = Path("schemas/p1a/capability-manifest.schema.json")
AUTHORIZATION_SCHEMA_PATH = Path(
    "schemas/p1a/asset-authorization-register.schema.json"
)
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


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.utcoffset() is not None else None


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


def _duplicate_record_groups(
    records: Iterable[dict[str, Any]], field: str
) -> list[tuple[str, tuple[str, ...]]]:
    categories_by_value: dict[str, list[str]] = {}
    for record in records:
        value = record.get(field)
        category = record.get("category")
        if isinstance(value, str) and category in CATEGORY_SET:
            categories_by_value.setdefault(value, []).append(category)
    return [
        (value, tuple(categories))
        for value, categories in categories_by_value.items()
        if len(categories) > 1
    ]


def _authorization_receipt_sha256(authorization: dict[str, Any]) -> str | None:
    method = authorization.get("method")
    if method == "purchase":
        purchase = authorization.get("purchase")
        return (
            purchase.get("purchase_receipt_sha256")
            if isinstance(purchase, dict)
            else None
        )
    if method == "loan":
        loan = authorization.get("loan")
        return loan.get("loan_receipt_sha256") if isinstance(loan, dict) else None
    if method == "existing_asset":
        return authorization.get("evidence_sha256")
    return None


def _firmware_review(
    manifest: dict[str, Any], label: str
) -> tuple[list[str], str | None, int]:
    errors: list[str] = []
    source_order_errors = 0
    if manifest.get("manifest_version") != "2.0.0":
        errors.append(f"{label} manifest_version must be 2.0.0")
    if manifest.get("category") not in FIRMWARE_CATEGORIES:
        return errors, None, source_order_errors

    firmware_pin = manifest.get("firmware_pin")
    if not isinstance(firmware_pin, dict):
        errors.append(f"{label} requires an immutable firmware pin")
        return errors, None, source_order_errors
    review = firmware_pin.get("advisory_review")
    if not isinstance(review, dict):
        errors.append(f"{label} requires advisory_review provenance")
        return errors, None, source_order_errors

    for field in ("reviewer", "reason"):
        if _placeholder(review.get(field)):
            errors.append(f"{label} advisory_review.{field} cannot be a placeholder")
    sources = review.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label} advisory_review requires at least one source")
    else:
        reviewed_at = _parse_date(review.get("reviewed_at"))
        for index, source in enumerate(sources):
            if not isinstance(source, dict) or _placeholder(source.get("locator")):
                errors.append(
                    f"{label} advisory_review.sources[{index}] requires an exact locator"
                )
                continue
            retrieved_at = _parse_datetime(source.get("retrieved_at"))
            if (
                reviewed_at is not None
                and retrieved_at is not None
                and retrieved_at.date() > reviewed_at
            ):
                source_order_errors += 1
                errors.append(
                    f"{label} advisory source was retrieved after review"
                )
    disposition = review.get("disposition")
    if disposition not in {"no_known_blocker", "block_firmware_use"}:
        errors.append(f"{label} advisory_review disposition is invalid")
        return errors, None, source_order_errors
    return errors, disposition, source_order_errors


def _inspection_predates_authorization(
    authorization: dict[str, Any], manifest: dict[str, Any]
) -> bool:
    authorized_at = _parse_datetime(authorization.get("authorized_at"))
    inspection = manifest.get("physical_inspection")
    inspected_at = (
        _parse_datetime(inspection.get("inspected_at"))
        if isinstance(inspection, dict)
        else None
    )
    return (
        authorized_at is not None
        and inspected_at is not None
        and inspected_at < authorized_at
    )


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
    schema_path: Path,
    authorization_schema_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    """Validate partial evidence without accepting physical claims."""
    request, errors = _read_json(request_path, "asset authorization request")
    warnings: list[str] = []
    schema, schema_errors = _read_json(schema_path, "capability manifest schema")
    errors.extend(schema_errors)
    validator: Draft202012Validator | None = None
    if schema is not None:
        try:
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
        except Exception as exc:
            errors.append(f"capability manifest schema is invalid: {exc}")
    authorization_schema, authorization_schema_errors = _read_json(
        authorization_schema_path, "asset authorization register schema"
    )
    errors.extend(authorization_schema_errors)
    authorization_validator: Draft202012Validator | None = None
    if authorization_schema is not None:
        try:
            Draft202012Validator.check_schema(authorization_schema)
            authorization_validator = Draft202012Validator(
                authorization_schema, format_checker=FormatChecker()
            )
        except Exception as exc:
            errors.append(f"asset authorization register schema is invalid: {exc}")
    inputs = [request_path, schema_path, authorization_schema_path]
    if request is None:
        return errors, warnings, {"task": "P1a-01"}, inputs

    rows = request.get("asset_requests")
    if not isinstance(rows, list):
        return (
            [*errors, "asset authorization request must contain asset_requests"],
            warnings,
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

    category_errors: dict[str, list[str]] = {
        category: [] for category in CATEGORIES
    }
    authorization_by_category: dict[str, dict[str, Any]] = {}
    authorization_records: list[dict[str, Any]] = []
    register_path = evidence_dir / "authorization-register.json"
    if register_path.is_file():
        inputs.append(register_path)
        register, register_errors = _read_json(register_path, "authorization register")
        errors.extend(register_errors)
        if register is not None and authorization_validator is not None:
            for issue in sorted(
                authorization_validator.iter_errors(register),
                key=lambda item: list(item.path),
            ):
                location = ".".join(str(part) for part in issue.path) or "$"
                message = f"authorization-register:{location}: {issue.message}"
                errors.append(message)
                path_parts = list(issue.path)
                if (
                    len(path_parts) >= 2
                    and path_parts[0] == "authorizations"
                    and isinstance(path_parts[1], int)
                ):
                    records_for_error = register.get("authorizations", [])
                    index = path_parts[1]
                    if index < len(records_for_error):
                        category = records_for_error[index].get("category")
                        if category in category_errors:
                            category_errors[category].append(message)
        if register is not None and register.get("register_version") != "1.0.0":
            errors.append("authorization register_version must be 1.0.0")
        if register is not None and register.get("task") != "P1a-01":
            errors.append("authorization register task must be P1a-01")
        records = register.get("authorizations") if register is not None else []
        if not isinstance(records, list):
            errors.append("authorization register authorizations must be an array")
            records = []
        for index, raw in enumerate(records):
            record_errors, record = _validate_authorization_record(raw, index)
            errors.extend(record_errors)
            if record is None:
                continue
            category = record.get("category")
            if category not in CATEGORY_SET:
                continue
            authorization_records.append(record)
            category_errors[category].extend(record_errors)
            if record.get("candidate_id") != CANDIDATE_BY_CATEGORY[category]:
                message = f"{category} authorization candidate_id does not match category"
                errors.append(message)
                category_errors[category].append(message)
            if category in authorization_by_category:
                message = f"duplicate authorization category: {category}"
                errors.append(message)
                category_errors[category].append(message)
            else:
                authorization_by_category[category] = record

    duplicate_authorization_id_groups = _duplicate_record_groups(
        authorization_records, "authorization_id"
    )
    duplicate_authorization_evidence_groups = _duplicate_record_groups(
        authorization_records, "evidence_sha256"
    )
    for _, categories in duplicate_authorization_id_groups:
        message = (
            "authorization_id is reused across categories: "
            + ", ".join(categories)
        )
        errors.append(message)
        for category in categories:
            category_errors[category].append(message)
    for _, categories in duplicate_authorization_evidence_groups:
        message = (
            "authorization evidence is reused across categories: "
            + ", ".join(categories)
        )
        errors.append(message)
        for category in categories:
            category_errors[category].append(message)

    manifest_by_category: dict[str, dict[str, Any]] = {}
    firmware_advisory_blocker_categories: list[str] = []
    advisory_source_order_errors = 0
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
        if category not in CATEGORY_SET:
            errors.append(f"{path.name} category is not governed")
            continue
        manifest_errors_for_category: list[str] = []
        if validator is not None:
            for issue in sorted(
                validator.iter_errors(manifest), key=lambda item: list(item.path)
            ):
                location = ".".join(str(part) for part in issue.path) or "$"
                manifest_errors_for_category.append(
                    f"{path.name}:{location}: {issue.message}"
                )
        for field in ("manufacturer", "model", "sku", "hardware_revision"):
            if _placeholder(manifest.get(field)):
                manifest_errors_for_category.append(
                    f"{path.name} has placeholder identity in {field}"
                )
        inspection = manifest.get("physical_inspection")
        if isinstance(inspection, dict) and inspection.get("condition") == "unknown":
            manifest_errors_for_category.append(
                f"{path.name} inspection condition cannot remain unknown"
            )
        firmware_errors, disposition, source_order_errors = _firmware_review(
            manifest, path.name
        )
        advisory_source_order_errors += source_order_errors
        manifest_errors_for_category.extend(firmware_errors)
        if disposition == "block_firmware_use":
            firmware_advisory_blocker_categories.append(category)
            warnings.append(
                f"{category} firmware use remains blocked by advisory review"
            )
        if manifest.get("candidate_id") != CANDIDATE_BY_CATEGORY[category]:
            manifest_errors_for_category.append(
                f"{path.name} candidate_id does not match governed shortlist"
            )
        if category in manifest_by_category:
            manifest_errors_for_category.append(
                f"duplicate manifest category: {category}"
            )
        else:
            manifest_by_category[category] = manifest
        errors.extend(manifest_errors_for_category)
        category_errors[category].extend(manifest_errors_for_category)

    duplicate_asset_id_groups = _duplicate_record_groups(
        manifest_by_category.values(), "asset_id"
    )
    duplicate_serial_evidence_groups = _duplicate_record_groups(
        manifest_by_category.values(), "serial_evidence_sha256"
    )
    duplicate_custody_receipt_groups = _duplicate_record_groups(
        (
            {
                "category": manifest.get("category"),
                "receipt_sha256": custody.get("receipt_sha256"),
            }
            for manifest in manifest_by_category.values()
            if isinstance((custody := manifest.get("custody")), dict)
        ),
        "receipt_sha256",
    )
    for _, categories in duplicate_asset_id_groups:
        message = (
            "asset_id is reused across categories: " + ", ".join(categories)
        )
        errors.append(message)
        for category in categories:
            category_errors[category].append(message)
    for _, categories in duplicate_serial_evidence_groups:
        message = (
            "serial evidence is reused across categories: "
            + ", ".join(categories)
        )
        errors.append(message)
        for category in categories:
            category_errors[category].append(message)
    for _, categories in duplicate_custody_receipt_groups:
        message = (
            "custody receipt is reused across categories: "
            + ", ".join(categories)
        )
        errors.append(message)
        for category in categories:
            category_errors[category].append(message)

    custody_receipt_mismatches = 0
    authorization_inspection_order_errors = 0
    for category in CATEGORIES:
        authorization = authorization_by_category.get(category)
        manifest = manifest_by_category.get(category)
        if authorization is None or manifest is None:
            continue
        custody = manifest.get("custody")
        expected = {
            "asset_id": manifest.get("asset_id"),
            "candidate_id": manifest.get("candidate_id"),
            "category": category,
            "method": custody.get("method") if isinstance(custody, dict) else None,
            "custodian": (
                custody.get("custodian") if isinstance(custody, dict) else None
            ),
        }
        if any(authorization.get(field) != value for field, value in expected.items()):
            message = f"{category} authorization does not match manifest"
            errors.append(message)
            category_errors[category].append(message)
        expected_receipt = _authorization_receipt_sha256(authorization)
        actual_receipt = (
            custody.get("receipt_sha256") if isinstance(custody, dict) else None
        )
        if expected_receipt != actual_receipt:
            custody_receipt_mismatches += 1
            message = (
                f"{category} custody receipt does not match authorization evidence"
            )
            errors.append(message)
            category_errors[category].append(message)
        if _inspection_predates_authorization(authorization, manifest):
            authorization_inspection_order_errors += 1
            message = f"{category} physical inspection predates authorization"
            errors.append(message)
            category_errors[category].append(message)

    checklist: list[dict[str, Any]] = []
    for category in CATEGORIES:
        request_row = requested_by_category.get(category, {})
        authorization_present = category in authorization_by_category
        manifest_present = category in manifest_by_category
        missing: list[str] = []
        if not authorization_present:
            missing.append("authorization_record")
        if not manifest_present:
            missing.append("capability_manifest")
        if missing:
            required = request_row.get("required_external_evidence", [])
            if isinstance(required, list):
                missing.extend(item for item in required if isinstance(item, str))
        validation_errors = category_errors[category]
        if validation_errors:
            status = "invalid_submission"
        elif authorization_present and manifest_present:
            status = "validated_for_acceptance_gate"
        else:
            status = "awaiting_external_evidence"
        checklist.append(
            {
                "category": category,
                "candidate_id": CANDIDATE_BY_CATEGORY[category],
                "authorization_present": authorization_present,
                "manifest_present": manifest_present,
                "status": status,
                "missing_external_evidence": list(dict.fromkeys(missing)),
                "validation_errors": validation_errors,
            }
        )

    valid = sum(
        row["status"] == "validated_for_acceptance_gate" for row in checklist
    )
    invalid = sum(row["status"] == "invalid_submission" for row in checklist)
    summary = {
        "task": "P1a-01",
        "task_status": (
            "ready_for_acceptance_gate"
            if valid == len(CATEGORIES) and invalid == 0
            else "blocked_external_evidence"
        ),
        "evidence_dir": str(evidence_dir.relative_to(root)),
        "category_denominator": len(CATEGORIES),
        "categories_ready_for_gate": valid,
        "categories_valid_for_gate": valid,
        "categories_invalid": invalid,
        "categories_awaiting_external_evidence": len(CATEGORIES) - valid - invalid,
        "duplicate_asset_id_groups": len(duplicate_asset_id_groups),
        "duplicate_serial_evidence_groups": len(
            duplicate_serial_evidence_groups
        ),
        "duplicate_authorization_id_groups": len(
            duplicate_authorization_id_groups
        ),
        "duplicate_authorization_evidence_groups": len(
            duplicate_authorization_evidence_groups
        ),
        "duplicate_custody_receipt_groups": len(
            duplicate_custody_receipt_groups
        ),
        "custody_receipt_mismatches": custody_receipt_mismatches,
        "authorization_inspection_order_errors": (
            authorization_inspection_order_errors
        ),
        "advisory_source_order_errors": advisory_source_order_errors,
        "firmware_advisory_blockers": len(
            firmware_advisory_blocker_categories
        ),
        "firmware_advisory_blocker_categories": sorted(
            firmware_advisory_blocker_categories
        ),
        "firmware_use_authorized": False,
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
            "Validated submissions remain non-accepted until the 9/9 acceptance gate passes."
        ),
    }
    return errors, warnings, summary, inputs


def run_asset_gate(
    root: Path,
    *,
    evidence_dir: Path,
    schema_path: Path,
    authorization_schema_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    warnings: list[str] = []
    inputs: list[Path] = [schema_path, authorization_schema_path]
    schema, schema_errors = _read_json(schema_path, "capability manifest schema")
    errors.extend(schema_errors)
    validator: Draft202012Validator | None = None
    if schema is not None:
        try:
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
        except Exception as exc:
            errors.append(f"capability manifest schema is invalid: {exc}")

    authorization_schema, authorization_schema_errors = _read_json(
        authorization_schema_path, "asset authorization register schema"
    )
    errors.extend(authorization_schema_errors)
    authorization_validator: Draft202012Validator | None = None
    if authorization_schema is not None:
        try:
            Draft202012Validator.check_schema(authorization_schema)
            authorization_validator = Draft202012Validator(
                authorization_schema, format_checker=FormatChecker()
            )
        except Exception as exc:
            errors.append(f"asset authorization register schema is invalid: {exc}")

    register_path = evidence_dir / "authorization-register.json"
    register, register_errors = _read_json(register_path, "authorization register")
    errors.extend(register_errors)
    if register_path.is_file():
        inputs.append(register_path)

    authorization_by_id: dict[str, dict[str, Any]] = {}
    authorization_records: list[dict[str, Any]] = []
    if register is not None:
        if authorization_validator is not None:
            for issue in sorted(
                authorization_validator.iter_errors(register),
                key=lambda item: list(item.path),
            ):
                location = ".".join(str(part) for part in issue.path) or "$"
                errors.append(f"authorization-register:{location}: {issue.message}")
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
            authorization_records.append(record)
            identifier = record.get("authorization_id")
            if identifier in authorization_by_id:
                errors.append(f"duplicate authorization_id: {identifier}")
            elif isinstance(identifier, str):
                authorization_by_id[identifier] = record

    duplicate_authorization_id_groups = _duplicate_record_groups(
        authorization_records, "authorization_id"
    )
    duplicate_authorization_evidence_groups = _duplicate_record_groups(
        authorization_records, "evidence_sha256"
    )
    for _, categories in duplicate_authorization_id_groups:
        errors.append(
            "authorization_id is reused across categories: "
            + ", ".join(categories)
        )
    for _, categories in duplicate_authorization_evidence_groups:
        errors.append(
            "authorization evidence is reused across categories: "
            + ", ".join(categories)
        )

    manifests_dir = evidence_dir / "manifests"
    manifest_paths = sorted(manifests_dir.glob("*.json")) if manifests_dir.is_dir() else []
    if len(manifest_paths) != len(CATEGORIES):
        errors.append("evidence must contain nine exact manifests")
    inputs.extend(manifest_paths)

    manifests: list[dict[str, Any]] = []
    support_statuses: dict[str, int] = {}
    authorization_mismatches = 0
    custody_receipt_mismatches = 0
    authorization_inspection_order_errors = 0
    firmware_advisory_blocker_categories: list[str] = []
    advisory_source_order_errors = 0
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
        firmware_errors, disposition, source_order_errors = _firmware_review(
            manifest, path.name
        )
        advisory_source_order_errors += source_order_errors
        errors.extend(firmware_errors)
        if disposition == "block_firmware_use":
            firmware_advisory_blocker_categories.append(category)
            warnings.append(
                f"{category} firmware use remains blocked by advisory review"
            )

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
        elif _authorization_receipt_sha256(authorization) != custody.get(
            "receipt_sha256"
        ):
            custody_receipt_mismatches += 1
            errors.append(
                f"{path.name} custody receipt does not match authorization evidence"
            )
        if (
            authorization is not None
            and _inspection_predates_authorization(authorization, manifest)
        ):
            authorization_inspection_order_errors += 1
            errors.append(f"{path.name} physical inspection predates authorization")
        if category in CANDIDATE_BY_CATEGORY and manifest.get("candidate_id") != CANDIDATE_BY_CATEGORY[category]:
            errors.append(f"{path.name} candidate_id does not match governed shortlist")

    categories = [manifest.get("category") for manifest in manifests]
    if set(categories) != CATEGORY_SET or len(categories) != len(set(categories)):
        errors.append("manifest categories must match the nine-category denominator exactly once")
    duplicate_asset_id_groups = _duplicate_record_groups(manifests, "asset_id")
    if duplicate_asset_id_groups:
        errors.append("asset_id values must be unique")
    duplicate_serial_evidence_groups = _duplicate_record_groups(
        manifests, "serial_evidence_sha256"
    )
    if duplicate_serial_evidence_groups:
        errors.append("serial evidence must be unique per physical asset")
    duplicate_custody_receipt_groups = _duplicate_record_groups(
        (
            {
                "category": manifest.get("category"),
                "receipt_sha256": custody.get("receipt_sha256"),
            }
            for manifest in manifests
            if isinstance((custody := manifest.get("custody")), dict)
        ),
        "receipt_sha256",
    )
    if duplicate_custody_receipt_groups:
        errors.append("custody receipt evidence must be unique per physical asset")

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
        "custody_receipt_mismatches": custody_receipt_mismatches,
        "authorization_inspection_order_errors": (
            authorization_inspection_order_errors
        ),
        "advisory_source_order_errors": advisory_source_order_errors,
        "duplicate_asset_id_groups": len(duplicate_asset_id_groups),
        "duplicate_serial_evidence_groups": len(
            duplicate_serial_evidence_groups
        ),
        "duplicate_authorization_id_groups": len(
            duplicate_authorization_id_groups
        ),
        "duplicate_authorization_evidence_groups": len(
            duplicate_authorization_evidence_groups
        ),
        "duplicate_custody_receipt_groups": len(
            duplicate_custody_receipt_groups
        ),
        "firmware_advisory_blockers": len(
            firmware_advisory_blocker_categories
        ),
        "firmware_advisory_blocker_categories": sorted(
            firmware_advisory_blocker_categories
        ),
        "firmware_use_authorized": False,
        "physical_behavior_validated": False,
        "radiated_tx_authorized": False,
    }
    return errors, warnings, summary, inputs
