from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

POLICY_PATH = Path("config/open-spec/governance.json")
PROFILES_PATH = Path("specs/openbrec/1.0.0-draft.1/reference-build-profiles.json")
BUILD_SCHEMA_PATH = Path("schemas/open-spec/reference-build-manifest.schema.json")
ADAPTER_SCHEMA_PATH = Path("schemas/open-spec/reuse-adapter-manifest.schema.json")
FIXTURES_PATH = Path("fixtures/open-spec/builds/conformance-examples.json")
GUIDE_INDEX_PATH = Path("docs/open-spec/reference-builds/README.md")
RESIDUALS_PATH = Path("docs/governance/open-spec-build-residuals.json")

ADDONS = {
    "energy",
    "machine_telemetry",
    "human_messaging",
    "beacon_sensing",
    "recursive_federation",
}
ROUTES = {"open_build", "reuse_existing", "hybrid"}
GUIDE_HEADINGS = {
    "## Alcance",
    "## Plano funcional",
    "## BOM por capacidades",
    "## Reutilización",
    "## Verificación",
    "## Límites",
}
SUPPORT_STATUSES = {"supported", "experimental", "unverified", "unavailable"}


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
    if [task.get("status") for task in tasks] != ["accepted"] * 8:
        errors.append("OS-01 through OS-08 must be accepted")
    if tasks[6].get("gate") != "open-spec-builds":
        errors.append("OS-07 must use the open-spec-builds gate")
    return errors


