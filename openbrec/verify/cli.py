from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from openbrec.contracts import (
    sync_generated_assets,
    validate_addon_fixtures,
    validate_addon_schemas,
    validate_compatibility,
    validate_core_schemas,
    validate_fixtures,
)
from openbrec.gates_m0_04 import (
    run_adapter_replay,
    run_core_replay,
    run_determinism,
    run_life_safety_preservation,
    run_privacy,
    run_review_quarantine,
    run_security,
)
from openbrec.gates_m0_05 import (
    run_core_scenario_gate,
    run_simulator_gate,
    run_ui_smoke_gate,
)
from openbrec.gates_m0_06 import (
    build_sbom,
    run_key_lifecycle_gate,
    run_license_gate,
    run_secret_scan,
    run_vulnerability_gate,
    write_sbom,
)
from openbrec.canonical import canonical_hash
from openbrec.energy import run_energy_replay_gate
from openbrec.messaging import SCENARIO_PATH as MESSAGE_SCENARIO_PATH
from openbrec.messaging import run_p0_message_gate
from openbrec.transports import WORKLOAD_PATH as TRANSPORT_WORKLOAD_PATH
from openbrec.transports import run_transport_gate
from openbrec.federation import SCENARIO_PATH as FEDERATION_SCENARIO_PATH
from openbrec.federation import run_federation_gate
from openbrec.terminal import PUBLIC_PROJECTION_PATH as TERMINAL_PUBLIC_PATH
from openbrec.terminal import P1A_PROTOCOL_PATH, SCENARIO_PATH as TERMINAL_SCENARIO_PATH
from openbrec.terminal import run_accessibility_gate, run_terminal_gate

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
VERIFY_VERSION = "0.1.0"
RUNTIME_GATES = {"compose-build", "offline-startup", "postgres-disposition"}
REPLAY_GATES = {"adapter-replay", "core-replay", "determinism"}
ENERGY_GATES = {"energy-replay"}
P0_MESSAGE_GATES = {
    "human-message-security",
    "sos-state-replay",
    "transport-policy",
}
P0_TRANSPORT_GATES = {"transport-comparison", "malicious-transport"}
P0_FEDERATION_GATES = {"federation-scale", "federation-reconciliation"}
P0_TERMINAL_GATES = {"terminal-ux", "accessibility"}
PRIVACY_SAFETY_GATES = {
    "review-quarantine",
    "life-safety-preservation",
    "privacy",
    "security",
    "key-lifecycle",
    "secret-scan",
    *P0_MESSAGE_GATES,
}
ALL_GATES = (
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
    "simulator",
    "ui-smoke",
    "key-lifecycle",
    "postgres-disposition",
    "secret-scan",
    "sbom",
    "licenses",
    "vulnerability-scan",
)


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
    paths = [
        root / "uv.lock",
        root / "pnpm-lock.yaml",
        root / "apps/web/pnpm-lock.yaml",
    ]
    return [
        {"path": str(path.relative_to(root)), "sha256": _sha256(path)}
        for path in paths
        if path.is_file()
    ]


def _runtime_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": sys.version.split()[0]}
    for name, command in (
        ("node", ["node", "--version"]),
        ("pnpm", ["pnpm", "--version"]),
        ("docker", ["docker", "--version"]),
    ):
        try:
            result = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
        except OSError:
            versions[name] = None
        else:
            versions[name] = result.stdout.strip() if result.returncode == 0 else None
    return versions


