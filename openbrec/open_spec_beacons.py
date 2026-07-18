from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash

PLAN_PATH = Path("docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md")
POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path("specs/openbrec/1.0.0-draft.1/beacon-capability-profiles.json")
EXTENSION_SCHEMA_PATH = Path("schemas/open-spec/beacon-modality-extension.schema.json")
DATASET_SCHEMA_PATH = Path("schemas/open-spec/beacon-dataset-manifest.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/beacons/conformance-examples.json")
RESIDUALS_PATH = Path("docs/governance/open-spec-beacon-residuals.json")

CORE_MODALITIES = {
    "acoustic_features",
    "movement_change",
    "thermal_low_resolution",
}
ALLOWED_OUTPUTS = {
    "unknown",
    "insufficient_coverage",
    "sensor_artifact_likely",
    "single_modality_candidate",
    "corroborated_candidate",
}
PROHIBITED_CLAIMS = {
    "person_present",
    "person_absent",
    "identity",
    "biometric_match",
    "medical_diagnosis",
    "victim_count",
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
    if tasks[4].get("gate") != "open-spec-beacons":
        errors.append("OS-05 must use the open-spec-beacons gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("beacon profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open beacon boundary is required")
    else:
        if boundary.get("minimum_modalities") != 1:
            errors.append(
                "a conforming beacon must permit exactly one minimum modality"
            )
        if boundary.get("reference_modalities") != 3:
            errors.append("the reference beacon must expose three modality slots")
        if boundary.get("trimodal_required") is not False:
            errors.append("tri-modal reference cannot be mandatory")
        if boundary.get("requires_owned_hardware") is not False:
            errors.append("owned hardware cannot gate the beacon specification")
        if boundary.get("physical_detection_blocks_spec") is not False:
            errors.append("physical detection cannot block the beacon specification")
        if boundary.get("modalities_are_replaceable_adapters") is not True:
            errors.append("beacon modalities must remain replaceable adapters")
        if boundary.get("cloud_dependency_allowed_in_critical_path") is not False:
            errors.append("cloud cannot enter the critical beacon path")

    rows = value.get("core_modality_profiles")
    if not isinstance(rows, list) or len(rows) != 3:
        errors.append("beacon profiles must define three core modality profiles")
    elif {
        row.get("modality") for row in rows if isinstance(row, dict)
    } != CORE_MODALITIES:
        errors.append("beacon profiles must cover acoustic, movement and thermal")
    else:
        for index, row in enumerate(rows):
            if row.get("required_for_spec") is not False:
                errors.append(f"core_modality_profiles[{index}] cannot be mandatory")
            if row.get("alternatives_allowed") is not True:
                errors.append(
                    f"core_modality_profiles[{index}] must allow alternatives"
                )
            for field in ("observations", "limitations"):
                if not row.get(field):
                    errors.append(
                        f"core_modality_profiles[{index}].{field} is required"
                    )

    observation = value.get("observation_policy")
    if not isinstance(observation, dict):
        errors.append("observation policy is required")
    else:
        if observation.get("normative_chain") != (
            "Observation -> Evidence -> FusionResult -> OperatorAnnotation"
        ):
            errors.append("beacons must reuse the normative core evidence chain")
        for field in (
            "parallel_fact_chain_allowed",
            "silence_means_absence",
            "missing_sensor_means_absence",
            "single_candidate_means_presence",
        ):
            if observation.get(field) is not False:
                errors.append(f"observation policy must keep {field} false")
        for field in (
            "unknown_and_abstention_required",
            "missing_capabilities_visible",
            "fusion_is_deterministic_without_ml",
            "ml_must_version_model_and_allow_unknown",
        ):
            if observation.get(field) is not True:
                errors.append(f"observation policy invariant missing: {field}")

    capture = value.get("raw_capture_policy")
    if not isinstance(capture, dict):
        errors.append("raw capture policy is required")
    else:
        if capture.get("default") != "disabled":
            errors.append("raw capture must default to disabled")
        for field in (
            "local_only_by_default",
            "explicit_authorization_required",
            "encryption_required",
            "bounded_duration_required",
            "audit_required",
            "life_safety_hold_before_deletion",
            "material_reference_only_in_observations",
        ):
            if capture.get(field) is not True:
                errors.append(f"raw capture invariant missing: {field}")
        for field in ("automatic_federation", "live_stream_allowed_initially"):
            if capture.get(field) is not False:
                errors.append(f"raw capture policy must keep {field} false")

    encoded = json.dumps(value, sort_keys=True).lower()
    for claim in PROHIBITED_CLAIMS:
        if f'"{claim}"' in encoded:
            errors.append(f"prohibited beacon claim in profiles: {claim}")
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


def _format_errors(
    validator: Draft202012Validator, value: Any, label: str
) -> list[str]:
    issues = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    return [
        f"{label} {'/'.join(str(part) for part in issue.path) or '<root>'}: {issue.message}"
        for issue in issues
    ]


def _validate_fixtures(
    extension_schema: dict[str, Any],
    dataset_schema: dict[str, Any],
    fixtures: dict[str, Any],
) -> tuple[list[str], int, int, int]:
    errors: list[str] = []
    extension_validator, extension_errors = _schema_validator(
        extension_schema, "beacon modality extension schema"
    )
    dataset_validator, dataset_errors = _schema_validator(
        dataset_schema, "beacon dataset manifest schema"
    )
    errors.extend(extension_errors)
    errors.extend(dataset_errors)

    deployments = fixtures.get("deployment_examples")
    if not isinstance(deployments, list) or len(deployments) < 3:
        errors.append(
            "fixtures must define single, tri-modal and extension deployments"
        )
        deployments = []
    else:
        compositions = {row.get("composition") for row in deployments}
        if compositions != {
            "single_modality",
            "trimodal_reference",
            "extension_modality",
        }:
            errors.append("deployment fixtures do not cover all three compositions")
        for index, row in enumerate(deployments):
            modalities = row.get("modalities")
            if not isinstance(modalities, list) or not modalities:
                errors.append(
                    f"deployment_examples[{index}] needs at least one modality"
                )
            if row.get("triangulation_available") is not False:
                errors.append(
                    f"deployment_examples[{index}] cannot imply triangulation"
                )
            if row.get("presence_confirmation_available") is not False:
                errors.append(
                    f"deployment_examples[{index}] cannot imply presence confirmation"
                )

    extensions = fixtures.get("extensions")
    if not isinstance(extensions, list) or not extensions:
        errors.append("fixtures must include at least one extension registration")
        extensions = []
    elif extension_validator is not None:
        for index, row in enumerate(extensions):
            errors.extend(
                _format_errors(extension_validator, row, f"extensions[{index}]")
            )

    manifests = fixtures.get("dataset_manifests")
    if not isinstance(manifests, list) or len(manifests) < 2:
        errors.append("fixtures must include at least two reusable dataset manifests")
        manifests = []
    elif dataset_validator is not None:
        for index, row in enumerate(manifests):
            errors.extend(
                _format_errors(dataset_validator, row, f"dataset_manifests[{index}]")
            )

    encoded = json.dumps(fixtures, sort_keys=True).lower()
    for claim in PROHIBITED_CLAIMS:
        if f'"{claim}"' in encoded:
            errors.append(f"prohibited beacon claim in fixtures: {claim}")
    return errors, len(deployments), len(extensions), len(manifests)


def _case_output(case: dict[str, Any]) -> str:
    if case.get("raw_material_present"):
        return "unknown"
    if case.get("known_artifact"):
        return "sensor_artifact_likely"
    if case.get("coverage") != "sufficient":
        return "insufficient_coverage"
    if (
        case.get("baseline_valid") is not True
        or case.get("placement_valid") is not True
        or case.get("out_of_distribution") is True
    ):
        return "unknown"
    beacons = set(case.get("beacon_ids", []))
    groups = set(case.get("independence_groups", []))
    if len(beacons) >= 2 and len(groups) >= 2:
        return "corroborated_candidate"
    return "single_modality_candidate"


def _projection(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "case_id": case["case_id"],
                "output": _case_output(case),
                "modalities": sorted(case.get("modalities", [])),
                "beacon_ids": sorted(set(case.get("beacon_ids", []))),
                "independence_groups": sorted(set(case.get("independence_groups", []))),
                "capabilities_absent": sorted(case.get("capabilities_absent", [])),
                "limitations": [
                    "candidate only",
                    "never confirms presence or absence",
                ],
            }
            for case in cases
        ],
        key=lambda item: item["case_id"],
    )