def _validate_profiles(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if value.get("profile_set_version") != "1.0.0-draft.1":
        errors.append("build profile_set_version must be 1.0.0-draft.1")
    boundary = value.get("open_boundary")
    if not isinstance(boundary, dict):
        errors.append("open build boundary is required")
    else:
        for field, label in (
            ("owned_hardware_required", "owned hardware"),
            ("named_vendor_required", "named vendor"),
            ("named_sku_required", "named SKU"),
            ("physical_evidence_blocks_spec", "physical evidence"),
            ("reference_build_is_field_ready", "field readiness"),
            ("reference_build_is_certified", "certification"),
        ):
            if boundary.get(field) is not False:
                errors.append(f"{label} cannot be required by the Open Spec")
        for field in (
            "capability_equivalent_substitution_allowed",
            "existing_components_reusable",
        ):
            if boundary.get(field) is not True:
                errors.append(f"open build boundary must enable {field}")

    if set(value.get("delivery_routes", [])) != ROUTES:
        errors.append("profiles must expose open, reuse and hybrid delivery routes")
    if set(value.get("support_statuses", [])) != SUPPORT_STATUSES:
        errors.append("profiles must expose all four support statuses")

    builds = value.get("reference_builds")
    if not isinstance(builds, list) or {row.get("addon") for row in builds} != ADDONS:
        errors.append("reference builds must cover all five addon families")
        builds = []
    for index, row in enumerate(builds):
        if set(row.get("delivery_routes", [])) != ROUTES:
            errors.append(f"reference_builds[{index}] must support all delivery routes")
        if row.get("required_for_spec") is not False:
            errors.append(f"reference_builds[{index}] cannot be mandatory")
        if row.get("substitution_allowed") is not True:
            errors.append(f"reference_builds[{index}] must allow substitution")
        if not row.get("guide_ref"):
            errors.append(f"reference_builds[{index}].guide_ref is required")

    bom_policy = value.get("bom_policy")
    if not isinstance(bom_policy, dict):
        errors.append("BOM policy is required")
    else:
        if bom_policy.get("capability_roles_only") is not True:
            errors.append("BOMs must use capability roles only")
        if bom_policy.get("minimum_substitution_classes") != 2:
            errors.append("BOM items require at least two substitution classes")
        if bom_policy.get("single_source_requirement_allowed") is not False:
            errors.append("single-source BOM requirements are prohibited")

    separation = value.get("plane_separation")
    if not isinstance(separation, dict):
        errors.append("human and machine plane separation is required")
    else:
        for field in (
            "human_plane_writes_observations",
            "human_plane_writes_facts",
            "machine_plane_accepts_sos",
        ):
            if separation.get(field) is not False:
                errors.append(f"plane separation must keep {field} false")
        for field in (
            "shared_enclosure_requires_coexistence_evidence",
            "keys_queues_priorities_and_audit_separate",
        ):
            if separation.get(field) is not True:
                errors.append(f"plane separation invariant missing: {field}")
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


def _prohibited_keys(value: Any, prefix: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}/{key}" if prefix else key
            if key.lower() in {"vendor", "sku", "product_url"}:
                errors.append(f"prohibited product-specific field: {path}")
            errors.extend(_prohibited_keys(nested, path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(_prohibited_keys(nested, f"{prefix}/{index}"))
    return errors


def _validate_fixtures(
    build_schema: dict[str, Any],
    adapter_schema: dict[str, Any],
    fixtures: dict[str, Any],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    build_validator, schema_errors = _schema_validator(
        build_schema, "reference build schema"
    )
    errors.extend(schema_errors)
    adapter_validator, schema_errors = _schema_validator(
        adapter_schema, "reuse adapter schema"
    )
    errors.extend(schema_errors)

    builds = fixtures.get("build_manifests")
    if not isinstance(builds, list) or {row.get("addon") for row in builds} != ADDONS:
        errors.append("build fixtures must cover all five addon families")
        builds = []
    for index, row in enumerate(builds):
        if build_validator is not None:
            errors.extend(
                _format_errors(build_validator, row, f"build_manifests[{index}]")
            )
        if set(row.get("delivery_routes", [])) != ROUTES:
            errors.append(f"build_manifests[{index}] must expose all delivery routes")
        if row.get("evidence_level") != "specified":
            errors.append(f"build_manifests[{index}] must remain specified-only")
        if row.get("physical_performance_claimed") is not False:
            errors.append(f"build_manifests[{index}] cannot claim physical performance")
        if row.get("field_readiness_claimed") is not False:
            errors.append(f"build_manifests[{index}] cannot claim field readiness")
        for item_index, item in enumerate(row.get("bom", [])):
            if len(item.get("substitution_classes", [])) < 2:
                errors.append(
                    f"build_manifests[{index}].bom[{item_index}] lacks substitutions"
                )
            if item.get("single_source_required") is not False:
                errors.append(
                    f"build_manifests[{index}].bom[{item_index}] is single-source"
                )
    errors.extend(_prohibited_keys(builds))

    adapters = fixtures.get("adapter_manifests")
    if not isinstance(adapters, list) or len(adapters) < 8:
        errors.append("fixtures require at least eight reuse adapters")
        adapters = []
    if adapters and {row.get("addon") for row in adapters} != ADDONS:
        errors.append("adapter fixtures must cover all five addon families")
    for index, row in enumerate(adapters):
        if adapter_validator is not None:
            errors.extend(
                _format_errors(adapter_validator, row, f"adapter_manifests[{index}]")
            )
        if row.get("support_status") == "supported" and not row.get(
            "support_evidence_refs"
        ):
            errors.append(
                f"adapter_manifests[{index}] cannot be supported without exact evidence"
            )
        if row.get("writes_facts_directly") is not False:
            errors.append(f"adapter_manifests[{index}] cannot write facts directly")
        if row.get("raw_payload_default") is not False:
            errors.append(f"adapter_manifests[{index}] cannot default to raw payload")

    return errors, {
        "build_manifests": len(builds),
        "adapter_manifests": len(adapters),
        "addons_covered": len({row.get("addon") for row in builds}),
        "delivery_routes": len(ROUTES),
        "bom_items": sum(len(row.get("bom", [])) for row in builds),
        "single_source_items": sum(
            item.get("single_source_required") is True
            for row in builds
            for item in row.get("bom", [])
        ),
        "supported_adapters": sum(
            row.get("support_status") == "supported" for row in adapters
        ),
        "experimental_adapters": sum(
            row.get("support_status") == "experimental" for row in adapters
        ),
        "unverified_adapters": sum(
            row.get("support_status") == "unverified" for row in adapters
        ),
    }


def _validate_guides(
    root: Path, profiles: dict[str, Any], guide_index_path: Path
) -> tuple[list[str], int]:
    errors: list[str] = []
    try:
        index = guide_index_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"guide index unreadable: {exc}"], 0
    for token in ("inventario de capacidades", "reutilizar", "no acredita"):
        if token not in index.lower():
            errors.append(f"guide index missing reuse boundary: {token}")
    guides = 0
    for position, row in enumerate(profiles.get("reference_builds", [])):
        guide_ref = row.get("guide_ref")
        if not isinstance(guide_ref, str):
            continue
        guide_path = (root / guide_ref).resolve()
        try:
            guide_path.relative_to(root.resolve())
        except ValueError:
            errors.append(f"reference_builds[{position}] guide escapes repository")
            continue
        try:
            source = guide_path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"reference_builds[{position}] guide missing: {guide_ref}")
            continue
        guides += 1
        for heading in GUIDE_HEADINGS:
            if heading not in source:
                errors.append(f"{guide_ref} missing heading: {heading}")
    return errors, guides


def _validate_residuals(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = value.get("residuals")
    if value.get("lane") != "open_spec" or value.get("task") != "OS-07":
        errors.append("build residual register must belong to open-spec OS-07")
    if not isinstance(rows, list) or len(rows) < 10:
        return [*errors, "at least ten build residuals are required"]
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


def run_open_spec_build_gate(
    root: Path,
    *,
    profiles_path: Path,
    build_schema_path: Path,
    adapter_schema_path: Path,
    fixtures_path: Path,
    guide_index_path: Path,
    residuals_path: Path,
) -> tuple[list[str], list[str], dict[str, Any], list[Path]]:
    policy_path = root / POLICY_PATH
    inputs = [
        policy_path,
        profiles_path,
        build_schema_path,
        adapter_schema_path,
        fixtures_path,
        guide_index_path,
        residuals_path,
        root / "openbrec/open_spec_builds.py",
    ]
    policy, errors = _read_json(policy_path, "open-spec policy")
    profiles, read_errors = _read_json(profiles_path, "reference build profiles")
    errors.extend(read_errors)
    build_schema, read_errors = _read_json(build_schema_path, "reference build schema")
    errors.extend(read_errors)
    adapter_schema, read_errors = _read_json(
        adapter_schema_path, "reuse adapter schema"
    )
    errors.extend(read_errors)
    fixtures, read_errors = _read_json(fixtures_path, "reference build fixtures")
    errors.extend(read_errors)
    residuals, read_errors = _read_json(residuals_path, "build residuals")
    errors.extend(read_errors)

    if policy is not None:
        errors.extend(_validate_policy(policy))
    if profiles is not None:
        errors.extend(_validate_profiles(profiles))
    fixture_summary: dict[str, Any] = {}
    if build_schema is not None and adapter_schema is not None and fixtures is not None:
        fixture_errors, fixture_summary = _validate_fixtures(
            build_schema, adapter_schema, fixtures
        )
        errors.extend(fixture_errors)
    guide_count = 0
    if profiles is not None:
        guide_errors, guide_count = _validate_guides(root, profiles, guide_index_path)
        errors.extend(guide_errors)
    if residuals is not None:
        errors.extend(_validate_residuals(residuals))

    return (
        errors,
        [],
        {
            "spec_version": policy.get("spec_version") if policy else None,
            "spec_tasks_accepted": 8,
            "spec_tasks_total": 8,
            **fixture_summary,
            "guides": guide_count,
            "physical_build_blocks_publication": False,
            "open_spec_complete": True,
            "next_task": "P1a-01",
            "next_task_lane": "optional_physical_validation",
            "next_task_started": False,
        },
        inputs,
    )
