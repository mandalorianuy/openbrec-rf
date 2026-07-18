from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

POLICY_PATH = Path("config/open-spec/governance.json")
KIT_PATH = Path("specs/openbrec/1.0.0-draft.1/conformance-kit.json")
SUBMISSION_SCHEMA_PATH = Path("schemas/open-spec/conformance-submission.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/conformance/conformance-examples.json")
MATRIX_PATH = Path("docs/decision-matrices/open-spec-functionality-matrix.json")
PUBLICATION_PATH = Path("docs/open-spec/README.md")
RESIDUALS_PATH = Path("docs/governance/open-spec-exit-residuals.json")

ADDONS = {
    "energy",
    "machine_telemetry",
    "human_messaging",
    "beacon_sensing",
    "recursive_federation",
}
CONTRIBUTION_TYPES = {
    "core_conformance",
    "addon_profile",
    "reuse_adapter",
    "reference_build",
    "evidence_pack",
    "extension",
}
EVIDENCE_LEVELS = [
    "unverified",
    "specified",
    "simulated",
    "lab_validated",
    "field_validated",
]
DECISIONS = {"build", "adapt", "evaluate", "defer", "prohibited"}
RESIDUAL_STATES = {"resolved", "controlled", "planned", "evidence_required"}
MATRIX_FIELDS = {
    "id",
    "functionality",
    "addon",
    "brec_value",
    "available_evidence",
    "decoupled_alternative",
    "hardware",
    "privacy",
    "safety_gate",
    "effort",
    "acceptance_criteria",
    "decision",
    "residual_refs",
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
        "accepted_tasks": 8,
        "total_tasks": 8,
        "percent": 100.0,
    }:
        errors.append("open-spec progress must be 8 / 8")
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 8:
        return [*errors, "open-spec policy must contain eight tasks"]
    if [task.get("id") for task in tasks] != [
        f"OS-{index:02d}" for index in range(1, 9)
    ]:
        errors.append("open-spec tasks must cover OS-01 through OS-08 in order")
    if [task.get("status") for task in tasks] != ["accepted"] * 8:
        errors.append("OS-01 through OS-08 must be accepted")
    if tasks[7].get("gate") != "open-spec-exit":
        errors.append("OS-08 must use the open-spec-exit gate")
    lane = value.get("physical_validation_lane")
    if not isinstance(lane, dict):
        errors.append("physical validation lane is required")
    else:
        if (
            lane.get("optional") is not True
            or lane.get("blocks_open_spec") is not False
        ):
            errors.append("physical validation must remain optional and nonblocking")
        if lane.get("progress") != {
            "accepted_tasks": 0,
            "total_tasks": 8,
            "percent": 0.0,
        }:
            errors.append("physical validation progress must remain 0 / 8")
    return errors


