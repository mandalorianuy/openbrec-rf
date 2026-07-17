from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from openbrec.contracts import (sync_generated_assets, validate_compatibility,
                                validate_core_schemas, validate_fixtures)
from openbrec.gates_m0_04 import (
    run_adapter_replay,
    run_core_replay,
    run_determinism,
    run_life_safety_preservation,
    run_privacy,
    run_review_quarantine,
    run_security,
)

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
VERIFY_VERSION = "0.1.0"
RUNTIME_GATES = {"compose-build", "offline-startup"}
REPLAY_GATES = {"adapter-replay", "core-replay", "determinism"}
PRIVACY_SAFETY_GATES = {
    "review-quarantine",
    "life-safety-preservation",
    "privacy",
    "security",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_state(root: Path) -> dict[str, Any]:
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    sha_result = git("rev-parse", "HEAD")
    status_result = git("status", "--porcelain")
    return {
        "git_sha": sha_result.stdout.strip() if sha_result.returncode == 0 else None,
        "dirty": status_result.returncode != 0 or bool(status_result.stdout.strip()),
    }


def _lockfiles(root: Path) -> list[dict[str, str]]:
    paths = [root / name for name in ("uv.lock", "pnpm-lock.yaml")]
    return [
        {"path": str(path.relative_to(root)), "sha256": _sha256(path)}
        for path in paths
        if path.is_file()
    ]


def _resolve_inside(root: Path, value: str, *, label: str) -> Path:
    candidate = Path(value)
    resolved = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} is outside repository root: {value}") from exc
    return resolved


def _validate_catalog(
    root: Path, catalog_path: Path
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    summary: dict[str, Any] = {
        "catalog": str(catalog_path.relative_to(root)),
        "catalog_entries": 0,
    }
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"catalog unreadable: {exc}"], summary

    if not isinstance(catalog, dict):
        return ["catalog must be a JSON object"], summary
    if catalog.get("draft") != DRAFT_2020_12:
        errors.append(f"catalog draft must be {DRAFT_2020_12}")
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        return [*errors, "catalog entries must be an array"], summary

    summary["catalog_entries"] = len(entries)
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        path_value = entry.get("path")
        schema_id = entry.get("$id")
        expected_hash = entry.get("sha256")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{prefix}.path must be a non-empty string")
            continue
        if path_value in seen_paths:
            errors.append(f"duplicate catalog path: {path_value}")
        seen_paths.add(path_value)
        if not isinstance(schema_id, str) or not schema_id:
            errors.append(f"{prefix}.$id must be a non-empty string")
        elif schema_id in seen_ids:
            errors.append(f"duplicate schema $id: {schema_id}")
        else:
            seen_ids.add(schema_id)
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or expected_hash != expected_hash.lower()
        ):
            errors.append(
                f"{prefix}.sha256 must be 64 lowercase hexadecimal characters"
            )
            continue
        try:
            int(expected_hash, 16)
        except ValueError:
            errors.append(
                f"{prefix}.sha256 must be 64 lowercase hexadecimal characters"
            )
            continue
        try:
            schema_path = _resolve_inside(root, path_value, label=f"{prefix}.path")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not schema_path.is_file():
            errors.append(f"schema file not found: {path_value}")
            continue
        actual_hash = _sha256(schema_path)
        if actual_hash != expected_hash:
            errors.append(
                f"sha256 mismatch for {path_value}: expected {expected_hash}, got {actual_hash}"
            )
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"schema unreadable {path_value}: {exc}")
            continue
        if not isinstance(schema, dict):
            errors.append(f"schema must be a JSON object: {path_value}")
            continue
        if schema.get("$schema") != DRAFT_2020_12:
            errors.append(f"schema draft mismatch for {path_value}")
        if schema.get("$id") != schema_id:
            errors.append(f"schema $id mismatch for {path_value}")
    return errors, summary


