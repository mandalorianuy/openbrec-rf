from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from openbrec.beacons import run_beacon_gate
from openbrec.canonical import canonical_hash
from openbrec.energy import run_energy_replay_gate
from openbrec.federation import run_federation_gate
from openbrec.messaging import run_p0_message_gate
from openbrec.terminal import run_accessibility_gate, run_terminal_gate
from openbrec.transports import run_transport_gate


EXPECTED_FAULTS = {
    "partition",
    "node_loss",
    "relay_loss",
    "source_loss",
    "hub_loss",
    "brownout",
    "forged_distress",
    "replay",
    "stolen_terminal",
    "spoofed_sensor",
    "malicious_hub",
}
EXPECTED_BEARERS = {"meshtastic", "meshcore", "reticulum"}
EXPECTED_PROJECTIONS = {"energy", "communication", "messages", "beacon", "review"}


class IntegratedCampaignError(ValueError):
    pass


def _load(root: Path, scenario_path: Path) -> dict[str, Any]:
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    if scenario.get("campaign_version") != "1.0.0":
        raise IntegratedCampaignError("campaign_version must be 1.0.0")
    if scenario.get("claim_scope") != "deterministic_simulation_only":
        raise IntegratedCampaignError("campaign must remain simulation only")
    if scenario.get("partition_duration_s") != 86400:
        raise IntegratedCampaignError("integrated partition must last 24 hours")
    cells = scenario.get("cells", [])
    if len(cells) != 3 or {item.get("bearer") for item in cells} != EXPECTED_BEARERS:
        raise IntegratedCampaignError("campaign must contain three distinct bearer cells")
    if any(not item.get("carry_bundle") for item in cells):
        raise IntegratedCampaignError("every cell must retain carry-bundle fallback")
    faults = scenario.get("faults", [])
    if {item.get("kind") for item in faults} != EXPECTED_FAULTS:
        raise IntegratedCampaignError("integrated fault denominator is incomplete")
    if len(faults) != len(EXPECTED_FAULTS):
        raise IntegratedCampaignError("integrated fault kinds must be unique")
    projections = scenario.get("offline_projection", [])
    if set(projections) != EXPECTED_PROJECTIONS:
        raise IntegratedCampaignError("offline projection domains are incomplete")
    for value in scenario.get("component_scenarios", {}).values():
        path = (root / value).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise IntegratedCampaignError("component scenario escapes repository") from exc
        if not path.is_file():
            raise IntegratedCampaignError(f"component scenario is missing: {value}")
    return scenario


def _component_runs(
    root: Path, scenario: dict[str, Any]
) -> dict[str, tuple[list[str], list[str], dict[str, Any]]]:
    paths = scenario["component_scenarios"]
    energy_path = root / paths["energy"]
    transport_path = root / paths["communication"]
    federation_path = root / paths["federation"]
    runners: dict[str, Callable[[], tuple[list[str], list[str], dict[str, Any]]]] = {
        "energy-replay": lambda: run_energy_replay_gate(root, energy_path),
        "human-message-security": lambda: run_p0_message_gate(root, "human-message-security"),
        "sos-state-replay": lambda: run_p0_message_gate(root, "sos-state-replay"),
        "transport-policy": lambda: run_p0_message_gate(root, "transport-policy"),
        "transport-comparison": lambda: run_transport_gate(root, "transport-comparison", transport_path),
        "malicious-transport": lambda: run_transport_gate(root, "malicious-transport", transport_path),
        "federation-scale": lambda: run_federation_gate(root, "federation-scale", federation_path),
        "federation-reconciliation": lambda: run_federation_gate(root, "federation-reconciliation", federation_path),
        "terminal-ux": lambda: run_terminal_gate(root),
        "accessibility": lambda: run_accessibility_gate(root),
        "beacon-replay": lambda: run_beacon_gate(root, "beacon-replay"),
        "beacon-adversarial": lambda: run_beacon_gate(root, "beacon-adversarial"),
        "retention-fault": lambda: run_beacon_gate(root, "retention-fault"),
    }
    return {gate: runner() for gate, runner in runners.items()}


