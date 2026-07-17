from __future__ import annotations

import copy
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
INVALID_FIXTURE_NAMES = {
    "required-missing.json",
    "unknown-field.json",
    "wrong-root-type.json",
    "enum-unknown.json",
    "null-not-allowed.json",
    "timestamp-noncanonical.json",
    "version-unknown.json",
}


def load_catalog(
    root: Path, relative_path: str = "schemas/core/catalog.json"
) -> dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def load_core_schemas(root: Path) -> list[tuple[dict[str, Any], Path]]:
    root = root.resolve()
    catalog = load_catalog(root)
    schemas: list[tuple[dict[str, Any], Path]] = []
    for entry in catalog["entries"]:
        path = (root / entry["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"catalog path is outside repository root: {entry['path']}"
            ) from exc
        schemas.append((json.loads(path.read_text(encoding="utf-8")), path))
    return schemas


def contract_set_sha256(schemas: list[tuple[dict[str, Any], Path]]) -> str:
    material = sorted(
        (
            {
                "id": schema["$id"],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for schema, path in schemas
        ),
        key=lambda item: item["id"],
    )
    canonical = json.dumps(
        material, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def schema_registry(schemas: list[tuple[dict[str, Any], Path]]) -> Registry:
    resources = {schema["$id"]: Resource.from_contents(schema) for schema, _ in schemas}
    for schema, _ in schemas:
        for reference in _references(schema):
            if reference.startswith(("http://", "https://", "urn:")):
                continue
            target = next(
                (item for item, path in schemas if path.name == Path(reference).name),
                None,
            )
            if target is not None:
                resources[urljoin(schema["$id"], reference)] = Resource.from_contents(
                    target
                )
    return Registry().with_resources(resources.items())


def _references(value: Any) -> list[str]:
    if isinstance(value, dict):
        references = [value["$ref"]] if isinstance(value.get("$ref"), str) else []
        for child in value.values():
            references.extend(_references(child))
        return references
    if isinstance(value, list):
        references: list[str] = []
        for child in value:
            references.extend(_references(child))
        return references
    return []


def validate_core_schemas(root: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    catalog = load_catalog(root)
    schemas = load_core_schemas(root)
    ids = {schema["$id"] for schema, _ in schemas}
    paths = {path.name for _, path in schemas}
    for schema, path in schemas:
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"metaschema failure {path.relative_to(root)}: {exc}")
        for reference in _references(schema):
            if reference.startswith(("http://", "https://", "urn:")):
                if reference not in ids:
                    errors.append(
                        f"unregistered reference in {path.relative_to(root)}: {reference}"
                    )
            elif Path(reference).name not in paths:
                errors.append(
                    f"missing local reference in {path.relative_to(root)}: {reference}"
                )
    actual_contract_set = contract_set_sha256(schemas)
    if catalog.get("contract_set_sha256") != actual_contract_set:
        errors.append(
            "contract_set_sha256 mismatch: "
            f"expected {catalog.get('contract_set_sha256')}, got {actual_contract_set}"
        )
    return errors, {
        "core_schemas": len(schemas),
        "contract_set_sha256": actual_contract_set,
        "metaschema": DRAFT_2020_12,
    }


def _first_top_level_property(schema: dict[str, Any], predicate: Any) -> str | None:
    for name, definition in schema.get("properties", {}).items():
        if isinstance(definition, dict) and predicate(definition):
            return name
    return None


def fixture_material(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    examples = schema.get("examples", [])
    if not isinstance(examples, list) or len(examples) < 2:
        raise ValueError(f"{schema.get('$id')}: two examples required")
    minimal = copy.deepcopy(examples[0])
    complete = copy.deepcopy(examples[1])
    first_required = schema["required"][0]
    non_version_required = next(
        name for name in schema["required"] if name != "schema_version"
    )
    enum_property = _first_top_level_property(schema, lambda item: "enum" in item)
    timestamp_property = _first_top_level_property(
        schema, lambda item: item.get("format") == "date-time"
    )
    if enum_property is None or timestamp_property is None:
        raise ValueError(
            f"{schema.get('$id')}: top-level enum and timestamp required for fixtures"
        )

    required_missing = copy.deepcopy(minimal)
    required_missing.pop(first_required)
    unknown_field = copy.deepcopy(minimal)
    unknown_field["unexpected_field"] = True
    enum_unknown = copy.deepcopy(minimal)
    enum_unknown[enum_property] = "unknown-enum-value"
    null_not_allowed = copy.deepcopy(minimal)
    null_not_allowed[non_version_required] = None
    timestamp_noncanonical = copy.deepcopy(minimal)
    timestamp_noncanonical[timestamp_property] = "2026-07-17T12:00:00Z"
    version_unknown = copy.deepcopy(minimal)
    version_unknown["schema_version"] = "9.9.9"
    return {
        "valid/minimal.json": minimal,
        "valid/complete.json": complete,
        "invalid/required-missing.json": required_missing,
        "invalid/unknown-field.json": unknown_field,
        "invalid/wrong-root-type.json": [],
        "invalid/enum-unknown.json": enum_unknown,
        "invalid/null-not-allowed.json": null_not_allowed,
        "invalid/timestamp-noncanonical.json": timestamp_noncanonical,
        "invalid/version-unknown.json": version_unknown,
    }


def generate_fixture_tree(root: Path, target: Path) -> None:
    for schema, path in load_core_schemas(root):
        schema_name = path.name.removesuffix(".schema.json")
        for relative, material in fixture_material(schema).items():
            output = target / schema_name / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(material, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )


def _run(command: list[str], *, root: Path) -> None:
    result = subprocess.run(
        command, cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}"
        )


def generate_python_models(root: Path, target: Path) -> None:
    executable = shutil.which("datamodel-codegen")
    if executable is None:
        raise RuntimeError("datamodel-codegen not available in locked environment")
    _run(
        [
            executable,
            "--input",
            "schemas/core/1.0.0",
            "--input-file-type",
            "jsonschema",
            "--output",
            str(target),
            "--output-model-type",
            "pydantic_v2.BaseModel",
            "--target-python-version",
            "3.12",
            "--strict-types",
            "str",
            "int",
            "float",
            "bool",
            "--extra-fields",
            "forbid",
            "--disable-timestamp",
            "--use-standard-collections",
            "--use-union-operator",
            "--use-title-as-name",
            "--formatters",
            "black",
            "isort",
        ],
        root=root,
    )
    exports: list[tuple[str, str]] = []
    for schema, path in load_core_schemas(root):
        module = path.name.removesuffix(".json").replace("-", "_").replace(".", "_")
        exports.append((module, schema["title"]))
    header = "# Generated from JSON Schema. DO NOT EDIT.\n"
    model_lines = [header]
    init_lines = [header]
    for module, title in sorted(exports):
        line = f"from .{module} import {title}\n"
        model_lines.append(line)
        init_lines.append(line)
    names = ", ".join(repr(title) for _, title in sorted(exports))
    model_lines.append(f"\n__all__ = [{names}]\n")
    init_lines.append(f"\n__all__ = [{names}]\n")
    (target / "models.py").write_text("".join(model_lines), encoding="utf-8")
    (target / "__init__.py").write_text("".join(init_lines), encoding="utf-8")


def generate_typescript_models(root: Path, target: Path) -> None:
    executable = root / "node_modules/.bin/json2ts"
    if not executable.is_file():
        raise RuntimeError("json2ts not available in locked environment")
    _run(
        [
            str(executable),
            "--input",
            "schemas/core/1.0.0",
            "--output",
            str(target),
            "--cwd",
            "schemas/core/1.0.0",
            "--unknownAny",
            "--no-enableConstEnums",
        ],
        root=root,
    )
    schemas = load_core_schemas(root)
    exports = [
        (path.name.removesuffix(".json"), schema["title"], path)
        for schema, path in schemas
    ]
    lines = ["// Generated from JSON Schema. DO NOT EDIT.\n"]
    fixture_lines = ["// Generated fixture type checks. DO NOT EDIT.\n"]
    for name, title, path in sorted(exports):
        lines.append(f"export type {{ {title} }} from './{name}';\n")
        fixture_lines.append(f"import type {{ {title} }} from './{name}';\n")
        schema = json.loads(path.read_text(encoding="utf-8"))
        for index, fixture in enumerate(schema["examples"]):
            variable = f"{title[0].lower()}{title[1:]}Fixture{index + 1}"
            material = json.dumps(fixture, ensure_ascii=False, sort_keys=True)
            fixture_lines.append(f"export const {variable}: {title} = {material};\n")
    (target / "models.d.ts").write_text("".join(lines), encoding="utf-8")
    (target / "fixture-check.ts").write_text("".join(fixture_lines), encoding="utf-8")
    (target / "tsconfig.json").write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "strict": True,
                    "noEmit": True,
                    "skipLibCheck": False,
                    "target": "ES2022",
                    "module": "NodeNext",
                    "moduleResolution": "NodeNext",
                },
                "include": ["*.ts", "*.d.ts"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def validate_typescript_models(root: Path) -> list[str]:
    executable = root / "node_modules/.bin/tsc"
    if not executable.is_file():
        return ["tsc not available in locked environment"]
    result = subprocess.run(
        [
            str(executable),
            "--project",
            "packages/contracts/generated/typescript/tsconfig.json",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return []
    return [
        f"TypeScript generated consumer check failed:\n{result.stdout}{result.stderr}"
    ]


def generate_assets(root: Path, target: Path) -> None:
    generate_fixture_tree(root, target / "fixtures")
    generate_python_models(root, target / "python")
    generate_typescript_models(root, target / "typescript")


def _tree_bytes(path: Path) -> dict[str, bytes]:
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file() and item.suffix != ".pyc" and "__pycache__" not in item.parts
    }


def sync_generated_assets(
    root: Path, *, check: bool
) -> tuple[list[str], dict[str, Any]]:
    with tempfile.TemporaryDirectory() as directory:
        generated = Path(directory)
        try:
            generate_assets(root, generated)
        except Exception as exc:
            return [str(exc)], {}
        mappings = {
            generated / "fixtures": root / "fixtures/contracts/core/1.0.0",
            generated / "python": root / "packages/contracts/generated/python",
            generated / "typescript": root / "packages/contracts/generated/typescript",
        }
        differences: list[str] = []
        for source, destination in mappings.items():
            if _tree_bytes(source) != _tree_bytes(destination):
                differences.append(str(destination.relative_to(root)))
                if not check:
                    if destination.exists():
                        shutil.rmtree(destination)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(source, destination)
        errors = (
            [f"generated assets differ: {', '.join(differences)}"]
            if check and differences
            else []
        )
        typescript_errors = [] if errors else validate_typescript_models(root)
        errors.extend(typescript_errors)
        return errors, {
            "fixture_files": len(_tree_bytes(generated / "fixtures")),
            "python_files": len(_tree_bytes(generated / "python")),
            "typescript_files": len(_tree_bytes(generated / "typescript")),
            "changed_targets": differences,
            "typescript_checked": not typescript_errors and not (check and differences),
        }


def validate_fixtures(root: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    schemas = load_core_schemas(root)
    registry = schema_registry(schemas)
    valid_count = 0
    invalid_count = 0
    for schema, schema_path in schemas:
        name = schema_path.name.removesuffix(".schema.json")
        base = root / "fixtures/contracts/core/1.0.0" / name
        validator = Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        valid_paths = sorted((base / "valid").glob("*.json"))
        invalid_paths = sorted((base / "invalid").glob("*.json"))
        if {path.name for path in valid_paths} != {"minimal.json", "complete.json"}:
            errors.append(f"{name}: minimal.json and complete.json required")
        if {path.name for path in invalid_paths} != INVALID_FIXTURE_NAMES:
            errors.append(f"{name}: invalid fixture matrix incomplete")
        for path in valid_paths:
            instance = json.loads(path.read_text(encoding="utf-8"))
            validation_errors = list(validator.iter_errors(instance))
            if validation_errors:
                errors.append(
                    f"{path.relative_to(root)} unexpectedly invalid: {validation_errors[0].message}"
                )
            valid_count += 1
        for path in invalid_paths:
            instance = json.loads(path.read_text(encoding="utf-8"))
            if not list(validator.iter_errors(instance)):
                errors.append(f"{path.relative_to(root)} unexpectedly valid")
            invalid_count += 1
    if not errors:
        errors.extend(validate_pydantic_fixtures(root))
    return errors, {
        "schemas": len(schemas),
        "valid_fixtures": valid_count,
        "invalid_fixtures": invalid_count,
    }


def validate_pydantic_fixtures(root: Path) -> list[str]:
    errors: list[str] = []
    sys.path.insert(0, str(root))
    try:
        for schema, path in load_core_schemas(root):
            name = path.name.removesuffix(".schema.json")
            module_name = (
                path.name.removesuffix(".json").replace("-", "_").replace(".", "_")
            )
            module = importlib.import_module(
                f"packages.contracts.generated.python.{module_name}"
            )
            model = getattr(module, schema["title"])
            for fixture in sorted(
                (root / "fixtures/contracts/core/1.0.0" / name / "valid").glob("*.json")
            ):
                try:
                    model.model_validate_json(
                        fixture.read_text(encoding="utf-8"), strict=True
                    )
                except Exception as exc:
                    errors.append(
                        f"{fixture.relative_to(root)} rejected by Pydantic: {exc}"
                    )
    finally:
        sys.path.remove(str(root))
    return errors


def validate_compatibility(root: Path) -> tuple[list[str], dict[str, Any]]:
    baseline_path = root / "schemas/core/compatibility-baseline.json"
    if not baseline_path.is_file():
        return ["schemas/core/compatibility-baseline.json missing"], {}
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    legacy = load_catalog(root, "schemas/legacy/catalog.json")
    core = load_catalog(root)
    errors: list[str] = []
    expected_legacy = [
        {"path": entry["path"], "sha256": entry["sha256"]}
        for entry in legacy["entries"]
    ]
    expected_core = [
        {"$id": entry["$id"], "sha256": entry["sha256"]} for entry in core["entries"]
    ]
    if baseline.get("legacy") != expected_legacy:
        errors.append("legacy compatibility baseline mismatch")
    if baseline.get("core") != expected_core:
        errors.append("core compatibility baseline mismatch")
    if baseline.get("contract_set_sha256") != core.get("contract_set_sha256"):
        errors.append("core contract set baseline mismatch")
    return errors, {
        "legacy_schemas": len(expected_legacy),
        "core_schemas": len(expected_core),
    }