def _responsible_role(gate: str) -> str:
    if gate in RUNTIME_GATES or gate == "ui-smoke":
        return "runtime-maintainer"
    if gate in REPLAY_GATES or gate == "simulator":
        return "core-replay-maintainer"
    if gate in ENERGY_GATES:
        return "energy-maintainer"
    if gate in P0_TRANSPORT_GATES:
        return "radio-transport-maintainer"
    if gate in P0_FEDERATION_GATES:
        return "federation-maintainer"
    if gate == "terminal-ux":
        return "product-ux-reviewer"
    if gate == "accessibility":
        return "privacy-safety-reviewer"
    if gate in PRIVACY_SAFETY_GATES:
        return "privacy-safety-reviewer"
    return "contract-maintainer"


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
    secret_directory = Path(tempfile.mkdtemp(prefix="openbrec-compose-secrets-"))
    postgres_secret = secret_directory / "postgres_password"
    master_key_secret = secret_directory / "openbrec_master_key"
    postgres_password = secrets.token_urlsafe(32)
    master_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    postgres_secret.write_text(postgres_password, encoding="utf-8")
    master_key_secret.write_text(master_key, encoding="utf-8")
    postgres_secret.chmod(0o444)
    master_key_secret.chmod(0o444)
    return {
        **os.environ,
        "OPENBREC_POSTGRES_PASSWORD": postgres_password,
        "OPENBREC_MASTER_KEY_B64": master_key,
        "OPENBREC_POSTGRES_PASSWORD_FILE_HOST": str(postgres_secret),
        "OPENBREC_MASTER_KEY_FILE_HOST": str(master_key_secret),
        "COMPOSE_MENU": "false",
    }


def _cleanup_compose_environment(environment: dict[str, str]) -> None:
    secret_path = environment.get("OPENBREC_POSTGRES_PASSWORD_FILE_HOST")
    if secret_path:
        shutil.rmtree(Path(secret_path).parent, ignore_errors=True)


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
    summary: dict[str, Any] = {
        "compose_config_exit_code": None,
        "infrastructure_pull_exit_code": None,
        "compose_build_exit_code": None,
        "services": ["mqtt", "postgres", "api", "fusion-worker", "web"],
    }
    errors: list[str] = []
    warnings: list[str] = []
    try:
        config = _compose_command(
            root,
            ["--profile", "lab-sim", "config", "--quiet"],
            environment=environment,
        )
        summary["compose_config_exit_code"] = config.returncode
        warnings.extend(line for line in config.stderr.splitlines() if line.strip())
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
        warnings.extend(
            line for line in build.stderr.splitlines() if "warning" in line.lower()
        )
        if build.returncode != 0:
            errors.append(f"docker compose build failed: {build.stderr.strip()}")
        return errors, warnings, summary
    finally:
        _cleanup_compose_environment(environment)


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
            logs = _compose_command(
                root,
                [*base, "logs", "--no-color", "fusion-worker", "postgres"],
                environment=environment,
            )
            summary["failure_logs"] = logs.stdout.splitlines()[-100:]
            errors.append(
                "offline compose startup failed: "
                f"{startup.stderr.strip()}\nservice logs:\n{logs.stdout.strip()}"
            )
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
                if smoke_result.get("postgres_durable") != "passed":
                    errors.append("runtime smoke did not prove PostgreSQL durability")
                if smoke_result.get("unreconciled") != 0:
                    errors.append("runtime smoke found unreconciled disposition units")
    finally:
        shutdown = _compose_command(
            root,
            [*base, "down", "--volumes", "--remove-orphans"],
            environment=environment,
        )
        summary["shutdown_exit_code"] = shutdown.returncode
        if shutdown.returncode != 0:
            errors.append(f"compose cleanup failed: {shutdown.stderr.strip()}")
        _cleanup_compose_environment(environment)
    return errors, warnings, summary


