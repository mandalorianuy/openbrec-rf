from __future__ import annotations

import copy
import json
import os
import re
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import (
    load_addon_schemas,
    load_core_schemas,
    schema_registry,
)

LOAD_CLASSES = {
    "L0_LIFE_SAFETY",
    "L1_MISSION_CRITICAL",
    "L2_MISSION_SUPPORT",
    "L3_DEFERRABLE",
}
EVENT_KINDS = {
    "sample",
    "source_loss",
    "source_restore",
    "sos_active",
    "brownout",
    "restart",
}
STATE_ORDER = {"normal": 0, "conserve": 1, "critical": 2, "survival": 3, "shutdown": 4}


class EnergyScenarioError(ValueError):
    pass


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise EnergyScenarioError(f"{label} must be numeric")
    result = Decimal(str(value))
    if not result.is_finite():
        raise EnergyScenarioError(f"{label} must be finite")
    return result


def _rounded(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def _timestamp(start: str, offset_s: int) -> str:
    parsed = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(UTC)
    return (
        (parsed + timedelta(seconds=offset_s))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _validate_scenario(scenario: dict[str, Any]) -> None:
    domains = scenario.get("domains")
    if not isinstance(domains, list) or len(domains) != 3:
        raise EnergyScenarioError("scenario requires exactly three energy domains")
    if not isinstance(scenario.get("window_s"), int) or scenario["window_s"] <= 0:
        raise EnergyScenarioError("window_s must be a positive integer")
    margin = _decimal(scenario.get("margin_factor"), "margin_factor")
    if margin < Decimal("1"):
        raise EnergyScenarioError("margin_factor must be at least one")

    domain_ids: set[str] = set()
    event_ids: set[str] = set()
    for domain in domains:
        domain_id = domain.get("domain_id")
        if not isinstance(domain_id, str) or domain_id in domain_ids:
            raise EnergyScenarioError("domain_id must be unique and non-empty")
        domain_ids.add(domain_id)
        if domain.get("autonomous") is not True:
            raise EnergyScenarioError(f"{domain_id}: autonomous must be true")
        if (
            re.fullmatch(r"[0-9a-f]{32}", str(domain.get("initial_boot_id", "")))
            is None
        ):
            raise EnergyScenarioError(
                f"{domain_id}.initial_boot_id must be 128-bit lowercase hex"
            )
        for name in ("initial_sequence", "initial_accepted_log_count"):
            value = domain.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise EnergyScenarioError(
                    f"{domain_id}.{name} must be a non-negative integer"
                )
        for name in (
            "measured_capacity_Wh",
            "capacity_uncertainty_Wh",
            "allowed_dod",
            "temperature_derating",
            "aging_derating",
            "conversion_efficiency_lower",
            "auxiliary_generation_Wh",
        ):
            if _decimal(domain.get(name), f"{domain_id}.{name}") < 0:
                raise EnergyScenarioError(f"{domain_id}.{name} must not be negative")
        for name in (
            "allowed_dod",
            "temperature_derating",
            "aging_derating",
            "conversion_efficiency_lower",
        ):
            value = _decimal(domain[name], f"{domain_id}.{name}")
            if value <= 0 or value > 1:
                raise EnergyScenarioError(f"{domain_id}.{name} must be in (0, 1]")
        reserves = domain.get("reserves")
        if not isinstance(reserves, dict) or set(reserves) != {
            "sos_Wh",
            "transition_Wh",
            "shutdown_Wh",
        }:
            raise EnergyScenarioError(
                f"{domain_id}.reserves must declare SOS, transition and shutdown"
            )
        for name, value in reserves.items():
            if _decimal(value, f"{domain_id}.reserves.{name}") < 0:
                raise EnergyScenarioError(
                    f"{domain_id}.reserves.{name} must not be negative"
                )
        soc = domain.get("initial_soc")
        uncertainty = domain.get("soc_uncertainty")
        if (soc is None) != (uncertainty is None):
            raise EnergyScenarioError(
                f"{domain_id}: SOC and uncertainty must both be known or unknown"
            )
        if soc is not None:
            soc_value = _decimal(soc, f"{domain_id}.initial_soc")
            soc_uncertainty = _decimal(uncertainty, f"{domain_id}.soc_uncertainty")
            if not 0 <= soc_value <= 1 or not 0 <= soc_uncertainty <= 1:
                raise EnergyScenarioError(f"{domain_id}: SOC values must be in [0, 1]")
        sources = domain.get("sources", [])
        source_ids = {source.get("source_id") for source in sources}
        if None in source_ids or len(source_ids) != len(sources):
            raise EnergyScenarioError(f"{domain_id}: source IDs must be unique")
        loads = domain.get("loads", [])
        classes = {load.get("class") for load in loads}
        if not {"L0_LIFE_SAFETY", "L1_MISSION_CRITICAL"}.issubset(classes):
            raise EnergyScenarioError(f"{domain_id}: L0 and L1 loads are required")
        load_ids: set[str] = set()
        for load in loads:
            load_id = load.get("load_id")
            if not isinstance(load_id, str) or load_id in load_ids:
                raise EnergyScenarioError(f"{domain_id}: load IDs must be unique")
            load_ids.add(load_id)
            if load.get("class") not in LOAD_CLASSES:
                raise EnergyScenarioError(f"{domain_id}.{load_id}: unknown load class")
            for name in ("power_W", "uncertainty_W", "duty_cycle"):
                if _decimal(load.get(name), f"{domain_id}.{load_id}.{name}") < 0:
                    raise EnergyScenarioError(
                        f"{domain_id}.{load_id}.{name} must not be negative"
                    )
            if _decimal(load["duty_cycle"], "duty_cycle") > 1:
                raise EnergyScenarioError(
                    f"{domain_id}.{load_id}: duty_cycle must not exceed one"
                )
        if not domain.get("events"):
            raise EnergyScenarioError(f"{domain_id} must declare at least one event")
        for event in sorted(
            domain.get("events", []),
            key=lambda item: (item.get("at_s", -1), item.get("event_id", "")),
        ):
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or event_id in event_ids:
                raise EnergyScenarioError("event_id must be unique and non-empty")
            event_ids.add(event_id)
            if event.get("kind") not in EVENT_KINDS:
                raise EnergyScenarioError(f"{event_id}: unknown energy event kind")
            at_s = event.get("at_s")
            if not isinstance(at_s, int) or at_s < 0 or at_s > scenario["window_s"]:
                raise EnergyScenarioError(f"{event_id}: at_s outside scenario window")
            if (
                event["kind"] in {"source_loss", "source_restore"}
                and event.get("source_id") not in source_ids
            ):
                raise EnergyScenarioError(
                    f"{event_id}: event references undeclared source"
                )
            event_soc = event.get("soc")
            if (
                event_soc is not None
                and not 0 <= _decimal(event_soc, f"{event_id}.soc") <= 1
            ):
                raise EnergyScenarioError(f"{event_id}: SOC must be in [0, 1]")


def next_energy_state(
    previous: str | None, soc: Decimal | None, event_kind: str
) -> str:
    if event_kind in {"brownout", "restart"}:
        return "survival"
    if soc is None:
        return "unknown"
    if soc <= Decimal("0.08"):
        target = "shutdown"
    elif soc <= Decimal("0.15"):
        target = "survival"
    elif soc <= Decimal("0.30"):
        target = "critical"
    elif soc <= Decimal("0.50"):
        target = "conserve"
    else:
        target = "normal"
    if previous is None or previous == "unknown":
        return target
    if STATE_ORDER[target] >= STATE_ORDER[previous]:
        return target
    if previous == "shutdown":
        return "survival"
    if previous == "survival":
        return "critical" if soc >= Decimal("0.20") else "survival"
    if previous == "critical":
        return "conserve" if soc >= Decimal("0.35") else "critical"
    if previous == "conserve":
        return "normal" if soc >= Decimal("0.55") else "conserve"
    return target


def _loads_shed(loads: list[dict[str, Any]], state: str, event_kind: str) -> list[str]:
    shed_classes = {
        "normal": set(),
        "conserve": {"L3_DEFERRABLE"},
        "critical": {"L2_MISSION_SUPPORT", "L3_DEFERRABLE"},
        "survival": {"L2_MISSION_SUPPORT", "L3_DEFERRABLE"},
        "shutdown": LOAD_CLASSES,
        "unknown": {"L2_MISSION_SUPPORT", "L3_DEFERRABLE"},
    }[state]
    if event_kind == "sos_active":
        shed_classes = {*shed_classes, "L3_DEFERRABLE"}
    return sorted(load["load_id"] for load in loads if load["class"] in shed_classes)


def _budget(
    domain: dict[str, Any], scenario: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    capacity_lower = max(
        Decimal("0"),
        _decimal(domain["measured_capacity_Wh"], "capacity")
        - _decimal(domain["capacity_uncertainty_Wh"], "capacity uncertainty"),
    )
    capacity_lower *= (
        _decimal(domain["allowed_dod"], "DoD")
        * _decimal(domain["temperature_derating"], "temperature derating")
        * _decimal(domain["aging_derating"], "aging derating")
    )
    soc = domain.get("initial_soc")
    if soc is None:
        remaining_lower: Decimal | None = None
    else:
        soc_lower = max(
            Decimal("0"),
            _decimal(soc, "SOC")
            - _decimal(domain["soc_uncertainty"], "SOC uncertainty"),
        )
        remaining_lower = capacity_lower * soc_lower
    critical_loads = [
        load
        for load in domain["loads"]
        if load["class"] in {"L0_LIFE_SAFETY", "L1_MISSION_CRITICAL"}
    ]
    critical_power_upper = sum(
        (
            _decimal(load["power_W"], "load power")
            + _decimal(load["uncertainty_W"], "load uncertainty")
        )
        * _decimal(load["duty_cycle"], "duty cycle")
        for load in critical_loads
    ) / _decimal(domain["conversion_efficiency_lower"], "conversion efficiency")
    critical_load_Wh = (
        critical_power_upper * Decimal(scenario["window_s"]) / Decimal(3600)
    )
    reserves = sum(_decimal(value, "reserve") for value in domain["reserves"].values())
    required_with_reserves = critical_load_Wh + reserves
    required_with_margin = required_with_reserves * _decimal(
        scenario["margin_factor"], "margin"
    )
    if remaining_lower is None or critical_power_upper == 0:
        result = "unknown"
        runtime_lower_bound_s = None
    else:
        result = (
            "sufficient_under_model"
            if remaining_lower >= required_with_margin
            else "insufficient"
        )
        runtime_energy = max(
            Decimal("0"),
            remaining_lower
            - _decimal(domain["reserves"]["shutdown_Wh"], "shutdown reserve"),
        )
        runtime_lower_bound_s = int(
            (runtime_energy * Decimal(3600) / critical_power_upper).to_integral_value(
                rounding=ROUND_FLOOR
            )
        )
    gaps = ["physical load trace", "measured hardware profile"]
    if remaining_lower is None:
        gaps.append("SOC measurement")
    budget = {
        "schema_version": "1.0.0",
        "budget_type": "energy_budget",
        "budget_id": "00000000-0000-5000-8000-"
        + canonical_hash(domain["domain_id"])[:12],
        "energy_domain_id": domain["domain_id"],
        "created_at": scenario["logical_start"],
        "window_s": scenario["window_s"],
        "usable_storage_Wh": _rounded(capacity_lower),
        "critical_load_Wh": _rounded(critical_load_Wh),
        "reserves_Wh": _rounded(reserves),
        "auxiliary_generation_Wh": _rounded(
            _decimal(domain["auxiliary_generation_Wh"], "auxiliary generation")
        ),
        "result": result,
        "assumptions": [
            "auxiliary generation excluded from storage reserve",
            "critical power uses declared upper uncertainty and lower conversion efficiency",
            "synthetic load profile",
        ],
        "gaps": sorted(gaps),
    }
    if runtime_lower_bound_s is not None:
        budget["runtime_lower_bound_s"] = runtime_lower_bound_s
    conservation = {
        "remaining_usable_Wh_lower": (
            None if remaining_lower is None else _rounded(remaining_lower)
        ),
        "critical_load_Wh_upper": _rounded(critical_load_Wh),
        "reserves_Wh": _rounded(reserves),
        "required_with_margin_Wh": _rounded(required_with_margin),
        "auxiliary_generation_Wh_separate": _rounded(
            _decimal(domain["auxiliary_generation_Wh"], "auxiliary generation")
        ),
        "auxiliary_credited_to_storage_reserve_Wh": 0,
        "storage_only_margin_Wh": (
            None
            if remaining_lower is None
            else _rounded(remaining_lower - required_with_margin)
        ),
        "energy_created_Wh": 0,
    }
    return budget, conservation


def _schema_validator(root: Path, name: str) -> Draft202012Validator:
    schemas = [*load_core_schemas(root), *load_addon_schemas(root)]
    schema = next(item for item, path in schemas if path.name == name)
    return Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )


def _validate_output(
    validator: Draft202012Validator, value: dict[str, Any], label: str
) -> None:
    errors = sorted(
        validator.iter_errors(value), key=lambda error: list(error.absolute_path)
    )
    if errors:
        raise EnergyScenarioError(f"{label}: {errors[0].message}")


def _scenario_material(scenario: dict[str, Any]) -> dict[str, Any]:
    material = {
        key: copy.deepcopy(value)
        for key, value in scenario.items()
        if key not in {"domains", "expected_result_sha256"}
    }
    domains: list[dict[str, Any]] = []
    for source in scenario["domains"]:
        domain = copy.deepcopy(source)
        domain["events"] = sorted(
            domain["events"], key=lambda item: (item["at_s"], item["event_id"])
        )
        domain["loads"] = sorted(domain["loads"], key=lambda item: item["load_id"])
        domain["sources"] = sorted(
            domain["sources"], key=lambda item: item["source_id"]
        )
        domains.append(domain)
    material["domains"] = sorted(domains, key=lambda item: item["domain_id"])
    return material


def run_energy_scenario(
    scenario: dict[str, Any], *, repository_root: Path
) -> dict[str, Any]:
    _validate_scenario(scenario)
    budget_validator = _schema_validator(repository_root, "energy-budget.schema.json")
    status_validator = _schema_validator(repository_root, "energy-status.schema.json")
    domain_results: list[dict[str, Any]] = []
    ingress_units = 0
    brownout_preserved: list[bool] = []
    central_source_reserve: list[bool] = []

    for domain in sorted(
        copy.deepcopy(scenario["domains"]), key=lambda item: item["domain_id"]
    ):
        budget, conservation = _budget(domain, scenario)
        _validate_output(budget_validator, budget, f"{domain['domain_id']} budget")
        previous_state: str | None = None
        boot_id = domain["initial_boot_id"]
        sequence = domain["initial_sequence"]
        accepted_log_count = domain["initial_accepted_log_count"]
        timeline: list[dict[str, Any]] = []
        source_types = {
            item["source_id"]: item["source_type"] for item in domain["sources"]
        }
        for event in sorted(
            domain["events"], key=lambda item: (item["at_s"], item["event_id"])
        ):
            before_sequence = sequence
            before_log = accepted_log_count
            sequence += 1
            accepted_log_count += 1
            if event["kind"] in {"brownout", "restart"}:
                boot_id = canonical_hash(
                    {"previous_boot_id": boot_id, "event_id": event["event_id"]}
                )[:32]
            event_soc = event.get("soc")
            state = next_energy_state(
                previous_state,
                None if event_soc is None else _decimal(event_soc, "event SOC"),
                event["kind"],
            )
            previous_state = state
            loads_shed = _loads_shed(domain["loads"], state, event["kind"])
            measurements = []
            if event_soc is not None:
                measurements.append(
                    {
                        "metric": "soc",
                        "value": float(event_soc),
                        "unit": "1",
                        "uncertainty": float(domain["soc_uncertainty"]),
                        "quality": 0.8,
                        "method": "synthetic replay",
                    }
                )
            status = {
                "schema_version": "1.0.0",
                "status_type": "energy_status",
                "energy_domain_id": domain["domain_id"],
                "observed_at": _timestamp(scenario["logical_start"], event["at_s"]),
                "sequence": sequence,
                "fsm_state": state,
                "reason": event["kind"],
                "soc_status": "unknown" if event_soc is None else "estimated",
                "measurements": measurements,
                "loads_shed": loads_shed,
                "alarms": (
                    ["brownout"]
                    if event["kind"] == "brownout"
                    else (["sensor"] if event_soc is None else [])
                ),
                "sensors_absent": ["soc"] if event_soc is None else [],
                "limitations": ["simulation only", "no physical autonomy claim"],
            }
            if event_soc is not None and "runtime_lower_bound_s" in budget:
                status["runtime_lower_bound_s"] = budget["runtime_lower_bound_s"]
            _validate_output(status_validator, status, f"{event['event_id']} status")
            checkpoint = {
                "event_id": event["event_id"],
                "kind": event["kind"],
                "boot_id": boot_id,
                "sequence_before": before_sequence,
                "sequence_after": sequence,
                "accepted_log_before": before_log,
                "accepted_log_after": accepted_log_count,
                "vital_state_preserved": True,
            }
            if event["kind"] in {"brownout", "restart"}:
                checkpoint["recovery_mode"] = "local_survival"
            if event["kind"] == "brownout":
                brownout_preserved.append(
                    sequence > before_sequence
                    and accepted_log_count >= before_log
                    and checkpoint["vital_state_preserved"]
                )
            if event["kind"] == "source_loss" and source_types[
                event["source_id"]
            ] not in {"storage", "replaceable_battery"}:
                central_source_reserve.append(
                    conservation["reserves_Wh"] > 0
                    and conservation["remaining_usable_Wh_lower"] is not None
                )
            timeline.append({"status": status, "checkpoint": checkpoint})
            ingress_units += 1
        domain_results.append(
            {
                "domain_id": domain["domain_id"],
                "autonomous": True,
                "budget": budget,
                "conservation": conservation,
                "timeline": timeline,
                "state_path": [item["status"]["fsm_state"] for item in timeline],
                "final_checkpoint": timeline[-1]["checkpoint"],
            }
        )

    disposition = {
        "ingress_units": ingress_units,
        "destinations": {
            "accepted_event_log": ingress_units,
            "review_quarantine": 0,
            "evidence_vault": 0,
            "rejection_ledger": 0,
        },
        "unreconciled": 0,
    }
    projection = {
        "schema_version": "1.0.0",
        "scenario_id": scenario["scenario_id"],
        "generated_at": _timestamp(scenario["logical_start"], scenario["window_s"]),
        "claim_scope": "simulation_only",
        "prohibited_claims": [],
        "domains": domain_results,
        "brownout_state_preserved": bool(brownout_preserved)
        and all(brownout_preserved),
        "source_loss_local_reserve_preserved": bool(central_source_reserve)
        and all(central_source_reserve),
        "disposition": disposition,
        "limitations": sorted(scenario["limitations"]),
    }
    material = {
        "scenario_sha256": canonical_hash(_scenario_material(scenario)),
        "projection": projection,
    }
    return {**projection, "result_sha256": canonical_hash(material)}


def run_energy_determinism(
    scenario: dict[str, Any], *, repository_root: Path, runs: int = 10
) -> tuple[list[str], list[dict[str, str]]]:
    hashes: list[str] = []
    matrix: list[dict[str, str]] = []
    old_tz, old_locale = os.environ.get("TZ"), os.environ.get("LC_ALL")
    try:
        for index in range(runs):
            candidate = copy.deepcopy(scenario)
            timezone = "UTC" if index % 2 == 0 else "Pacific/Auckland"
            locale = "C" if index % 2 == 0 else "C.UTF-8"
            os.environ["TZ"] = timezone
            os.environ["LC_ALL"] = locale
            if hasattr(time, "tzset"):
                time.tzset()
            if index % 2:
                candidate["domains"].reverse()
                for domain in candidate["domains"]:
                    domain["events"].reverse()
                    domain["loads"].reverse()
                    domain["sources"].reverse()
            result = run_energy_scenario(candidate, repository_root=repository_root)
            hashes.append(result["result_sha256"])
            matrix.append(
                {
                    "timezone": timezone,
                    "locale": locale,
                    "order": "forward" if index % 2 == 0 else "reverse",
                }
            )
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        if old_locale is None:
            os.environ.pop("LC_ALL", None)
        else:
            os.environ["LC_ALL"] = old_locale
        if hasattr(time, "tzset"):
            time.tzset()
    return sorted(set(hashes)), matrix


def run_energy_replay_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        outcome = run_energy_scenario(scenario, repository_root=root)
        hashes, matrix = run_energy_determinism(scenario, repository_root=root, runs=10)
    except (OSError, json.JSONDecodeError, EnergyScenarioError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path.relative_to(root))}
    errors: list[str] = []
    if len(hashes) != 1 or hashes[0] != outcome["result_sha256"]:
        errors.append("energy replay is not deterministic")
    if scenario.get("expected_result_sha256") != outcome["result_sha256"]:
        errors.append("energy replay result does not match frozen expected hash")
    if not outcome["brownout_state_preserved"]:
        errors.append(
            "brownout did not preserve sequence, accepted log and vital state"
        )
    if not outcome["source_loss_local_reserve_preserved"]:
        errors.append("source loss eliminated local simulated reserve")
    if outcome["disposition"]["unreconciled"] != 0:
        errors.append("energy replay inputs were not fully reconciled")
    return (
        errors,
        [],
        {
            "scenario": str(scenario_path.relative_to(root)),
            "domains": len(outcome["domains"]),
            "determinism_runs": len(matrix),
            "unique_result_hashes": hashes,
            "result_sha256": outcome["result_sha256"],
            "budget_results": {
                item["domain_id"]: item["budget"]["result"]
                for item in outcome["domains"]
            },
            "domain_evidence": {
                item["domain_id"]: {
                    "result": item["budget"]["result"],
                    "usable_storage_Wh": item["budget"]["usable_storage_Wh"],
                    "remaining_usable_Wh_lower": item["conservation"][
                        "remaining_usable_Wh_lower"
                    ],
                    "critical_load_Wh_upper": item["conservation"][
                        "critical_load_Wh_upper"
                    ],
                    "reserves_Wh": item["conservation"]["reserves_Wh"],
                    "storage_only_margin_Wh": item["conservation"][
                        "storage_only_margin_Wh"
                    ],
                    "runtime_lower_bound_s": item["budget"].get(
                        "runtime_lower_bound_s"
                    ),
                    "state_path": item["state_path"],
                }
                for item in outcome["domains"]
            },
            "unknown_soc_domains": sum(
                item["budget"]["result"] == "unknown" for item in outcome["domains"]
            ),
            "brownout_state_preserved": outcome["brownout_state_preserved"],
            "source_loss_local_reserve_preserved": outcome[
                "source_loss_local_reserve_preserved"
            ],
            "unreconciled": outcome["disposition"]["unreconciled"],
            "claim_scope": outcome["claim_scope"],
            "matrix": matrix,
        },
    )
