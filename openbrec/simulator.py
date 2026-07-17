from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import load_core_schemas, schema_registry


FAULT_OUTCOMES = {
    "brownout": "confidence_degraded",
    "duplicate": "deduplicated",
    "loss": "coverage_degraded",
    "malicious_peer": "quarantined",
    "partition": "capability_absent",
    "restart": "new_boot_session_preserved",
}


class ScenarioValidationError(ValueError):
    pass


def _round(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN))


def _validate_scenario(scenario: dict[str, Any], repository_root: Path) -> None:
    if len(scenario.get("nodes", [])) != 6:
        raise ScenarioValidationError("scenario requires exactly six nodes")
    if len(scenario.get("tracks", [])) != 2:
        raise ScenarioValidationError("scenario requires exactly two tracks")
    if len(scenario.get("zones", [])) != 3:
        raise ScenarioValidationError("scenario requires exactly three zones")
    if {item.get("kind") for item in scenario.get("faults", [])} != set(FAULT_OUTCOMES):
        raise ScenarioValidationError("scenario fault set is incomplete")

    schemas = load_core_schemas(repository_root)
    schema = next(
        item for item, path in schemas if path.name == "capability-manifest.schema.json"
    )
    validator = Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )
    errors: list[str] = []
    for node in scenario["nodes"]:
        errors.extend(
            f"{node.get('node_id', 'unknown')}: {error.message}"
            for error in validator.iter_errors(node.get("capability_manifest"))
        )
    if errors:
        raise ScenarioValidationError("; ".join(sorted(errors)))