def _run_postgres_disposition(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    environment = _compose_environment()
    errors: list[str] = []
    warnings: list[str] = []
    summary: dict[str, Any] = {
        "startup_exit_code": None,
        "gate_exit_code": None,
        "shutdown_exit_code": None,
    }
    try:
        startup = _compose_command(
            root,
            [
                "--profile",
                "lab-sim",
                "up",
                "--detach",
                "--no-build",
                "--pull",
                "never",
                "--wait",
                "--wait-timeout",
                "60",
                "postgres",
            ],
            environment=environment,
        )
        summary["startup_exit_code"] = startup.returncode
        if startup.returncode != 0:
            errors.append(f"PostgreSQL startup failed: {startup.stderr.strip()}")
            return errors, warnings, summary
        gate = _compose_command(
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
                "python",
                "-m",
                "openbrec.postgres_gate",
            ],
            environment=environment,
        )
        summary["gate_exit_code"] = gate.returncode
        if gate.returncode != 0:
            errors.append(f"PostgreSQL disposition gate failed: {gate.stderr.strip()}")
        else:
            try:
                summary.update(json.loads(gate.stdout.strip().splitlines()[-1]))
            except (IndexError, json.JSONDecodeError):
                errors.append("PostgreSQL disposition gate emitted no JSON result")
    finally:
        shutdown = _compose_command(
            root,
            ["--profile", "lab-sim", "down", "--volumes", "--remove-orphans"],
            environment=environment,
        )
        summary["shutdown_exit_code"] = shutdown.returncode
        if shutdown.returncode != 0:
            errors.append(f"PostgreSQL cleanup failed: {shutdown.stderr.strip()}")
        _cleanup_compose_environment(environment)
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
        "runtime": _runtime_versions(),
        "lockfiles": _lockfiles(root),
        "command": list(command),
        "inputs": [
            {"path": str(path.relative_to(root)), "sha256": _sha256(path)}
            for path in inputs
            if path.is_file() and path.is_relative_to(root)
        ],
        "summary": summary,
        "output_sha256": canonical_hash(
            {
                "result": "failed" if errors else "passed",
                "summary": summary,
                "errors": errors,
                "warnings": warnings,
            }
        ),
        "errors": errors,
        "warnings": warnings,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "responsible_role": _responsible_role(gate),
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def validate_receipt(
    receipt_path: Path,
    *,
    expected_git_sha: str | None,
    require_clean: bool,
) -> list[str]:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"receipt unreadable: {receipt_path}: {exc}"]
    errors: list[str] = []
    if expected_git_sha and receipt.get("git_sha") != expected_git_sha:
        errors.append(
            f"receipt git_sha mismatch: {receipt.get('git_sha')} != {expected_git_sha}"
        )
    if require_clean and receipt.get("dirty") is not False:
        errors.append("receipt was not evaluated from a clean checkout")
    for field in ("runtime", "lockfiles", "inputs"):
        if not receipt.get(field):
            errors.append(f"receipt has no {field} evidence")
    expected_output = canonical_hash(
        {
            "result": receipt.get("result"),
            "summary": receipt.get("summary"),
            "errors": receipt.get("errors"),
            "warnings": receipt.get("warnings"),
        }
    )
    if receipt.get("output_sha256") != expected_output:
        errors.append("receipt output_sha256 does not match canonical gate output")
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m openbrec.verify")
    subparsers = parser.add_subparsers(dest="gate", required=True)
    for gate in (
        "bundle-structure",
        "schema",
        "fixtures",
        "addon-contracts",
        "addon-fixtures",
        "schema-compat",
        "contracts-gen",
        "compose-build",
        "offline-startup",
        "adapter-replay",
        "core-replay",
        "determinism",
        "energy-replay",
        "human-message-security",
        "sos-state-replay",
        "transport-policy",
        "transport-comparison",
        "malicious-transport",
        "federation-scale",
        "federation-reconciliation",
        "terminal-ux",
        "accessibility",
        "review-quarantine",
        "life-safety-preservation",
        "privacy",
        "security",
        "simulator",
        "ui-smoke",
        "secret-scan",
        "sbom",
        "licenses",
        "vulnerability-scan",
        "key-lifecycle",
        "postgres-disposition",
        "all",
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
        if gate == "simulator":
            subparser.add_argument("--scenario", required=True)
        if gate == "energy-replay":
            subparser.add_argument("--scenario", required=True)
        if gate == "transport-comparison":
            subparser.add_argument("--workload", required=True)
        if gate == "federation-scale":
            subparser.add_argument("--scenario", required=True)
        if gate == "core-replay":
            subparser.add_argument("--bundle")
        if gate == "sbom":
            subparser.add_argument("--output")
        if gate == "all":
            subparser.add_argument("--evidence-dir", default="evidence/m0")
            subparser.add_argument("--plan-only", action="store_true")
    return parser


def _all_arguments(gate: str, temporary: Path) -> list[str]:
    if gate == "contracts-gen":
        return ["--check"]
    if gate == "determinism":
        return ["--runs", "10"]
    if gate == "simulator":
        return ["--scenario", "fixtures/replay/core/m0-six-node.json"]
    if gate == "sbom":
        return ["--output", str(temporary / "sbom/openbrec-m0.cdx.json")]
    return []


def _run_all(root: Path, evidence_dir: str) -> tuple[int, dict[str, Any]]:
    target = Path(evidence_dir)
    if not target.is_absolute():
        target = root / target
    gate_results: list[dict[str, Any]] = []
    state = _repository_state(root)
    with tempfile.TemporaryDirectory(prefix="openbrec-m0-exit-") as directory:
        temporary = Path(directory)
        for gate in ALL_GATES:
            receipt = temporary / gate / "m0-06-receipt.json"
            command = [
                sys.executable,
                "-m",
                "openbrec.verify",
                gate,
                "--root",
                str(root),
                *_all_arguments(gate, temporary),
                "--receipt",
                str(receipt),
            ]
            result = subprocess.run(
                command, cwd=root, text=True, capture_output=True, check=False
            )
            integrity_errors = validate_receipt(
                receipt,
                expected_git_sha=state["git_sha"],
                require_clean=True,
            )
            gate_results.append(
                {
                    "gate": gate,
                    "exit_code": result.returncode,
                    "receipt": str(receipt.relative_to(temporary)),
                    "receipt_integrity": (
                        "passed" if not integrity_errors else "failed"
                    ),
                    "integrity_errors": integrity_errors,
                }
            )
        manifest = {
            "manifest_version": "1.0.0",
            "result": (
                "passed"
                if all(
                    item["exit_code"] == 0 and item["receipt_integrity"] == "passed"
                    for item in gate_results
                )
                else "failed"
            ),
            "gates": gate_results,
        }
        (temporary / "m0-exit-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(temporary, target, dirs_exist_ok=True)
    return (0 if manifest["result"] == "passed" else 1), manifest


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.gate == "all" and args.plan_only:
        print(json.dumps({"result": "planned", "gates": list(ALL_GATES)}))
        return 0
    if args.gate == "all":
        exit_code, manifest = _run_all(root, args.evidence_dir)
        print(json.dumps(manifest, sort_keys=True))
        return exit_code
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
            errors, summary = (
                [str(exc)],
                {
                    "catalog": args.catalog,
                    "catalog_entries": 0,
                },
            )
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
    elif args.gate == "addon-contracts":
        catalog_errors, catalog_summary = _validate_catalog(
            root, root / "schemas/addons/catalog.json"
        )
        errors, summary = validate_addon_schemas(root)
        errors = [*catalog_errors, *errors]
        summary = {**catalog_summary, **summary}
        warnings = []
        scope = "addon_metaschema_and_catalog"
        inputs.append(root / "schemas/addons/catalog.json")
    elif args.gate == "addon-fixtures":
        errors, summary = validate_addon_fixtures(root)
        warnings = []
        scope = "addon_schema_fixture_matrix"
        inputs.append(root / "schemas/addons/catalog.json")
    elif args.gate == "schema-compat":
        errors, summary = validate_compatibility(root)
        warnings = []
        scope = "immutable_baseline"
        inputs.append(root / "schemas/core/compatibility-baseline.json")
        inputs.append(root / "schemas/addons/compatibility-baseline.json")
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
    elif args.gate == "core-replay" and args.bundle:
        try:
            bundle_path = _resolve_inside(root, args.bundle, label="bundle")
            errors, warnings, summary = run_core_scenario_gate(root, bundle_path)
            inputs.extend(
                [
                    bundle_path,
                    root / "openbrec/simulator.py",
                    root / "openbrec/canonical.py",
                ]
            )
        except (OSError, ValueError) as exc:
            errors, warnings, summary = [str(exc)], [], {"bundle": args.bundle}
        scope = "scenario_semantic_replay"
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
    elif args.gate == "energy-replay":
        try:
            scenario_path = _resolve_inside(root, args.scenario, label="scenario")
            errors, warnings, summary = run_energy_replay_gate(root, scenario_path)
            inputs.extend(
                [
                    scenario_path,
                    root / "openbrec/energy.py",
                    root / "schemas/addons/1.0.0/energy-budget.schema.json",
                    root / "schemas/addons/1.0.0/energy-status.schema.json",
                ]
            )
        except (OSError, ValueError) as exc:
            errors, warnings, summary = [str(exc)], [], {"scenario": args.scenario}
        scope = "three_domain_energy_replay"
    elif args.gate in P0_MESSAGE_GATES:
        errors, warnings, summary = run_p0_message_gate(root, args.gate)
        scope = {
            "human-message-security": "application_authenticity_aead_and_offline_rekey",
            "sos-state-replay": "append_only_distress_state_derivation",
            "transport-policy": "hostile_bearer_deduplication_and_anti_loop",
        }[args.gate]
        inputs.extend(
            [
                root / MESSAGE_SCENARIO_PATH,
                root / "openbrec/messaging.py",
                root / "schemas/addons/1.0.0/human-message.schema.json",
                root / "schemas/addons/1.0.0/human-message-event.schema.json",
                root / "schemas/addons/1.0.0/transport-envelope.schema.json",
                root / "schemas/addons/1.0.0/transport-policy-decision.schema.json",
            ]
        )
    elif args.gate in P0_TRANSPORT_GATES:
        try:
            workload_path = (
                _resolve_inside(root, args.workload, label="workload")
                if args.gate == "transport-comparison"
                else root / TRANSPORT_WORKLOAD_PATH
            )
            errors, warnings, summary = run_transport_gate(
                root, args.gate, workload_path
            )
            inputs.extend(
                [
                    workload_path,
                    root / "openbrec/transports.py",
                    root / "openbrec/messaging.py",
                    root / "schemas/addons/1.0.0/transport-profile.schema.json",
                    root / "schemas/addons/1.0.0/transport-envelope.schema.json",
                ]
            )
        except (OSError, ValueError) as exc:
            errors, warnings, summary = [str(exc)], [], {
                "workload": str(getattr(args, "workload", TRANSPORT_WORKLOAD_PATH))
            }
        scope = {
            "transport-comparison": "versioned_common_envelope_transport_models",
            "malicious-transport": "hostile_transport_disposition_and_safety_boundary",
        }[args.gate]
    elif args.gate in P0_FEDERATION_GATES:
        try:
            scenario_path = (
                _resolve_inside(root, args.scenario, label="scenario")
                if args.gate == "federation-scale"
                else root / FEDERATION_SCENARIO_PATH
            )
            errors, warnings, summary = run_federation_gate(
                root, args.gate, scenario_path
            )
            inputs.extend(
                [
                    scenario_path,
                    root / "openbrec/federation.py",
                    root / "schemas/addons/1.0.0/federation-event.schema.json",
                    root
                    / "schemas/addons/1.0.0/federation-topology-event.schema.json",
                ]
            )
        except (OSError, ValueError) as exc:
            errors, warnings, summary = [str(exc)], [], {
                "scenario": str(
                    getattr(args, "scenario", FEDERATION_SCENARIO_PATH)
                )
            }
        scope = {
            "federation-scale": "generated_50k_hierarchy_and_recursive_autonomy",
            "federation-reconciliation": "append_only_partition_and_hostile_hub_reconciliation",
        }[args.gate]
    elif args.gate in P0_TERMINAL_GATES:
        if args.gate == "terminal-ux":
            errors, warnings, summary = run_terminal_gate(root)
            scope = "offline_human_terminal_event_derived_states"
        else:
            errors, warnings, summary = run_accessibility_gate(root)
            scope = "technical_accessibility_without_human_claim"
        inputs.extend(
            [
                root / TERMINAL_SCENARIO_PATH,
                root / TERMINAL_PUBLIC_PATH,
                root / P1A_PROTOCOL_PATH,
                root / "openbrec/terminal.py",
                root / "schemas/addons/1.0.0/terminal-capability.schema.json",
                root / "apps/web/src/main.tsx",
                root / "apps/web/src/style.css",
                root / "apps/web/public/sw.js",
                root / "apps/web/scripts/ui-smoke.mjs",
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
    elif args.gate == "simulator":
        try:
            scenario_path = _resolve_inside(root, args.scenario, label="scenario")
            errors, warnings, summary = run_simulator_gate(root, scenario_path)
            inputs.extend(
                [
                    scenario_path,
                    root / "openbrec/simulator.py",
                    root / "openbrec/canonical.py",
                ]
            )
        except (OSError, ValueError) as exc:
            errors, warnings, summary = [str(exc)], [], {"scenario": args.scenario}
        scope = "six_node_logical_campaign"
    elif args.gate == "ui-smoke":
        errors, warnings, summary = run_ui_smoke_gate(root)
        scope = "explainable_offline_pwa"
        inputs.extend(
            [
                root / "apps/web/src/main.tsx",
                root / "apps/web/src/style.css",
                root / "apps/web/index.html",
                root / "apps/web/package.json",
                root / "apps/web/pnpm-lock.yaml",
                root / "apps/web/public/favicon.svg",
                root / "apps/web/public/m0-projection.json",
                root / "apps/web/public/p0-terminal.json",
                root / "apps/web/public/sw.js",
                root / "apps/web/scripts/ui-smoke.mjs",
                root / "docker-compose.yml",
                root / "fixtures/replay/core/m0-six-node.json",
                root / "fixtures/p0/terminal/offline-terminal.json",
            ]
        )
    elif args.gate == "secret-scan":
        errors, warnings, summary = run_secret_scan(root)
        scope = "tracked_source_high_confidence_secrets"
        inputs.extend([root / ".gitignore", root / "openbrec/supply_chain.py"])
    elif args.gate == "sbom":
        sbom = build_sbom(root)
        if args.output:
            output_path = Path(args.output)
            if not output_path.is_absolute():
                output_path = root / output_path
            write_sbom(root, output_path)
        errors, warnings = [], []
        summary = {
            "format": "CycloneDX",
            "spec_version": sbom["specVersion"],
            "components": len(sbom["components"]),
            "sbom_sha256": canonical_hash(sbom),
            "output": str(args.output) if args.output else None,
        }
        scope = "installed_locked_component_inventory"
        inputs.extend(
            [
                root / "uv.lock",
                root / "pnpm-lock.yaml",
                root / "apps/web/pnpm-lock.yaml",
            ]
        )
    elif args.gate == "licenses":
        errors, warnings, summary = run_license_gate(root)
        scope = "installed_component_license_policy"
        inputs.extend(
            [
                root / "uv.lock",
                root / "pnpm-lock.yaml",
                root / "apps/web/pnpm-lock.yaml",
            ]
        )
    elif args.gate == "vulnerability-scan":
        errors, warnings, summary = run_vulnerability_gate(root)
        scope = "current_locked_dependency_advisories"
        inputs.extend(
            [
                root / "uv.lock",
                root / "pnpm-lock.yaml",
                root / "apps/web/pnpm-lock.yaml",
            ]
        )
    elif args.gate == "key-lifecycle":
        errors, warnings, summary = run_key_lifecycle_gate(root)
        scope = "lab_key_rotation_recovery_and_rollback"
        inputs.extend([root / "openbrec/keyring.py", root / "openbrec/disposition.py"])
    elif args.gate == "postgres-disposition":
        errors, warnings, summary = _run_postgres_disposition(root)
        scope = "postgres_four_destination_runtime_boundary"
        inputs.extend(
            [
                root / "docker-compose.yml",
                root / "openbrec/postgres_disposition.py",
                root / "migrations/postgresql/0001_m0_disposition.sql",
                root / "apps/fusion-worker/openbrec_worker/worker.py",
            ]
        )
    else:
        errors, summary = sync_generated_assets(root, check=args.check)
        warnings = []
        scope = "generated_consumers"
        inputs.append(root / "schemas/core/catalog.json")
        inputs.append(root / "schemas/addons/catalog.json")

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