def _run_bundle_structure(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    validator = root / "scripts/validate_bundle.py"
    if not validator.is_file():
        return ["scripts/validate_bundle.py not found"], [], {}
    result = subprocess.run(
        [sys.executable, str(validator)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    summary = {
        "legacy_validator": "scripts/validate_bundle.py",
        "legacy_validator_sha256": _sha256(validator),
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    errors = [] if result.returncode == 0 else ["legacy structural validator failed"]
    warnings = [
        line[2:] for line in result.stdout.splitlines() if line.startswith("- ")
    ]
    return errors, warnings, summary


def _compose_environment() -> dict[str, str]:
    return {
        **os.environ,
        "OPENBREC_POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "COMPOSE_MENU": "false",
    }


def _compose_command(
    root: Path, args: Sequence[str], *, environment: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_compose_build(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    environment = _compose_environment()
    config = _compose_command(
        root, ["--profile", "lab-sim", "config", "--quiet"], environment=environment
    )
    summary: dict[str, Any] = {
        "compose_config_exit_code": config.returncode,
        "infrastructure_pull_exit_code": None,
        "compose_build_exit_code": None,
        "services": ["mqtt", "postgres", "api", "fusion-worker", "web"],
    }
    errors: list[str] = []
    warnings = [line for line in config.stderr.splitlines() if line.strip()]
    if config.returncode != 0:
        errors.append(f"docker compose config failed: {config.stderr.strip()}")
        return errors, warnings, summary
    pull = _compose_command(
        root,
        ["--profile", "lab-sim", "pull", "mqtt", "postgres"],
        environment=environment,
    )
    summary["infrastructure_pull_exit_code"] = pull.returncode
    if pull.returncode != 0:
        errors.append(f"infrastructure image pull failed: {pull.stderr.strip()}")
        return errors, warnings, summary
    build = _compose_command(
        root, ["--profile", "lab-sim", "build"], environment=environment
    )
    summary["compose_build_exit_code"] = build.returncode
    summary["build_output_tail"] = build.stdout.splitlines()[-20:]
    warnings.extend(line for line in build.stderr.splitlines() if "warning" in line.lower())
    if build.returncode != 0:
        errors.append(f"docker compose build failed: {build.stderr.strip()}")
    return errors, warnings, summary


def _run_offline_startup(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    environment = _compose_environment()
    base = ["--profile", "lab-sim"]
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {
        "startup_exit_code": None,
        "smoke_exit_code": None,
        "shutdown_exit_code": None,
        "external_network": "not_checked",
    }
    try:
        startup = _compose_command(
            root,
            [
                *base,
                "up",
                "--detach",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "90",
            ],
            environment=environment,
        )
        summary["startup_exit_code"] = startup.returncode
        warnings.extend(
            line for line in startup.stderr.splitlines() if "warning" in line.lower()
        )
        if startup.returncode != 0:
            errors.append(f"offline compose startup failed: {startup.stderr.strip()}")
            return errors, warnings, summary

        smoke = _compose_command(
            root,
            [
                "--profile",
                "lab-sim",
                "--profile",
                "m0-gate",
                "run",
                "--rm",
                "--no-deps",
                "runtime-smoke",
            ],
            environment=environment,
        )
        summary["smoke_exit_code"] = smoke.returncode
        summary["smoke_output"] = smoke.stdout.strip()
        if smoke.returncode != 0:
            errors.append(f"runtime smoke failed: {smoke.stderr.strip()}")
        else:
            try:
                smoke_result = json.loads(smoke.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                errors.append("runtime smoke did not emit a JSON result")
            else:
                summary.update(smoke_result)
                if smoke_result.get("external_network") != "denied":
                    errors.append("runtime smoke did not prove external network denial")
    finally:
        shutdown = _compose_command(
            root,
            [*base, "down", "--volumes", "--remove-orphans"],
            environment=environment,
        )
        summary["shutdown_exit_code"] = shutdown.returncode
        if shutdown.returncode != 0:
            errors.append(f"compose cleanup failed: {shutdown.stderr.strip()}")
    return errors, warnings, summary


def _write_receipt(
    *,
    root: Path,
    receipt_value: str,
    gate: str,
    scope: str,
    command: Sequence[str],
    started_at: str,
    errors: list[str],
    warnings: list[str],
    summary: dict[str, Any],
    inputs: list[Path],
) -> None:
    receipt_path = Path(receipt_value)
    if not receipt_path.is_absolute():
        receipt_path = root / receipt_path
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    state = _repository_state(root)
    receipt = {
        "receipt_version": "1.0.0",
        "gate": gate,
        "gate_version": VERIFY_VERSION,
        "scope": scope,
        "result": "failed" if errors else "passed",
        **state,
        "runtime": {"python": sys.version.split()[0]},
        "lockfiles": _lockfiles(root),
        "command": list(command),
        "inputs": [
            {"path": str(path.relative_to(root)), "sha256": _sha256(path)}
            for path in inputs
            if path.is_file() and path.is_relative_to(root)
        ],
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "responsible_role": (
            "runtime-maintainer"
            if gate in RUNTIME_GATES
            else "core-replay-maintainer"
            if gate in REPLAY_GATES
            else "privacy-safety-reviewer"
            if gate in PRIVACY_SAFETY_GATES
            else "contract-maintainer"
        ),
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m openbrec.verify")
    subparsers = parser.add_subparsers(dest="gate", required=True)
    for gate in (
        "bundle-structure",
        "schema",
        "fixtures",
        "schema-compat",
        "contracts-gen",
        "compose-build",
        "offline-startup",
        "adapter-replay",
        "core-replay",
        "determinism",
        "review-quarantine",
        "life-safety-preservation",
        "privacy",
        "security",
    ):
        subparser = subparsers.add_parser(gate)
        subparser.add_argument("--root", default=".")
        subparser.add_argument("--receipt")
        if gate == "schema":
            subparser.add_argument("--catalog")
        if gate == "contracts-gen":
            subparser.add_argument("--check", action="store_true")
        if gate == "determinism":
            subparser.add_argument("--runs", type=int, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    inputs: list[Path] = []
    if args.gate == "bundle-structure":
        errors, warnings, summary = _run_bundle_structure(root)
        inputs.append(root / "scripts/validate_bundle.py")
        scope = "structural_only"
    elif args.gate == "schema" and args.catalog:
        try:
            catalog_path = _resolve_inside(root, args.catalog, label="catalog")
            inputs.append(catalog_path)
            errors, summary = _validate_catalog(root, catalog_path)
        except ValueError as exc:
            errors, summary = [str(exc)], {
                "catalog": args.catalog,
                "catalog_entries": 0,
            }
        warnings = []
        scope = "catalog_integrity_only"
    elif args.gate == "schema":
        catalog_errors, catalog_summary = _validate_catalog(
            root, root / "schemas/core/catalog.json"
        )
        errors, summary = validate_core_schemas(root)
        errors = [*catalog_errors, *errors]
        summary = {**catalog_summary, **summary}
        warnings = []
        scope = "metaschema_and_catalog"
        inputs.append(root / "schemas/core/catalog.json")
    elif args.gate == "fixtures":
        errors, summary = validate_fixtures(root)
        warnings = []
        scope = "schema_fixture_matrix"
        inputs.append(root / "schemas/core/catalog.json")
    elif args.gate == "schema-compat":
        errors, summary = validate_compatibility(root)
        warnings = []
        scope = "immutable_baseline"
        inputs.append(root / "schemas/core/compatibility-baseline.json")
    elif args.gate == "compose-build":
        errors, warnings, summary = _run_compose_build(root)
        scope = "lab_sim_images"
        inputs.extend(
            [
                root / "docker-compose.yml",
                root / "apps/api/Dockerfile",
                root / "apps/web/Dockerfile",
                root / "apps/web/pnpm-lock.yaml",
                root / "uv.lock",
            ]
        )
    elif args.gate == "offline-startup":
        errors, warnings, summary = _run_offline_startup(root)
        scope = "contained_lab_sim_runtime"
        inputs.extend(
            [
                root / "docker-compose.yml",
                root / "config/mosquitto/lab-sim.conf",
                root / "schemas/core/catalog.json",
            ]
        )
    elif args.gate == "adapter-replay":
        errors, warnings, summary = run_adapter_replay(root)
        scope = "adapter_fixture_to_domain_events"
        inputs.extend(
            [
                root / "fixtures/replay/adapter/synthetic-observation.bundle.json",
                root / "openbrec/replay.py",
                root / "openbrec/semantic.py",
            ]
        )
    elif args.gate == "core-replay":
        errors, warnings, summary = run_core_replay(root)
        scope = "domain_events_to_derived_outputs"
        inputs.extend(
            [
                root / "fixtures/replay/core/synthetic-observation.events.json",
                root / "fixtures/replay/failure-cases.json",
                root / "openbrec/replay.py",
                root / "openbrec/semantic.py",
            ]
        )
    elif args.gate == "determinism":
        errors, warnings, summary = run_determinism(root, args.runs)
        scope = "replay_result_hash_stability"
        inputs.extend(
            [
                root / "fixtures/replay/adapter/synthetic-observation.bundle.json",
                root / "openbrec/canonical.py",
                root / "openbrec/replay.py",
            ]
        )
    elif args.gate == "review-quarantine":
        errors, warnings, summary = run_review_quarantine(root)
        scope = "exactly_one_primary_disposition"
        inputs.extend(
            [
                root / "fixtures/replay/core/synthetic-observation.events.json",
                root / "openbrec/disposition.py",
                root / "migrations/0001_m0_disposition.sql",
            ]
        )
    elif args.gate == "life-safety-preservation":
        errors, warnings, summary = run_life_safety_preservation(root)
        scope = "sealed_audited_ttl_preservation"
        inputs.extend(
            [
                root / "openbrec/disposition.py",
                root / "migrations/0001_m0_disposition.sql",
            ]
        )
    elif args.gate == "privacy":
        errors, warnings, summary = run_privacy(root)
        scope = "sensitive_cleartext_minimization"
        inputs.extend(
            [
                root / "openbrec/disposition.py",
                root / "migrations/0001_m0_disposition.sql",
            ]
        )
    elif args.gate == "security":
        errors, warnings, summary = run_security(root)
        scope = "tamper_and_fail_closed"
        inputs.extend(
            [
                root / "openbrec/canonical.py",
                root / "openbrec/disposition.py",
                root / "openbrec/replay.py",
                root / "openbrec/semantic.py",
                root / "migrations/0001_m0_disposition.sql",
            ]
        )
    else:
        errors, summary = sync_generated_assets(root, check=args.check)
        warnings = []
        scope = "generated_consumers"
        inputs.append(root / "schemas/core/catalog.json")

    if args.receipt:
        _write_receipt(
            root=root,
            receipt_value=args.receipt,
            gate=args.gate,
            scope=scope,
            command=[
                "python",
                "-m",
                "openbrec.verify",
                *(argv if argv is not None else sys.argv[1:]),
            ],
            started_at=started_at,
            errors=errors,
            warnings=warnings,
            summary=summary,
            inputs=inputs,
        )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"gate": args.gate, "result": "passed", "scope": scope, "summary": summary},
            sort_keys=True,
        )
    )
    return 0
