from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from openbrec.canonical import canonical_hash
from openbrec.simulator import run_scenario


def _load_scenario(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("scenario root must be an object")
    return value


def run_simulator_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    scenario = _load_scenario(scenario_path)
    first = run_scenario(scenario, repository_root=root)
    result_hashes: list[str] = []
    for run_index in range(10):
        reordered = copy.deepcopy(scenario)
        for offset, key in enumerate(("nodes", "tracks", "zones", "faults")):
            values = reordered[key]
            rotation = (run_index + offset) % len(values)
            reordered[key] = values[rotation:] + values[:rotation]
            if run_index % 2:
                reordered[key].reverse()
        result_hashes.append(
            run_scenario(reordered, repository_root=root)["result_sha256"]
        )
    unique_result_hashes = sorted(set(result_hashes))
    projection_sha256 = canonical_hash(first["projection"])
    errors: list[str] = []
    if unique_result_hashes != [first["result_sha256"]]:
        errors.append("scenario result changed under input order variation")
    if projection_sha256 != scenario["expected"]["projection_sha256"]:
        errors.append("scenario projection hash does not match expected fixture")
    if first["disposition"]["unreconciled"] != 0:
        errors.append("scenario produced unreconciled dispositions")
    if any(item["state"] != "abstained" for item in first["projection"]["results"]):
        errors.append("scenario produced a non-abstained consolidated result")
    return errors, [], {
        "scenario": str(scenario_path.relative_to(root)),
        "scenario_sha256": first["scenario_sha256"],
        "result_sha256": first["result_sha256"],
        "runs": len(result_hashes),
        "unique_result_hashes": unique_result_hashes,
        "projection_sha256": projection_sha256,
        "nodes": len(first["projection"]["nodes"]),
        "tracks": len(first["projection"]["tracks"]),
        "zones": len(first["projection"]["zones"]),
        "fault_outcomes": first["fault_outcomes"],
        "disposition": first["disposition"],
    }


def run_core_scenario_gate(
    root: Path, bundle_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors, warnings, summary = run_simulator_gate(root, bundle_path)
    scenario = _load_scenario(bundle_path)
    result = run_scenario(scenario, repository_root=root)
    layers = {
        item["layer"] for item in result["projection"]["timeline"]
    }
    expected_layers = {"observation", "evidence", "fusion_result"}
    if layers != expected_layers:
        errors.append(f"semantic replay layers differ: {sorted(layers)}")
    summary = {
        **summary,
        "semantic_layers": sorted(layers),
        "consolidated_states": sorted(
            {item["state"] for item in result["projection"]["results"]}
        ),
    }
    return errors, warnings, summary


def run_ui_smoke_gate(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    projection_path = root / "apps/web/public/m0-projection.json"
    source_path = root / "apps/web/src/main.tsx"
    compose_path = root / "docker-compose.yml"
    errors: list[str] = []
    if not projection_path.is_file():
        errors.append("PWA projection fixture is missing")
    source = source_path.read_text(encoding="utf-8") if source_path.is_file() else ""
    for marker in (
        'data-testid="operations-map"',
        'data-testid="capability-matrix"',
        'data-testid="event-timeline"',
        'data-testid="semantic-inspector"',
    ):
        if marker not in source:
            errors.append(f"PWA source is missing {marker}")
    compose = compose_path.read_text(encoding="utf-8") if compose_path.is_file() else ""
    if '127.0.0.1:${OPENBREC_WEB_PORT:-8080}:8080' not in compose:
        errors.append("PWA ingress is not constrained to host loopback")
    scenario_path = root / "fixtures/replay/core/m0-six-node.json"
    projection_sha256: str | None = None
    if projection_path.is_file() and scenario_path.is_file():
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        scenario = _load_scenario(scenario_path)
        projection_sha256 = canonical_hash(projection)
        if projection_sha256 != scenario["expected"]["projection_sha256"]:
            errors.append("PWA projection does not match the versioned scenario")

    summary: dict[str, Any] = {
        "projection": "apps/web/public/m0-projection.json",
        "projection_sha256": projection_sha256,
        "ingress_bind": "127.0.0.1",
        "build_exit_code": None,
        "browser": "not_run",
        "offline_reload": "not_run",
    }
    if errors:
        return errors, [], summary

    build = subprocess.run(
        ["pnpm", "--dir", "apps/web", "build"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    summary["build_exit_code"] = build.returncode
    if build.returncode != 0:
        errors.append(f"PWA build failed: {build.stderr.strip() or build.stdout.strip()}")
        return errors, [], summary

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {
        **os.environ,
        "OPENBREC_UI_BASE_URL": f"http://127.0.0.1:{port}",
    }
    server = subprocess.Popen(
        [
            "pnpm",
            "--dir",
            "apps/web",
            "exec",
            "vite",
            "preview",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--strictPort",
        ],
        cwd=root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        ready = False
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and server.poll() is None:
            try:
                with urllib.request.urlopen(
                    environment["OPENBREC_UI_BASE_URL"], timeout=1
                ) as response:
                    ready = response.status == 200
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
            if ready:
                break
        if not ready:
            errors.append("PWA preview did not become ready on loopback")
            return errors, [], summary

        smoke = subprocess.run(
            ["node", "apps/web/scripts/ui-smoke.mjs"],
            cwd=root,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=45,
        )
        if smoke.returncode != 0:
            errors.append(
                f"Chromium UI smoke failed: {smoke.stderr.strip() or smoke.stdout.strip()}"
            )
            return errors, [], summary
        try:
            browser_summary = json.loads(smoke.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            errors.append(f"Chromium UI smoke returned no valid receipt: {exc}")
            return errors, [], summary
        summary.update(browser_summary)
        return errors, [], summary
    except subprocess.TimeoutExpired:
        errors.append("Chromium UI smoke exceeded 45 seconds")
        return errors, [], summary
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
