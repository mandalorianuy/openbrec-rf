from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
VERIFY_VERSION = "0.1.0"


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


def _validate_catalog(root: Path, catalog_path: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    summary: dict[str, Any] = {"catalog": str(catalog_path.relative_to(root)), "catalog_entries": 0}
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
            errors.append(f"{prefix}.sha256 must be 64 lowercase hexadecimal characters")
            continue
        try:
            int(expected_hash, 16)
        except ValueError:
            errors.append(f"{prefix}.sha256 must be 64 lowercase hexadecimal characters")
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
            errors.append(f"sha256 mismatch for {path_value}: expected {expected_hash}, got {actual_hash}")
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


def _run_bundle_structure(root: Path) -> tuple[list[str], dict[str, Any]]:
    validator = root / "scripts/validate_bundle.py"
    if not validator.is_file():
        return ["scripts/validate_bundle.py not found"], {}
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
    return errors, summary


def _write_receipt(
    *,
    root: Path,
    receipt_value: str,
    gate: str,
    scope: str,
    command: Sequence[str],
    started_at: str,
    errors: list[str],
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
        "warnings": [],
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "responsible_role": "contract-maintainer",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m openbrec.verify")
    subparsers = parser.add_subparsers(dest="gate", required=True)
    for gate in ("bundle-structure", "schema"):
        subparser = subparsers.add_parser(gate)
        subparser.add_argument("--root", default=".")
        subparser.add_argument("--receipt")
        if gate == "schema":
            subparser.add_argument("--catalog", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    inputs: list[Path] = []
    if args.gate == "bundle-structure":
        errors, summary = _run_bundle_structure(root)
        inputs.append(root / "scripts/validate_bundle.py")
        scope = "structural_only"
    else:
        try:
            catalog_path = _resolve_inside(root, args.catalog, label="catalog")
            inputs.append(catalog_path)
            errors, summary = _validate_catalog(root, catalog_path)
        except ValueError as exc:
            errors, summary = [str(exc)], {"catalog": args.catalog, "catalog_entries": 0}
        scope = "catalog_integrity_only"

    if args.receipt:
        _write_receipt(
            root=root,
            receipt_value=args.receipt,
            gate=args.gate,
            scope=scope,
            command=["python", "-m", "openbrec.verify", *(argv if argv is not None else sys.argv[1:])],
            started_at=started_at,
            errors=errors,
            summary=summary,
            inputs=inputs,
        )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(json.dumps({"gate": args.gate, "result": "passed", "scope": scope}, sort_keys=True))
    return 0
