from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

PLAN_PATH = Path("docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md")
POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path("specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json")
ARCHITECTURE_SCHEMA_PATH = Path("schemas/open-spec/energy-architecture.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/energy/architecture-examples.json")
RESIDUALS_PATH = Path("docs/governance/open-spec-energy-residuals.json")

TOPOLOGIES = {
    "component_local",
    "shared_site_hub",
    "hybrid_site_component",
    "logistics_replacement",
}
ROLE_CATEGORIES = {
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
SOURCE_TYPES = {
    "storage",
    "portable_station",
    "replaceable_battery",
    "solar",
    "generator",
    "grid",
    "vehicle_dc",
    "manual_replacement",
}
LOAD_CLASSES = [
    "L0_LIFE_SAFETY",
    "L1_MISSION_CRITICAL",
    "L2_MISSION_SUPPORT",
    "L3_DEFERRABLE",
]
CLAIM_TYPES = [
    "unknown",
    "bounded_runtime",
    "storage_only_window",
    "sustainable_under_profile",
]


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
    if tasks[1].get("gate") != "open-spec-energy":
        errors.append("OS-02 must use the open-spec-energy gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("energy profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open energy boundary is required")
    else:
        if boundary.get("requires_owned_hardware") is not False:
            errors.append("owned hardware cannot gate the energy specification")
        if boundary.get("requires_solar") is not False:
            errors.append("solar cannot be mandatory")
        if boundary.get("requires_single_architecture") is not False:
            errors.append("a single energy architecture cannot be mandatory")
        if boundary.get("physical_validation_blocks_spec") is not False:
            errors.append("physical validation cannot block the energy specification")
        if boundary.get("perpetual_claim_allowed") is not False:
            errors.append("perpetual energy claims are prohibited")

    if value.get("load_classes") != LOAD_CLASSES:
        errors.append("energy load classes are incomplete or out of order")
    policy = value.get("claim_policy")
    if not isinstance(policy, dict) or policy.get("allowed_claim_types") != CLAIM_TYPES:
        errors.append("energy claim types must be bounded and complete")
    elif not all(
        policy.get(field) is True
        for field in (
            "storage_only_excludes_auxiliary_generation",
            "sustainable_claim_requires_nonnegative_lower_bound_each_window",
            "claims_are_scoped_to_load_environment_maintenance_and_window",
            "physical_claims_require_exact_implementation_evidence",
        )
    ):
        errors.append("energy claim policy invariants are incomplete")

    degradation = value.get("degradation_policy")
    if not isinstance(degradation, dict):
        errors.append("energy degradation policy is required")
    else:
        if degradation.get("shed_order") != LOAD_CLASSES[:0:-1]:
            errors.append("degradation must shed L3, L2 and L1 in that order")
        if degradation.get("preserve_l0_until_hardware_cutoff") is not True:
            errors.append("L0 must be preserved until hardware safety cutoff")
        if degradation.get("hardware_safety_overrides_l0") is not True:
            errors.append("hardware safety must override L0 when required")
        if degradation.get("requires_local_control_without_parent") is not True:
            errors.append("energy control must operate without a parent")

    architectures = value.get("architectures")
    if not isinstance(architectures, list) or len(architectures) != 4:
        errors.append("energy profiles must define four open architectures")
    else:
        topologies = {
            row.get("topology") for row in architectures if isinstance(row, dict)
        }
        if topologies != TOPOLOGIES:
            errors.append("energy architectures must cover all four topologies")
        for index, row in enumerate(architectures):
            if not isinstance(row, dict):
                errors.append(f"architectures[{index}] must be an object")
                continue
            if row.get("required_for_spec") is not False:
                errors.append(f"architectures[{index}] cannot be required for the spec")
            if row.get("alternatives_allowed") is not True:
                errors.append(f"architectures[{index}] must allow alternatives")
            for field in ("minimum_contracts", "alternatives", "solar_modes"):
                if not isinstance(row.get(field), list) or not row[field]:
                    errors.append(f"architectures[{index}].{field} must not be empty")

    mappings = value.get("role_mappings")
    if (
        not isinstance(mappings, list)
        or {row.get("category") for row in mappings if isinstance(row, dict)}
        != ROLE_CATEGORIES
    ):
        errors.append("energy role mappings must cover all nine OpenBREC categories")
    else:
        for index, row in enumerate(mappings):
            if "L0_LIFE_SAFETY" not in row.get("critical_load_classes", []):
                errors.append(f"role_mappings[{index}] must preserve L0")
            for field in (
                "allowed_architectures",
                "degradable_load_classes",
                "supply_alternatives",
            ):
                if not isinstance(row.get(field), list) or not row[field]:
                    errors.append(f"role_mappings[{index}].{field} must not be empty")

    adapters = value.get("source_adapters")
    if (
        not isinstance(adapters, list)
        or {row.get("source_type") for row in adapters if isinstance(row, dict)}
        != SOURCE_TYPES
    ):
        errors.append("source adapters must cover eight interchangeable source types")
    else:
        for index, row in enumerate(adapters):
            if row.get("required_for_spec") is not False:
                errors.append(f"source_adapters[{index}] cannot be required")
            for field in ("safety_controls", "evidence_requirements"):
                if not isinstance(row.get(field), list) or not row[field]:
                    errors.append(f"source_adapters[{index}].{field} must not be empty")
    if "indefinite" in json.dumps(value, sort_keys=True).lower():
        errors.append("unbounded indefinite energy language is prohibited")
    return errors


def _validate_schema_and_fixtures(
    schema: dict[str, Any], fixtures: dict[str, Any]
) -> tuple[list[str], int]:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return [f"energy architecture schema is invalid: {exc}"], 0
    errors: list[str] = []
    if schema.get("additionalProperties") is not False:
        errors.append("energy architecture schema must reject additional properties")
    examples = fixtures.get("examples")
    if not isinstance(examples, list) or len(examples) != 4:
        return [*errors, "energy fixtures must contain four examples"], 0
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    conforming = 0
    topologies: set[str] = set()
    solar_modes: set[str] = set()
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
        topologies.add(example["topology"])
        solar_modes.add(example["solar_mode"])
        if example["evidence_level"] not in {"specified", "simulated"}:
            errors.append(f"examples[{index}] cannot make a physical evidence claim")
        budget = example["modeled_budget"]
        required = (
            Decimal(str(budget["critical_load_Wh"]))
            + Decimal(str(budget["reserves_Wh"]))
        ) * Decimal(str(budget["margin_factor"]))
        expected_pass = Decimal(str(budget["usable_storage_Wh"])) >= required
        if budget["storage_only_pass"] is not expected_pass:
            errors.append(
                f"examples[{index}] storage_only_pass incorrectly credits or rejects energy"
            )
        if example["autonomy_claim"]["claim_type"] == "sustainable_under_profile":
            expected_net = (
                Decimal(str(budget["generation_lower_bound_Wh"]))
                - Decimal(str(budget["all_load_upper_bound_Wh"]))
                - Decimal(str(budget["conversion_storage_losses_Wh"]))
            )
            if Decimal(str(budget["net_energy_lower_bound_Wh"])) != expected_net:
                errors.append(
                    f"examples[{index}] sustainable net energy is inconsistent"
                )
            if expected_net < 0:
                errors.append(
                    f"examples[{index}] sustainable claim has negative lower bound"
                )
        if "indefinite" in json.dumps(example, sort_keys=True).lower():
            errors.append(f"examples[{index}] contains an unbounded energy claim")
    if topologies != TOPOLOGIES:
        errors.append("energy fixtures must exercise all four topologies")
    if solar_modes != {"none", "central", "per_component", "hybrid"}:
        errors.append("energy fixtures must exercise all solar modes")
    return errors, conforming


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("task") != "OS-02" or value.get("lane") != "open_spec":
        errors.append("energy residual register must belong to OS-02 open_spec")
    if not isinstance(rows, list) or len(rows) < 6:
        return [*errors, "at least six energy residuals are required"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"residuals[{index}] must be an object")
            continue
        if row.get("state") not in {"controlled", "planned", "evidence_required"}:
            errors.append(f"residuals[{index}] state is invalid")
        if row.get("blocks_open_spec") is not False:
            errors.append(f"residuals[{index}] cannot silently block Open Spec")
        for field in ("id", "owner", "risk", "gate_or_task", "stop_condition"):
            if not row.get(field):
                errors.append(f"residuals[{index}].{field} is required")
    return errors


def run_open_spec_energy_gate(
    root: Path,
    *,
    profiles_path: Path,
    architecture_schema_path: Path,
    fixtures_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    errors: list[str] = []
    plan_path = root / PLAN_PATH
    policy_path = root / POLICY_PATH
    inputs = [
        plan_path,
        policy_path,
        profiles_path,
        architecture_schema_path,
        fixtures_path,
        residuals_path,
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
        "OS-02 — aceptada",
        "OS-03 — aceptada",
        "OS-04 — aceptada",
        "OS-05 — aceptada",
        "OS-06 — no iniciada",
        "Solar es opcional",
        "sustainable_under_profile",
    ):
        if marker not in normalized_plan:
            errors.append(f"open-spec plan missing OS-02 boundary: {marker}")

    policy, policy_errors = _read_json(policy_path, "open-spec policy")
    profiles, profile_errors = _read_json(profiles_path, "energy profiles")
    schema, schema_errors = _read_json(
        architecture_schema_path, "energy architecture schema"
    )
    fixtures, fixture_errors = _read_json(fixtures_path, "energy fixtures")
    residuals, residual_errors = _read_json(residuals_path, "energy residuals")
    errors.extend(
        policy_errors
        + profile_errors
        + schema_errors
        + fixture_errors
        + residual_errors
    )
    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    conforming = 0
    if schema is not None and fixtures is not None:
        fixture_validation, conforming = _validate_schema_and_fixtures(schema, fixtures)
        errors.extend(fixture_validation)
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 5,
            "spec_tasks_total": 8,
            "architectures": len(profiles.get("architectures", [])) if profiles else 0,
            "role_mappings": len(profiles.get("role_mappings", [])) if profiles else 0,
            "source_adapters": (
                len(profiles.get("source_adapters", [])) if profiles else 0
            ),
            "conforming_examples": conforming,
            "physical_evidence_blocks_publication": False,
            "next_task": "OS-06",
            "next_task_started": False,
        },
        inputs,
    )