def _replay_summary(fixtures: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    cases = fixtures.get("replay_cases")
    if not isinstance(cases, list) or not cases:
        return ["fixtures must define replay_cases"], {}
    errors: list[str] = []
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or len(ids) != len(set(ids)):
        errors.append("replay case IDs must be present and unique")
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"replay_cases[{index}] must be an object")
            continue
        expected = case.get("expected_output")
        if expected not in ALLOWED_OUTPUTS:
            errors.append(f"prohibited beacon claim in replay_cases[{index}]")
            continue
        derived = _case_output(case)
        if derived != expected:
            errors.append(
                f"replay_cases[{index}] derived {derived} != expected {expected}"
            )

    hashes: set[str] = set()
    for offset in range(10):
        ordered = cases[offset % len(cases) :] + cases[: offset % len(cases)]
        if offset % 2:
            ordered = list(reversed(ordered))
        hashes.add(canonical_hash(_projection(ordered)))
    projection = _projection(cases)
    abstained = sum(
        item["output"] in {"unknown", "insufficient_coverage"} for item in projection
    )
    shared_cause_independent = sum(
        len(item["beacon_ids"]) >= 2
        and len(item["independence_groups"]) < 2
        and item["output"] == "corroborated_candidate"
        for item in projection
    )
    raw_promotions = sum(
        case.get("raw_material_present") is True and _case_output(case) != "unknown"
        for case in cases
    )
    summary = {
        "replay_orders": 10,
        "replay_hashes": len(hashes),
        "replay_sha256": canonical_hash(projection),
        "replay_cases": len(cases),
        "abstained_cases": abstained,
        "automatic_presence_confirmations": 0,
        "absence_inferences": 0,
        "shared_cause_counted_independent": shared_cause_independent,
        "raw_material_fact_promotions": raw_promotions,
        "missing_capabilities_visible": sum(
            bool(item["capabilities_absent"]) for item in projection
        ),
    }
    if len(hashes) != 1:
        errors.append("beacon replay projection is not deterministic")
    if shared_cause_independent:
        errors.append("shared-cause beacon evidence was counted independent")
    if raw_promotions:
        errors.append("raw beacon material was promoted to a fact")
    return errors, summary


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("lane") != "open_spec" or value.get("task") != "OS-05":
        errors.append("beacon residual register must belong to open-spec OS-05")
    if not isinstance(rows, list) or len(rows) < 10:
        return [*errors, "at least ten beacon residuals are required"]
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
            errors.append(f"residuals[{index}] cannot block open-spec publication")
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


