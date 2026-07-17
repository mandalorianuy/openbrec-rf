from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any

from openbrec.canonical import canonical_hash


SECRET_PATTERNS = (
    re.compile(rb"ghp_[A-Za-z0-9]{36,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
DENIED_LICENSE_MARKERS = {
    "AGPL-3.0",
    "BUSL-1.1",
    "Commons-Clause",
    "SSPL-1.0",
}
CLASSIFIER_LICENSES = {
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "ISC License (ISCL)": "ISC",
    "MIT License": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}
CONTAINER_LICENSES = {
    "eclipse-mosquitto": "EPL-2.0 OR BSD-3-Clause",
    "nginx": "BSD-2-Clause",
    "node": "MIT",
    "postgres": "PostgreSQL",
    "python": "PSF-2.0",
}


def scan_bytes(raw: bytes, *, path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(raw):
            findings.append(
                {
                    "path": path,
                    "offset": match.start(),
                    "kind": pattern.pattern.decode("ascii"),
                }
            )
    return findings


def _tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed during secret scan")
    return [
        root / value.decode("utf-8") for value in result.stdout.split(b"\0") if value
    ]


def run_secret_scan(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    for path in _tracked_files(root):
        if not path.is_file():
            continue
        raw = path.read_bytes()
        if len(raw) > 5 * 1024 * 1024 or b"\0" in raw:
            continue
        scanned += 1
        findings.extend(scan_bytes(raw, path=str(path.relative_to(root))))
    dummy = b"ghp_" + b"A1b2C3d4" * 5
    negative_detected = bool(scan_bytes(dummy, path="synthetic-negative.txt"))
    errors = [
        f"potential secret in {item['path']} at byte {item['offset']}"
        for item in findings
    ]
    if not negative_detected:
        errors.append("negative secret dummy was not detected")
    return (
        errors,
        [],
        {
            "files_scanned": scanned,
            "findings": len(findings),
            "negative_secret_dummy": "detected" if negative_detected else "missed",
        },
    )


def _normalize_license(
    value: str | None, distribution: Distribution | None = None
) -> str | None:
    if value and "\n" in value and value.startswith("MIT License"):
        return "MIT"
    aliases = {
        "Apache Software License": "Apache-2.0",
        "BSD": "BSD-3-Clause",
        "Dual License": "Apache-2.0 OR BSD-3-Clause",
        "GNU GPLv3+": "GPL-3.0-or-later",
        "ISC License": "ISC",
        "MIT license": "MIT",
        "MIT License": "MIT",
        "Modified BSD License": "BSD-3-Clause",
        "MPL 2.0": "MPL-2.0",
        "UNKNOWN": None,
    }
    normalized = aliases.get(value, value)
    if normalized:
        return normalized
    if distribution is None:
        return None
    classifiers = distribution.metadata.get_all("Classifier", [])
    licenses = []
    for classifier in classifiers:
        prefix = "License :: OSI Approved :: "
        if classifier.startswith(prefix):
            mapped = CLASSIFIER_LICENSES.get(classifier.removeprefix(prefix))
            if mapped:
                licenses.append(mapped)
    return " OR ".join(sorted(set(licenses))) or None


def _runtime_python_names(lock: dict[str, Any]) -> set[str]:
    packages = {item["name"]: item for item in lock["package"]}
    required = {"openbrec-rf"}
    pending = ["openbrec-rf"]
    while pending:
        name = pending.pop()
        for dependency in packages.get(name, {}).get("dependencies", []):
            dependency_name = dependency["name"]
            if dependency_name not in required:
                required.add(dependency_name)
                pending.append(dependency_name)
    return required


def _python_components(root: Path) -> list[dict[str, Any]]:
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked = {item["name"]: item["version"] for item in lock["package"]}
    runtime = _runtime_python_names(lock)
    components: list[dict[str, Any]] = []
    for distribution in distributions():
        raw_name = distribution.metadata.get("Name")
        if not raw_name:
            continue
        name = raw_name.lower().replace("_", "-")
        if name not in locked:
            continue
        license_id = _normalize_license(
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License"),
            distribution,
        )
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": f"pkg:pypi/{name}@{distribution.version}",
            "name": name,
            "version": distribution.version,
            "purl": f"pkg:pypi/{name}@{distribution.version}",
            "scope": "required" if name in runtime else "excluded",
            "properties": [{"name": "openbrec:ecosystem", "value": "python"}],
        }
        if license_id:
            component["licenses"] = [{"expression": license_id}]
        components.append(component)
    return components


def _node_package_paths(node_modules: Path) -> list[Path]:
    store = node_modules / ".pnpm"
    paths: list[Path] = []
    if not store.is_dir():
        return paths
    for package_root in store.glob("*/node_modules"):
        for child in package_root.iterdir():
            if child.name.startswith("@") and child.is_dir():
                paths.extend(
                    grandchild / "package.json" for grandchild in child.iterdir()
                )
            else:
                paths.append(child / "package.json")
    return paths


def _node_components(root: Path) -> list[dict[str, Any]]:
    components: dict[str, dict[str, Any]] = {}
    for relative, scope in (
        ("node_modules", "excluded"),
        ("apps/web/node_modules", "required"),
    ):
        for path in _node_package_paths(root / relative):
            if not path.is_file():
                continue
            try:
                package = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            name, version = package.get("name"), package.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                continue
            purl_name = name.replace("@", "%40", 1) if name.startswith("@") else name
            purl = f"pkg:npm/{purl_name}@{version}"
            license_value = package.get("license")
            if isinstance(license_value, dict):
                license_value = license_value.get("type")
            component: dict[str, Any] = {
                "type": "library",
                "bom-ref": purl,
                "name": name,
                "version": version,
                "purl": purl,
                "scope": scope,
                "properties": [{"name": "openbrec:ecosystem", "value": "npm"}],
            }
            if isinstance(license_value, str):
                component["licenses"] = [
                    {"expression": _normalize_license(license_value) or license_value}
                ]
            previous = components.get(purl)
            if (
                previous is None
                or previous["scope"] == "excluded"
                and scope == "required"
            ):
                components[purl] = component
    return list(components.values())


def _container_components(root: Path) -> list[dict[str, Any]]:
    references: set[str] = set()
    for path in (root / "apps/api/Dockerfile", root / "apps/web/Dockerfile"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("FROM "):
                references.add(line.split()[1])
    for line in (root / "docker-compose.yml").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("image:"):
            reference = stripped.split(":", 1)[1].strip()
            if not reference.startswith("openbrec/"):
                references.add(reference)

    components: list[dict[str, Any]] = []
    for reference in sorted(references):
        image, separator, digest = reference.partition("@sha256:")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"container input is not pinned by SHA-256: {reference}")
        repository, _, tag = image.partition(":")
        name = repository.rsplit("/", 1)[-1]
        components.append(
            {
                "type": "container",
                "bom-ref": f"pkg:oci/{repository}@sha256:{digest}",
                "name": name,
                "version": tag or f"sha256:{digest}",
                "purl": f"pkg:oci/{repository}@sha256:{digest}",
                "scope": "required",
                "hashes": [{"alg": "SHA-256", "content": digest}],
                "licenses": [{"expression": CONTAINER_LICENSES[name]}],
                "properties": [
                    {"name": "openbrec:ecosystem", "value": "oci"},
                    {"name": "openbrec:declared-reference", "value": reference},
                ],
            }
        )
    return components


def build_sbom(root: Path) -> dict[str, Any]:
    project = {
        "type": "application",
        "bom-ref": "pkg:generic/openbrec-rf@0.0.0",
        "name": "openbrec-rf",
        "version": "0.0.0",
        "purl": "pkg:generic/openbrec-rf@0.0.0",
        "scope": "required",
        "licenses": [{"expression": "Apache-2.0"}],
        "properties": [{"name": "openbrec:profile", "value": "lab-sim"}],
    }
    components = [
        project,
        *_python_components(root),
        *_node_components(root),
        *_container_components(root),
    ]
    unique = {item["bom-ref"]: item for item in components}
    ordered = [unique[key] for key in sorted(unique)]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {"component": project},
        "components": ordered,
        "properties": [
            {"name": "openbrec:deterministic", "value": "true"},
            {"name": "openbrec:component-count", "value": str(len(ordered))},
        ],
    }


def write_sbom(root: Path, output: Path) -> dict[str, Any]:
    sbom = build_sbom(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return sbom


def run_license_gate(
    root: Path, sbom: dict[str, Any] | None = None
) -> tuple[list[str], list[str], dict[str, Any]]:
    inventory = sbom or build_sbom(root)
    missing: list[str] = []
    denied: list[str] = []
    reviewed = 0
    for component in inventory["components"]:
        licenses = component.get("licenses", [])
        if not licenses:
            missing.append(component["bom-ref"])
            continue
        reviewed += 1
        expression = " ".join(
            item.get("expression") or item.get("license", {}).get("id", "")
            for item in licenses
        )
        if any(marker in expression for marker in DENIED_LICENSE_MARKERS):
            denied.append(f"{component['bom-ref']}: {expression}")
    errors = [
        *(f"missing license: {item}" for item in missing),
        *(f"denied license: {item}" for item in denied),
    ]
    return (
        errors,
        [],
        {
            "components": len(inventory["components"]),
            "reviewed": reviewed,
            "missing_license": len(missing),
            "denied_license": len(denied),
            "sbom_sha256": canonical_hash(inventory),
        },
    )


def summarize_vulnerability_reports(
    python_report: dict[str, Any], node_reports: list[dict[str, Any]]
) -> tuple[list[str], dict[str, Any]]:
    python_findings = [
        {"package": dependency.get("name"), "id": vulnerability.get("id")}
        for dependency in python_report.get("dependencies", [])
        for vulnerability in dependency.get("vulns", [])
    ]
    node_counts = {
        level: 0 for level in ("info", "low", "moderate", "high", "critical")
    }
    for report in node_reports:
        counts = report.get("metadata", {}).get("vulnerabilities", {})
        for level in node_counts:
            node_counts[level] += int(counts.get(level, 0))
    node_total = sum(node_counts.values())
    total = len(python_findings) + node_total
    errors = []
    if python_findings:
        errors.append(
            "known Python vulnerabilities: "
            + ", ".join(f"{item['package']}:{item['id']}" for item in python_findings)
        )
    if node_total:
        errors.append(f"known Node vulnerabilities: {node_counts}")
    return errors, {
        "known_vulnerabilities": total,
        "python_vulnerabilities": len(python_findings),
        "node_vulnerabilities": node_counts,
    }


def run_vulnerability_gate(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openbrec-vulnerability-") as directory:
        cache = Path(directory)
        python = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--local", "--format", "json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PIP_AUDIT_CACHE_DIR": str(cache)},
        )
        try:
            python_report = json.loads(python.stdout)
        except json.JSONDecodeError:
            return (
                [f"pip-audit failed: {python.stderr.strip()}"],
                warnings,
                {
                    "scanner": "pip-audit 2.10.1",
                    "python_exit_code": python.returncode,
                },
            )

        node_reports: list[dict[str, Any]] = []
        node_exit_codes: list[int] = []
        for cwd in (root, root / "apps/web"):
            node = subprocess.run(
                ["pnpm", "audit", "--json"],
                cwd=cwd,
                text=True,
                capture_output=True,
                check=False,
            )
            node_exit_codes.append(node.returncode)
            try:
                node_reports.append(json.loads(node.stdout))
            except json.JSONDecodeError:
                return (
                    [f"pnpm audit failed in {cwd}: {node.stderr.strip()}"],
                    warnings,
                    {
                        "scanner": "pip-audit 2.10.1 + pnpm audit",
                        "python_exit_code": python.returncode,
                        "node_exit_codes": node_exit_codes,
                    },
                )

    errors, summary = summarize_vulnerability_reports(python_report, node_reports)
    synthetic_errors, _ = summarize_vulnerability_reports(
        {"dependencies": [{"name": "synthetic", "vulns": [{"id": "SYNTHETIC-1"}]}]},
        [],
    )
    if not synthetic_errors:
        errors.append("synthetic vulnerability negative was not detected")
    summary.update(
        {
            "scanner": "pip-audit 2.10.1 + pnpm audit",
            "python_exit_code": python.returncode,
            "node_exit_codes": node_exit_codes,
            "synthetic_negative": "detected" if synthetic_errors else "missed",
        }
    )
    return errors, warnings, summary