def _ordered(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted((copy.deepcopy(item) for item in items), key=lambda item: item[key])


def _scenario_material(scenario: dict[str, Any]) -> dict[str, Any]:
    material = {
        key: copy.deepcopy(value)
        for key, value in scenario.items()
        if key not in {"expected", "nodes", "tracks", "zones", "faults"}
    }
    material.update(
        {
            "nodes": _ordered(scenario["nodes"], "node_id"),
            "tracks": _ordered(scenario["tracks"], "track_id"),
            "zones": _ordered(scenario["zones"], "zone_id"),
            "faults": _ordered(scenario["faults"], "fault_id"),
        }
    )
    return material


def run_scenario(
    scenario: dict[str, Any],
    *,
    repository_root: Path,
    active_faults: list[str] | None = None,
) -> dict[str, Any]:
    _validate_scenario(scenario, repository_root)
    enabled = set(FAULT_OUTCOMES if active_faults is None else active_faults)
    unknown = enabled - set(FAULT_OUTCOMES)
    if unknown:
        raise ScenarioValidationError(f"unknown active faults: {sorted(unknown)}")

    faults = {
        item["kind"]: item
        for item in _ordered(scenario["faults"], "fault_id")
        if item["kind"] in enabled
    }
    zones = _ordered(scenario["zones"], "zone_id")
    nodes = _ordered(scenario["nodes"], "node_id")
    tracks = _ordered(scenario["tracks"], "track_id")
    node_projection: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    for index, node in enumerate(nodes):
        quality = Decimal(str(node["quality"]))
        reporting = not (
            "loss" in faults and faults["loss"]["node_id"] == node["node_id"]
        )
        absent = set(node["capability_manifest"]["capabilities_absent"])
        status = "reporting" if reporting else "lost"
        boot_session = "session-1"
        if "brownout" in faults and faults["brownout"]["node_id"] == node["node_id"]:
            quality *= Decimal("0.55")
            absent.add("power.stable")
            status = "degraded"
        if "partition" in faults and faults["partition"]["node_id"] == node["node_id"]:
            quality *= Decimal("0.75")
            absent.add("backhaul.connected")
            status = "partitioned"
        if "restart" in faults and faults["restart"]["node_id"] == node["node_id"]:
            boot_session = "session-2"
            status = "restarted"
        if not reporting:
            quality = Decimal("0")
            absent.add("node.reporting")

        projected = {
            "node_id": node["node_id"],
            "label": node["label"],
            "zone_id": node["zone_id"],
            "position": node["position"],
            "status": status,
            "quality": _round(quality),
            "boot_session": boot_session,
            "capabilities": sorted(node["capability_manifest"]["capabilities"]),
            "capabilities_absent": sorted(absent),
        }
        node_projection.append(projected)
        if reporting:
            observation_id = f"observation-{index + 1:02d}"
            timeline.extend(
                [
                    {
                        "event_id": observation_id,
                        "timestamp": scenario["logical_start"],
                        "zone_id": node["zone_id"],
                        "node_id": node["node_id"],
                        "layer": "observation",
                        "label": "Observación sintética recibida",
                        "confidence": _round(quality),
                    },
                    {
                        "event_id": f"evidence-{index + 1:02d}",
                        "timestamp": scenario["logical_end"],
                        "zone_id": node["zone_id"],
                        "node_id": node["node_id"],
                        "layer": "evidence",
                        "label": "Evidencia limitada derivada",
                        "confidence": _round(quality * Decimal("0.8")),
                    },
                ]
            )

    zone_summary: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for zone in zones:
        members = [item for item in node_projection if item["zone_id"] == zone["zone_id"]]
        reporting = [item for item in members if item["status"] != "lost"]
        coverage_ratio = Decimal(len(reporting)) / Decimal(len(members))
        average_quality = (
            sum(Decimal(str(item["quality"])) for item in reporting)
            / Decimal(len(reporting))
            if reporting
            else Decimal("0")
        )
        confidence = _round(average_quality * coverage_ratio)
        absent = sorted(
            {capability for item in members for capability in item["capabilities_absent"]}
        )
        coverage = f"{len(reporting)}/{len(members)} nodos sintéticos reportando"
        if len(reporting) < len(members):
            coverage += "; cobertura parcial"
        explanation = (
            f"Cobertura {coverage}. La evidencia es sintética y no alcanza para "
            "confirmar presencia ni ausencia; se requiere revisión operativa."
        )
        summary = {
            "state": "abstained",
            "confidence": confidence,
            "coverage": coverage,
            "capabilities_absent": absent,
            "sources": sorted(item["node_id"] for item in reporting),
            "explanation": explanation,
        }
        zone_summary[zone["zone_id"]] = summary
        results.append(
            {
                "result_id": f"result-{zone['zone_id']}",
                "timestamp": scenario["logical_end"],
                "zone_id": zone["zone_id"],
                "precision": f"±{zone['precision_m']} m (escenario sintético)",
                **summary,
            }
        )
        timeline.append(
            {
                "event_id": f"fusion-{zone['zone_id']}",
                "timestamp": scenario["logical_end"],
                "zone_id": zone["zone_id"],
                "layer": "fusion_result",
                "label": "Inferencia consolidada: Abstención",
                "confidence": confidence,
            }
        )

    fault_outcomes = {
        kind: FAULT_OUTCOMES[kind] for kind in sorted(enabled)
    }
    accepted = sum(1 for item in node_projection if item["status"] != "lost")
    quarantine = int("malicious_peer" in enabled)
    disposition = {
        "ingress_units": accepted + quarantine,
        "destinations": {
            "accepted_event_log": accepted,
            "review_quarantine": quarantine,
            "evidence_vault": 0,
            "rejection_ledger": 0,
        },
        "unreconciled": 0,
    }
    projection = {
        "schema_version": "1.0.0",
        "scenario_id": scenario["scenario_id"],
        "generated_at": scenario["logical_end"],
        "mode": "offline_replay",
        "semantic_layers": ["observation", "evidence", "fusion_result"],
        "zones": [
            {
                **zone,
                "summary": zone_summary[zone["zone_id"]],
            }
            for zone in zones
        ],
        "nodes": node_projection,
        "tracks": tracks,
        "timeline": sorted(
            timeline,
            key=lambda item: (item["timestamp"], item["layer"], item["event_id"]),
        ),
        "results": results,
        "fault_outcomes": fault_outcomes,
        "safety_notice": (
            "Los indicios no confirman presencia ni ausencia. El silencio o la pérdida "
            "de una fuente sólo degradan cobertura y confianza."
        ),
    }
    material = {
        "scenario_sha256": canonical_hash(_scenario_material(scenario)),
        "active_faults": sorted(enabled),
        "projection": projection,
        "disposition": disposition,
    }
    return {
        **material,
        "projection": projection,
        "zone_summary": zone_summary,
        "fault_outcomes": fault_outcomes,
        "result_sha256": canonical_hash(material),
    }