def _project(
    scenario: dict[str, Any],
    components: dict[str, tuple[list[str], list[str], dict[str, Any]]],
) -> dict[str, Any]:
    summaries = {gate: result[2] for gate, result in components.items()}
    failures = sorted(gate for gate, result in components.items() if result[0])
    faults = sorted(scenario["faults"], key=lambda item: item["fault_id"])
    gaps = sorted(scenario["component_gaps"], key=lambda item: item["domain"])
    visible_gaps = [item for item in gaps if item.get("visible") and item.get("explanation")]
    energy = summaries["energy-replay"]
    transport = summaries["transport-comparison"]
    messaging_security = summaries["human-message-security"]
    sos = summaries["sos-state-replay"]
    malicious_transport = summaries["malicious-transport"]
    federation_scale = summaries["federation-scale"]
    federation_reconciliation = summaries["federation-reconciliation"]
    terminal = summaries["terminal-ux"]
    beacon = summaries["beacon-replay"]
    beacon_adversarial = summaries["beacon-adversarial"]
    retention = summaries["retention-fault"]

    degraded = {
        "energy": any(value != "sufficient_under_model" for value in energy["budget_results"].values()),
        "radio": transport["failed_messages"] > 0,
        "sensing": beacon["missing_capabilities_visible"] > 0 or beacon_adversarial["ood_or_unknown_visible"] > 0,
    }
    cells = sorted(scenario["cells"], key=lambda item: item["cell_id"])
    local_operation_supported = (
        federation_scale["local_operations_blocked_by_superior"] == 0
        and federation_scale["central_critical_path_dependencies"] == 0
    )
    reconciled_faults = [
        item for item in faults
        if item.get("reconciled") and item.get("visible") and item.get("disposition")
    ]
    projection = {
        "claim_scope": scenario["claim_scope"],
        "partition_duration_s": scenario["partition_duration_s"],
        "component_gates": [
            {
                "gate": gate,
                "result": "failed" if result[0] else "passed",
                "result_sha256": result[2].get("result_sha256"),
            }
            for gate, result in sorted(components.items())
        ],
        "component_gates_denominator": len(components),
        "component_gates_passed": len(components) - len(failures),
        "component_gates_failed": len(failures),
        "failed_component_gates": failures,
        "component_gaps_reported": len(gaps),
        "component_gaps_visible": len(visible_gaps),
        "hidden_component_gaps": len(gaps) - len(visible_gaps),
        "faults_denominator": len(faults),
        "faults_reconciled": len(reconciled_faults),
        "unreconciled": len(faults) - len(reconciled_faults),
        "silent_successes": sum(1 for item in faults if not item.get("visible")),
        "fault_dispositions": faults,
        "false_acceptance": max(
            sos["false_operator_accepted"],
            malicious_transport["false_operational_acceptance"],
            federation_scale["false_operational_acceptance"],
            federation_reconciliation["false_operational_acceptance"],
        ),
        "false_confirmation": beacon["automatic_presence_confirmations"] + beacon_adversarial["false_presence_confirmations"],
        "false_absence": terminal["false_absence_claims"] + beacon["absence_inferences"] + beacon_adversarial["false_absence_inferences"],
        "lost_accepted_log_events": 0 if energy["brownout_state_preserved"] else 1,
        "lost_vital_state_events": 0 if energy["brownout_state_preserved"] else 1,
        "sos_priority_inversions": transport["sos_priority_violations"],
        "distress_preserved_for_review": messaging_security["unverified_distress_preserved"] + sos["unverified_distress_preserved"],
        "cells_denominator": len(cells),
        "cells_operating_locally": len(cells) if local_operation_supported else 0,
        "cells_blocked_by_superior": 0 if local_operation_supported else len(cells),
        "carry_bundles_reconciled": len(cells) if federation_scale["federation_events_reconciled"] == federation_scale["federation_events_denominator"] else 0,
        "cell_projection": cells,
        "degraded_domains": sum(degraded.values()),
        "degraded_domains_visible": sum(degraded.values()) if all(degraded.values()) else 0,
        "degradation_states": sorted(key for key, value in degraded.items() if value),
        "offline_projection": {
            "energy": {"budget_results": energy["budget_results"], "brownout_state_preserved": energy["brownout_state_preserved"]},
            "communication": {"failed_messages": transport["failed_messages"], "bearer_models": transport["bearer_models"]},
            "messages": {"operational_state": sos["derived_operational_state"], "false_acceptance": sos["false_operator_accepted"]},
            "beacon": {"outputs": beacon["fusion_outputs"], "false_confirmation": beacon["automatic_presence_confirmations"]},
            "review": {"life_safety_items_preserved": retention["life_safety_items_preserved"], "holds_created": retention["holds_created"]},
        },
        "limitations": [item["explanation"] for item in visible_gaps],
    }
    material = copy.deepcopy(projection)
    hashes = []
    for index in range(10):
        candidate = copy.deepcopy(material)
        if index % 2:
            candidate["component_gates"].reverse()
            candidate["fault_dispositions"].reverse()
            candidate["cell_projection"].reverse()
        candidate["component_gates"] = sorted(candidate["component_gates"], key=lambda item: item["gate"])
        candidate["fault_dispositions"] = sorted(candidate["fault_dispositions"], key=lambda item: item["fault_id"])
        candidate["cell_projection"] = sorted(candidate["cell_projection"], key=lambda item: item["cell_id"])
        hashes.append(canonical_hash(candidate))
    projection["order_variations"] = 10
    projection["distinct_projection_hashes"] = len(set(hashes))
    projection["projection_sha256"] = hashes[0]
    projection["result_sha256"] = canonical_hash(projection)
    return projection


def run_integrated_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        scenario = _load(root, scenario_path)
        components = _component_runs(root, scenario)
        summary = _project(scenario, components)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    for field in (
        "component_gates_failed",
        "hidden_component_gaps",
        "unreconciled",
        "silent_successes",
        "false_acceptance",
        "false_confirmation",
        "false_absence",
        "lost_accepted_log_events",
        "lost_vital_state_events",
        "sos_priority_inversions",
        "cells_blocked_by_superior",
    ):
        if summary[field]:
            errors.append(f"integrated safety invariant failed: {field}")
    if summary["degraded_domains"] != summary["degraded_domains_visible"]:
        errors.append("integrated degradation was hidden")
    if summary["distinct_projection_hashes"] != 1:
        errors.append("integrated campaign is not deterministic")
    expected = scenario["expected_result_sha256"]
    if expected != "TBD" and expected != summary["result_sha256"]:
        errors.append("integrated result does not match frozen expected hash")
    return errors, [], summary
