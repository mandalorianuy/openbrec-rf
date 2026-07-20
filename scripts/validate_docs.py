#!/usr/bin/env python3
"""Small offline validator for the public OpenBREC documentation surface."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = (
    Path("docs/open-spec"),
    Path("docs/guides"),
    Path("docs/reference-builds"),
    Path("docs/evidence-packs"),
    Path("docs/field-profiles"),
    Path("docs/research"),
    Path("docs/outreach"),
)
PUBLIC_FILES = (
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    Path("docs/START_HERE.md"),
    Path("docs/DOCUMENTATION_ARCHITECTURE.md"),
    Path("docs/architecture.md"),
    Path("docs/faq.md"),
    Path("docs/glossary.md"),
)
REQUIRED_FILES = {
    *PUBLIC_FILES,
    Path("docs/guides/quickstart-offgrid.md"),
    Path("docs/guides/deployment-planning.md"),
    Path("docs/guides/energy.md"),
    Path("docs/guides/transports.md"),
    Path("docs/guides/messaging-sos.md"),
    Path("docs/guides/beacons.md"),
    Path("docs/guides/federation.md"),
    Path("docs/guides/building-reuse.md"),
    Path("docs/guides/validation-troubleshooting.md"),
    Path("docs/reference-builds/personal-team-kit.md"),
    Path("docs/reference-builds/response-cell.md"),
    Path("docs/reference-builds/federated-deployment.md"),
}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```(json|ya?ml)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
BASH_FENCE_RE = re.compile(r"```(?:bash|sh)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def public_markdown_files(root: Path) -> list[Path]:
    files = [root / path for path in PUBLIC_FILES]
    for directory in PUBLIC_ROOTS:
        files.extend(sorted((root / directory).rglob("*.md")))
    return sorted(set(files))


def validate_markdown_links(root: Path, files: list[Path]) -> list[str]:
    errors: list[str] = []
    resolved_root = root.resolve()
    for source_path in files:
        if not source_path.is_file():
            errors.append(f"missing documentation file: {source_path.relative_to(root)}")
            continue
        source = source_path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(source):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0])
            candidate = (source_path.parent / target).resolve()
            try:
                candidate.relative_to(resolved_root)
            except ValueError:
                errors.append(
                    f"link escapes repository: {source_path.relative_to(root)} -> {target}"
                )
                continue
            if not candidate.exists():
                errors.append(
                    f"missing target: {source_path.relative_to(root)} -> {target}"
                )
    return errors


def validate_fenced_examples(root: Path, files: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in files:
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for index, (language, payload) in enumerate(FENCE_RE.findall(source), start=1):
            try:
                if language.lower() == "json":
                    json.loads(payload)
                else:
                    import yaml

                    yaml.safe_load(payload)
            except Exception as exc:
                errors.append(
                    f"invalid {language} example: {path.relative_to(root)}#{index}: {exc}"
                )
    return errors


def _known_verify_commands(root: Path) -> tuple[set[str], str | None]:
    result = subprocess.run(
        [sys.executable, "-m", "openbrec.verify", "--help"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set(), result.stderr.strip() or "openbrec.verify --help failed"
    match = re.search(r"\{([^}]+)\}", result.stdout)
    return (set(match.group(1).split(",")) if match else set()), None


def validate_commands(root: Path, files: list[Path]) -> list[str]:
    errors: list[str] = []
    known, command_error = _known_verify_commands(root)
    if command_error:
        return [command_error]
    for path in files:
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for block in BASH_FENCE_RE.findall(source):
            for line in block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    parts = shlex.split(line)
                except ValueError as exc:
                    errors.append(f"invalid shell example: {path.relative_to(root)}: {exc}")
                    continue
                if "openbrec.verify" in parts:
                    module_index = parts.index("openbrec.verify")
                    if len(parts) <= module_index + 1 or parts[module_index + 1] not in known:
                        errors.append(
                            f"unknown verify command: {path.relative_to(root)}: {line}"
                        )
                for part in parts:
                    if part.startswith("scripts/") and part.endswith(".py"):
                        if not (root / part).is_file():
                            errors.append(
                                f"missing command target: {path.relative_to(root)}: {part}"
                            )
    return errors


def validate_status_contract(root: Path) -> list[str]:
    architecture = (root / "docs/DOCUMENTATION_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    public_labels = {
        "specified",
        "simulated",
        "bench-validated",
        "field-validated",
        "unsupported",
        "unverified",
    }
    errors: list[str] = []
    for label in public_labels:
        if f"`{label}`" not in architecture or f"`{label}`" not in readme:
            errors.append(f"public status vocabulary missing: {label}")
    for legacy in ("supported", "experimental", "unavailable"):
        if f"`{legacy}`" not in architecture:
            errors.append(f"legacy status mapping missing: {legacy}")
    return errors


def main() -> int:
    files = public_markdown_files(ROOT)
    errors = [
        *(f"missing required file: {path}" for path in REQUIRED_FILES if not (ROOT / path).is_file()),
        *validate_markdown_links(ROOT, files),
        *validate_fenced_examples(ROOT, files),
        *validate_commands(ROOT, files),
        *validate_status_contract(ROOT),
    ]
    if errors:
        print("\n".join(sorted(set(errors))), file=sys.stderr)
        return 1
    print(f"documentation valid: {len(files)} markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