def _validate_kit(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("kit_version") != "1.0.0-draft.1":
        errors.append("conformance kit_version must be 1.0.0-draft.1")
    if value.get("spec_version") != "1.0.0-draft.1":
        errors.append("conformance spec_version must be 1.0.0-draft.1")

    gates = value.get("normative_gates")
    if not isinstance(gates, list) or [row.get("task") for row in gates] != [
        f"OS-{index:02d}" for index in range(1, 8)
    ]:
        errors.append("conformance kit must aggregate OS-01 through OS-07 in order")
        gates = []
    for index, row in enumerate(gates):
        for field in (
            "gate",
            "command",
            "normative_inputs",
            "proves",
            "does_not_prove",
        ):
            if not row.get(field):
                errors.append(f"normative_gates[{index}].{field} is required")

    classes = value.get("conformance_classes")
    if (
        not isinstance(classes, list)
        or {row.get("contribution_type") for row in classes} != CONTRIBUTION_TYPES
    ):
        errors.append("conformance classes must cover all contribution types")

    ladder = value.get("claim_ladder")
    if (
        not isinstance(ladder, list)
        or [row.get("level") for row in ladder] != EVIDENCE_LEVELS
    ):
        errors.append("claim ladder must preserve all evidence levels in order")
        ladder = []
    for row in ladder:
        physical = row.get("level") in {"lab_validated", "field_validated"}
        if row.get("physical_evidence_required") is not physical:
            errors.append(
                f"claim ladder physical evidence boundary invalid for {row.get('level')}"
            )
        if not row.get("minimum_evidence") or not row.get("allowed_claim"):
            errors.append(f"claim ladder requirements missing for {row.get('level')}")

    boundary = value.get("publication_boundary")
    if not isinstance(boundary, dict):
        errors.append("publication boundary is required")
    else:
        for field in (
            "owned_hardware_required",
            "physical_evidence_blocks_open_spec",
        ):
            if boundary.get(field) is not False:
                errors.append(f"publication boundary must keep {field} false")
        for field in (
            "conformance_never_implies_field_readiness",
            "reference_candidate_never_becomes_mandatory",
            "supported_requires_exact_current_evidence",
        ):
            if boundary.get(field) is not True:
                errors.append(f"publication boundary must enforce {field}")

    physical_rules = value.get("physical_evidence_rules")
    if not isinstance(physical_rules, dict):
        errors.append("physical evidence rules are required")
    else:
        if physical_rules.get("scope") != "exact_combination_only":
            errors.append("physical evidence must be scoped to the exact combination")
        for field in (
            "exact_hardware_and_firmware",
            "measurement_protocol",
            "raw_or_derived_results",
            "limitations_and_negative_results",
            "custody_and_responsible_actor",
            "jurisdiction_and_environment",
        ):
            if physical_rules.get(field) is not True:
                errors.append(f"physical evidence rule missing: {field}")
        for field in (
            "reference_candidate_becomes_requirement",
            "evidence_pack_blocks_open_spec",
        ):
            if physical_rules.get(field) is not False:
                errors.append(f"physical evidence rule must keep {field} false")

    publication = value.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication policy is required")
    else:
        if publication.get("license") != "Apache-2.0":
            errors.append("normative publication license must be Apache-2.0")
        for field in (
            "offline_bundle",
            "versioned_normative_paths",
            "checksums_required",
        ):
            if publication.get(field) is not True:
                errors.append(f"publication must enable {field}")
        for field in (
            "cloud_required",
            "vendor_certification_program",
            "paywall_allowed",
        ):
            if publication.get(field) is not False:
                errors.append(f"open publication must keep {field} false")

    process = value.get("community_process")
    expected_states = [
        "draft",
        "submitted",
        "validated",
        "accepted",
        "rejected_with_record",
        "superseded",
    ]
    if not isinstance(process, dict):
        errors.append("community process is required")
    else:
        if process.get("states") != expected_states:
            errors.append("community states must preserve rejection and supersession")
        for field in (
            "review_decisions_append_only",
            "negative_results_preserved",
            "rejected_submissions_preserved",
            "security_privacy_safety_review_required",
            "life_safety_precedes_destructive_minimization",
            "supersession_preserves_history",
        ):
            if process.get(field) is not True:
                errors.append(f"community process must enforce {field}")
        if process.get("silent_deletion_allowed") is not False:
            errors.append("community process cannot allow silent deletion")
    return errors


def _schema_validator(
    value: dict[str, Any], label: str
) -> tuple[Draft202012Validator | None, list[str]]:
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        return None, [f"{label} is not valid Draft 2020-12: {exc}"]
    if value.get("additionalProperties") is not False:
        return None, [f"{label} must reject additional properties"]
    return Draft202012Validator(value, format_checker=FormatChecker()), []


def _format_schema_errors(
    validator: Draft202012Validator, value: Any, label: str
) -> list[str]:
    issues = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    return [
        f"{label} {'/'.join(str(part) for part in issue.path) or '<root>'}: {issue.message}"
        for issue in issues
    ]


def _validate_fixtures(
    value: dict[str, Any], validator: Draft202012Validator | None
) -> tuple[list[str], int]:
    errors: list[str] = []
    if value.get("fixture_version") != "1.0.0-draft.1":
        errors.append("conformance fixture_version must be 1.0.0-draft.1")
    if value.get("synthetic_only") is not True:
        errors.append("conformance examples must declare synthetic_only")
    submissions = value.get("submissions")
    if (
        not isinstance(submissions, list)
        or {row.get("contribution_type") for row in submissions} != CONTRIBUTION_TYPES
    ):
        errors.append("fixtures must cover all contribution types")
        submissions = []
    identifiers: set[str] = set()
    for index, row in enumerate(submissions):
        if validator is not None:
            errors.extend(
                _format_schema_errors(validator, row, f"submissions[{index}]")
            )
        identifier = row.get("submission_id")
        if identifier in identifiers:
            errors.append(f"duplicate submission_id: {identifier}")
        identifiers.add(identifier)
        if not row.get("limitations"):
            errors.append(f"submissions[{index}] must declare limitations")
        if row.get("claimed_evidence_level") in {"lab_validated", "field_validated"}:
            if not isinstance(row.get("exact_configuration"), dict):
                errors.append(
                    f"submissions[{index}] physical evidence requires exact configuration"
                )
            if not isinstance(row.get("physical_evidence"), dict):
                errors.append(
                    f"submissions[{index}] physical evidence pack is required"
                )
            if len(row.get("evidence_refs", [])) < 2:
                errors.append(
                    f"submissions[{index}] physical evidence requires protocol and results refs"
                )
    return errors, len(submissions)


def _validate_matrix(value: dict[str, Any]) -> tuple[list[str], int]:
    errors: list[str] = []
    if value.get("matrix_version") != "1.0.0-draft.1":
        errors.append("matrix_version must be 1.0.0-draft.1")
    method = value.get("method")
    if not isinstance(method, dict):
        errors.append("decision matrix method is required")
    else:
        if method.get("aggregate_score") is not None:
            errors.append("decision matrix cannot use an aggregate score")
        if method.get("global_winner") is not None:
            errors.append("decision matrix cannot select a global winner")
        if method.get("history_policy") != "append_only":
            errors.append("decision matrix history must be append_only")
        if method.get("negative_results_policy") != "preserve_and_link":
            errors.append("decision matrix must preserve and link negative results")

    rows = value.get("functionalities")
    if not isinstance(rows, list) or len(rows) < 10:
        errors.append("decision matrix must include at least ten functionalities")
        rows = []
    if {row.get("addon") for row in rows} != ADDONS:
        errors.append("decision matrix must cover all five addon families")
    identifiers: set[str] = set()
    for index, row in enumerate(rows):
        if set(row) != MATRIX_FIELDS:
            errors.append(f"functionalities[{index}] fields do not match the contract")
        identifier = row.get("id")
        if not identifier or identifier in identifiers:
            errors.append(f"functionalities[{index}] id must be unique")
        identifiers.add(identifier)
        if row.get("brec_value") not in {"V1", "V2", "V3", "V4", "V5"}:
            errors.append(f"functionalities[{index}] has invalid BREC value")
        if row.get("decision") not in DECISIONS:
            errors.append(f"functionalities[{index}] has invalid decision")
        if row.get("effort") not in {"S", "M", "L", "XL"}:
            errors.append(f"functionalities[{index}] has invalid effort")
        if not row.get("decoupled_alternative") or not row.get("acceptance_criteria"):
            errors.append(f"functionalities[{index}] lacks alternative or acceptance")
        hardware = row.get("hardware", {})
        if hardware.get("required_for_spec") is not False:
            errors.append(f"functionalities[{index}] cannot require hardware for spec")
        if hardware.get("substitution_allowed") is not True:
            errors.append(f"functionalities[{index}] must allow hardware substitution")
        privacy = row.get("privacy", {})
        if privacy.get("life_safety_precedes_minimization") is not True:
            errors.append(f"functionalities[{index}] must prioritize life safety")
        if not privacy.get("controls"):
            errors.append(f"functionalities[{index}] privacy controls are required")
        safety = row.get("safety_gate", {})
        if not safety.get("stop_condition"):
            errors.append(f"functionalities[{index}] safety stop condition is required")
        if (
            safety.get("possible_distress") is True
            and safety.get("preserve_for_review") is not True
        ):
            errors.append(
                f"functionalities[{index}] possible distress must be preserved"
            )
        if not row.get("residual_refs"):
            errors.append(f"functionalities[{index}] residual refs are required")
    return errors, len(rows)


def _validate_publication(root: Path, path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8").lower()
    except OSError as exc:
        return [f"publication unreadable: {exc}"]
    errors: list[str] = []
    for token in (
        "1.0.0-draft.1",
        "conformance.md",
        "community-evidence.md",
        "publishing.md",
        "apache-2.0",
        "no acredita",
    ):
        if token not in text:
            errors.append(f"publication index missing boundary: {token}")
    for relative in (
        "docs/open-spec/CONFORMANCE.md",
        "docs/open-spec/COMMUNITY-EVIDENCE.md",
        "docs/open-spec/PUBLISHING.md",
    ):
        if not (root / relative).is_file():
            errors.append(f"publication document missing: {relative}")
    return errors


def _validate_residuals(
    value: dict[str, Any], matrix: dict[str, Any] | None
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    if value.get("task") != "OS-08":
        errors.append("exit residual register must belong to OS-08")
    rows = value.get("residuals")
    if not isinstance(rows, list) or len(rows) < 12:
        errors.append("OS-08 must govern at least twelve residuals")
        rows = []
    identifiers: set[str] = set()
    counts = {state: 0 for state in RESIDUAL_STATES}
    for index, row in enumerate(rows):
        identifier = row.get("id")
        if not identifier or identifier in identifiers:
            errors.append(f"residuals[{index}] id must be unique")
        identifiers.add(identifier)
        state = row.get("state")
        if state not in RESIDUAL_STATES:
            errors.append(f"residuals[{index}] has invalid state")
        else:
            counts[state] += 1
        if row.get("blocks_open_spec") is not False:
            errors.append(f"residuals[{index}] cannot block the completed Open Spec")
        for field in ("owner", "risk", "disposition", "gate_or_task", "stop_condition"):
            if not row.get(field):
                errors.append(f"residuals[{index}].{field} is required")
    if matrix:
        for index, row in enumerate(matrix.get("functionalities", [])):
            unknown = set(row.get("residual_refs", [])) - identifiers
            if unknown:
                errors.append(
                    f"functionalities[{index}] references unknown residuals: {sorted(unknown)}"
                )
    return errors, counts


def run_open_spec_exit_gate(
    root: Path,
    *,
    kit_path: Path,
    submission_schema_path: Path,
    fixtures_path: Path,
    matrix_path: Path,
    publication_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    inputs = [
        root / POLICY_PATH,
        kit_path,
        submission_schema_path,
        fixtures_path,
        matrix_path,
        publication_path,
        residuals_path,
        root / "openbrec/open_spec_exit.py",
    ]
    policy, errors = _read_json(root / POLICY_PATH, "open-spec policy")
    kit, read_errors = _read_json(kit_path, "conformance kit")
    errors.extend(read_errors)
    schema, read_errors = _read_json(submission_schema_path, "submission schema")
    errors.extend(read_errors)
    fixtures, read_errors = _read_json(fixtures_path, "conformance fixtures")
    errors.extend(read_errors)
    matrix, read_errors = _read_json(matrix_path, "decision matrix")
    errors.extend(read_errors)
    residuals, read_errors = _read_json(residuals_path, "exit residuals")
    errors.extend(read_errors)

    if policy:
        errors.extend(_validate_policy(policy))
    if kit:
        errors.extend(_validate_kit(kit))
    validator: Draft202012Validator | None = None
    if schema:
        validator, schema_errors = _schema_validator(schema, "submission schema")
        errors.extend(schema_errors)
    submission_count = 0
    if fixtures:
        fixture_errors, submission_count = _validate_fixtures(fixtures, validator)
        errors.extend(fixture_errors)
    functionality_count = 0
    if matrix:
        matrix_errors, functionality_count = _validate_matrix(matrix)
        errors.extend(matrix_errors)
    errors.extend(_validate_publication(root, publication_path))
    residual_counts = {state: 0 for state in RESIDUAL_STATES}
    if residuals:
        residual_errors, residual_counts = _validate_residuals(residuals, matrix)
        errors.extend(residual_errors)

    summary = {
        "spec_version": policy.get("spec_version") if policy else None,
        "spec_tasks_accepted": 8,
        "spec_tasks_total": 8,
        "open_spec_complete": True,
        "normative_gates": len(kit.get("normative_gates", [])) if kit else 0,
        "conformance_classes": len(kit.get("conformance_classes", [])) if kit else 0,
        "conforming_examples": submission_count,
        "matrix_addons": len(ADDONS),
        "matrix_functionalities": functionality_count,
        "resolved_residuals": residual_counts["resolved"],
        "controlled_residuals": residual_counts["controlled"],
        "planned_residuals": residual_counts["planned"],
        "evidence_required_residuals": residual_counts["evidence_required"],
        "physical_evidence_blocks_publication": False,
        "next_task": "P1a-01",
        "next_task_lane": "optional_physical_validation",
        "next_task_started": False,
    }
    return errors, [], summary, inputs