def run_open_spec_beacon_gate(
    root: Path,
    *,
    profiles_path: Path,
    extension_schema_path: Path,
    dataset_schema_path: Path,
    fixtures_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    policy_path = root / POLICY_PATH
    inputs = [
        policy_path,
        profiles_path,
        extension_schema_path,
        dataset_schema_path,
        fixtures_path,
        residuals_path,
        root / "openbrec/open_spec_beacons.py",
    ]
    policy, errors = _read_json(policy_path, "open-spec policy")
    profiles, read_errors = _read_json(profiles_path, "beacon profiles")
    errors.extend(read_errors)
    extension_schema, read_errors = _read_json(
        extension_schema_path, "beacon extension schema"
    )
    errors.extend(read_errors)
    dataset_schema, read_errors = _read_json(
        dataset_schema_path, "beacon dataset schema"
    )
    errors.extend(read_errors)
    fixtures, read_errors = _read_json(fixtures_path, "beacon fixtures")
    errors.extend(read_errors)
    residuals, read_errors = _read_json(residuals_path, "beacon residuals")
    errors.extend(read_errors)

    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    deployments = extensions = datasets = 0
    replay_summary: dict[str, Any] = {}
    if (
        extension_schema is not None
        and dataset_schema is not None
        and fixtures is not None
    ):
        fixture_errors, deployments, extensions, datasets = _validate_fixtures(
            extension_schema, dataset_schema, fixtures
        )
        errors.extend(fixture_errors)
        if not fixture_errors:
            replay_errors, replay_summary = _replay_summary(fixtures)
            errors.extend(replay_errors)
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    boundary = profiles.get("open_boundary", {}) if profiles else {}
    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 6,
            "spec_tasks_total": 8,
            "core_modality_profiles": len(
                profiles.get("core_modality_profiles", []) if profiles else []
            ),
            "minimum_modalities": boundary.get("minimum_modalities"),
            "reference_modalities": boundary.get("reference_modalities"),
            "deployment_examples": deployments,
            "extension_examples": extensions,
            "dataset_manifests": datasets,
            **replay_summary,
            "physical_detection_blocks_publication": False,
            "next_task": "OS-07",
            "next_task_started": False,
        },
        inputs,
    )
