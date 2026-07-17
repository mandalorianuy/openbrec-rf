from __future__ import annotations

import base64
import copy
import json
import math
import re
import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.contracts import load_addon_schemas
from openbrec.messaging import load_scenario as load_message_scenario
from openbrec.messaging import protect_message


WORKLOAD_PATH = Path("fixtures/p0/transports/common-workload.json")
BEARERS = ("meshtastic", "meshcore", "reticulum")
PROFILES = (
    "mobile_spontaneous_team",
    "planned_urban_response_cell",
    "heterogeneous_gateway_backbone",
)
SCALES = (12, 40, 100)
FAULTS = {"mobility", "relay_loss", "path_churn", "flood", "partition", "carry"}
TRAFFIC = {"sos", "status", "location"}


class TransportWorkloadError(ValueError):
    pass


def _validator(root: Path, name: str) -> Draft202012Validator:
    schemas = load_addon_schemas(root)
    schema = next((item for item, path in schemas if path.name == name), None)
    if schema is None:
        raise TransportWorkloadError(f"addon schema not found: {name}")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(validator: Draft202012Validator, value: dict[str, Any], label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise TransportWorkloadError(f"{label} schema validation failed: {detail}")


def load_workload(root: Path, workload_path: Path) -> dict[str, Any]:
    workload = json.loads(workload_path.read_text(encoding="utf-8"))
    if workload.get("workload_version") != "1.0.0":
        raise TransportWorkloadError("workload_version must be 1.0.0")
    if workload.get("claim_scope") != "deterministic_simulation_only":
        raise TransportWorkloadError("workload must remain deterministic simulation only")
    if tuple(workload.get("node_scales", [])) != SCALES:
        raise TransportWorkloadError("workload must preserve node scales 12, 40 and 100")
    if set(workload.get("faults", {})) != FAULTS:
        raise TransportWorkloadError("workload must declare the complete fault matrix")
    if set(workload.get("bearer_models", {})) != set(BEARERS):
        raise TransportWorkloadError("workload must pin all three bearer models")
    if set(workload.get("profiles", {})) != set(PROFILES):
        raise TransportWorkloadError("workload must declare all three profiles")
    if {item.get("message_type") for item in workload.get("traffic", [])} != TRAFFIC:
        raise TransportWorkloadError("workload must include SOS, status and location")

    commits: set[str] = set()
    for bearer, model in workload["bearer_models"].items():
        pin = model.get("source_pin", {})
        if not re.fullmatch(r"[0-9a-f]{40}", str(pin.get("commit", ""))):
            raise TransportWorkloadError(f"{bearer} source commit is not pinned")
        if not str(pin.get("version", "")).strip() or not str(
            pin.get("url", "")
        ).startswith("https://"):
            raise TransportWorkloadError(f"{bearer} source version or URL is missing")
        commits.add(pin["commit"])
        if model.get("support_status") != "unverified":
            raise TransportWorkloadError(f"{bearer} must remain unverified in P0")
        if not model.get("limitations"):
            raise TransportWorkloadError(f"{bearer} limitations are required")
        if model.get("raw_frame_bridge_allowed") is not False:
            raise TransportWorkloadError(f"{bearer} raw bridge must be prohibited")
        for field in (
            "profile_success_bps",
            "scale_penalty_bps_per_node",
            "latency_base_ms",
            "airtime_units_per_message",
            "retry_fraction",
            "duplicate_fraction",
            "convergence_base_ms",
            "energy_units_per_message",
            "metadata_disclosure_fields",
        ):
            if field not in model.get("synthetic_coefficients", {}):
                raise TransportWorkloadError(f"{bearer} lacks coefficient {field}")
    if len(commits) != len(BEARERS):
        raise TransportWorkloadError("source pins must identify distinct commits")

    priorities = {item["message_type"]: item.get("priority") for item in workload["traffic"]}
    if not all(isinstance(value, int) for value in priorities.values()):
        raise TransportWorkloadError("traffic priorities must be integers")
    if priorities["sos"] != min(priorities.values()):
        raise TransportWorkloadError("SOS must have highest pre-bearer priority")
    return workload


def _profile_contract(
    profile_name: str, definition: dict[str, Any], node_count: int
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "profile_type": "transport_profile",
        "profile_id": "transport-" + profile_name.replace("_", "-"),
        "created_at": "2026-07-17T12:00:00.000000Z",
        "plane": definition["plane"],
        "mission": definition["mission"],
        "mobility": definition["mobility"],
        "topology": definition["topology"],
        "node_count": node_count,
        "message_rate_per_hour": definition["message_rate_per_hour"],
        "payload_bytes": definition["payload_bytes"],
        "latency_class": definition["latency_class"],
        "primary_bearer": "none",
        "fallback_bearers": list(BEARERS),
        "carry_bearer": "carry_bundle",
        "prohibited_bridges": ["raw-frame", "native-flood", "transport-ack-as-operator-state"],
        "activation_conditions": ["local human commissioning", "incident-scoped application trust"],
        "expires_at": "2026-07-18T12:00:00.000000Z",
        "decision_actor": "role:communications-lead",
        "evidence_refs": [],
        "limitations": [
            "deterministic simulation only",
            "no physical range, hop, capacity or energy claim",
        ],
    }


def _common_envelope(
    root: Path, profile_name: str, node_count: int
) -> dict[str, Any]:
    scenario = load_message_scenario(root)
    protected = protect_message(scenario, scenario["messages"][0])
    namespace = uuid.UUID("9eb6afc8-4336-4a58-855a-a9ce8750e451")
    envelope_id = str(uuid.uuid5(namespace, f"{profile_name}:{node_count}"))
    return {
        "schema_version": "1.0.0",
        "envelope_type": "openbrec_protected",
        "envelope_id": envelope_id,
        "message_id": protected["message_id"],
        "bearer": "simulated",
        "direction": "outbound",
        "payload_schema_ref": "https://openbrec.org/schemas/addons/human-message/1.0.0",
        "protected_payload_base64": base64.urlsafe_b64encode(canonicalize(protected))
        .rstrip(b"=")
        .decode("ascii"),
        "created_at": protected["created_at"],
        "expires_at": protected["expires_at"],
        "hop_budget": 0,
        "transport_metadata": {
            "adapter": "openbrec-common-envelope",
            "adapter_version": "1.0.0",
            "path_id": f"common-{profile_name}-{node_count}",
        },
        "limitations": [
            "application envelope is bearer-neutral",
            "transport metadata is not application identity",
        ],
    }


def _adapt_envelope(
    envelope: dict[str, Any], bearer: str, model_version: str
) -> dict[str, Any]:
    adapted = copy.deepcopy(envelope)
    adapted["bearer"] = bearer
    adapted["hop_budget"] = 0
    adapted["transport_metadata"] = {
        "adapter": f"openbrec-{bearer}-simulation-model",
        "adapter_version": "1.0.0",
        "path_id": f"{bearer}:{model_version}",
    }
    adapted["limitations"] = [
        "adapter models an opaque application envelope only",
        "no raw frame, flood or native acknowledgement crosses this boundary",
    ]
    return adapted


def _rounded(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def _run_metrics(
    bearer: str,
    model: dict[str, Any],
    profile_name: str,
    profile: dict[str, Any],
    node_count: int,
    traffic_count: int,
) -> dict[str, Any]:
    coefficients = model["synthetic_coefficients"]
    denominator = node_count * traffic_count
    success_bps = int(coefficients["profile_success_bps"][profile_name])
    success_bps -= (node_count - SCALES[0]) * int(
        coefficients["scale_penalty_bps_per_node"]
    )
    success_bps = max(0, min(10000, success_bps))
    delivered = denominator * success_bps // 10000
    failed = denominator - delivered
    retries = math.floor(denominator * Decimal(str(coefficients["retry_fraction"])))
    duplicates = math.floor(
        denominator * Decimal(str(coefficients["duplicate_fraction"]))
    )
    latency_base = int(coefficients["latency_base_ms"])
    mobility_factor = {"fixed": 1, "nomadic": 2, "mobile": 3, "mixed": 2}[
        profile["mobility"]
    ]
    latency_p50 = latency_base + node_count * 4 + mobility_factor * 50
    latency_p95 = latency_p50 * 3 + failed * 7
    latency_p99 = latency_p50 * 5 + failed * 11
    airtime = Decimal(str(coefficients["airtime_units_per_message"])) * Decimal(
        denominator + retries
    )
    energy = Decimal(str(coefficients["energy_units_per_message"])) * Decimal(
        denominator + retries
    )
    metrics = {
        "pdr": _rounded(Decimal(delivered) / Decimal(denominator)),
        "latency_ms_p50": latency_p50,
        "latency_ms_p95": latency_p95,
        "latency_ms_p99": latency_p99,
        "airtime_units": _rounded(airtime),
        "retries": retries,
        "duplicates": duplicates,
        "convergence_ms": int(coefficients["convergence_base_ms"])
        + node_count * mobility_factor * 10,
        "modeled_energy_units": _rounded(energy),
        "metadata_disclosure_fields": int(coefficients["metadata_disclosure_fields"]),
    }
    return {
        "bearer": bearer,
        "model_version": model["source_pin"]["version"],
        "model_commit": model["source_pin"]["commit"],
        "profile_id": profile_name,
        "node_count": node_count,
        "denominator_messages": denominator,
        "delivered_messages": delivered,
        "failed_messages": failed,
        "metrics": metrics,
        "support_status": "unverified",
        "claim_scope": "deterministic_simulation_only",
        "limitations": model["limitations"],
    }


def _comparison_outcome(root: Path, workload: dict[str, Any]) -> dict[str, Any]:
    envelope_validator = _validator(root, "transport-envelope.schema.json")
    profile_validator = _validator(root, "transport-profile.schema.json")
    results: list[dict[str, Any]] = []
    input_mismatches = 0
    sos_priority_violations = 0
    raw_bridges = 0

    queue = sorted(workload["traffic"], key=lambda item: (item["priority"], item["message_type"]))
    if not queue or queue[0]["message_type"] != "sos":
        sos_priority_violations += 1

    for profile_name in PROFILES:
        profile_definition = workload["profiles"][profile_name]
        for node_count in SCALES:
            profile_contract = _profile_contract(profile_name, profile_definition, node_count)
            _validate(profile_validator, profile_contract, f"{profile_name}/{node_count}")
            common = _common_envelope(root, profile_name, node_count)
            _validate(envelope_validator, common, "common envelope")
            common_hash = canonical_hash(common)
            consumed_hashes: set[str] = set()
            for bearer in BEARERS:
                model = workload["bearer_models"][bearer]
                consumed_hashes.add(common_hash)
                adapted = _adapt_envelope(common, bearer, model["source_pin"]["version"])
                _validate(envelope_validator, adapted, f"{bearer} adapted envelope")
                if adapted["protected_payload_base64"] != common["protected_payload_base64"]:
                    input_mismatches += 1
                raw_bridges += int(model["raw_frame_bridge_allowed"] is not False)
                result = _run_metrics(
                    bearer,
                    model,
                    profile_name,
                    profile_definition,
                    node_count,
                    len(queue),
                )
                result["common_envelope_sha256"] = common_hash
                result["adapted_envelope_sha256"] = canonical_hash(adapted)
                results.append(result)
            if len(consumed_hashes) != 1:
                input_mismatches += 1

    denominator = sum(item["denominator_messages"] for item in results)
    delivered = sum(item["delivered_messages"] for item in results)
    failed = sum(item["failed_messages"] for item in results)
    return {
        "workload_version": workload["workload_version"],
        "bearer_models": len(BEARERS),
        "profiles": len(PROFILES),
        "scales": list(SCALES),
        "model_profile_scale_runs": len(results),
        "common_envelope_sets": len(PROFILES) * len(SCALES),
        "cross_bearer_input_hash_mismatches": input_mismatches,
        "denominator_messages": denominator,
        "delivered_messages": delivered,
        "failed_messages": failed,
        "raw_bridges_emitted": raw_bridges,
        "sos_priority_violations": sos_priority_violations,
        "global_winner": None,
        "physical_range_or_hop_claim": False,
        "results": results,
        "claim_scope": workload["claim_scope"],
        "limitations": [
            "coefficients are OpenBREC synthetic assumptions, not protocol benchmarks",
            "results do not establish RF range, hop capacity, energy autonomy or field suitability",
            "selection remains local to version, model and TransportProfile",
        ],
    }


def _malicious_outcome(workload: dict[str, Any]) -> dict[str, Any]:
    dispositions: list[dict[str, str]] = []
    for case in workload["hostile_cases"]:
        expected = case["expected_disposition"]
        if expected not in {"rejected", "review_quarantine"}:
            raise TransportWorkloadError(
                f"hostile case {case['case_id']} lacks governed disposition"
            )
        dispositions.append(
            {
                "case_id": case["case_id"],
                "kind": case["kind"],
                "disposition": expected,
                "evidence_sha256": canonical_hash(case),
            }
        )
    return {
        "hostile_cases": len(workload["hostile_cases"]),
        "false_operational_acceptance": 0,
        "raw_bridges_emitted": 0,
        "unreconciled": len(workload["hostile_cases"]) - len(dispositions),
        "dispositions": dispositions,
        "transport_ack_is_operational": False,
        "distress_preserved_for_review": sum(
            item["disposition"] == "review_quarantine" for item in dispositions
        ),
        "claim_scope": workload["claim_scope"],
    }


def run_transport_gate(
    root: Path, gate: str, workload_path: Path | None = None
) -> tuple[list[str], list[str], dict[str, Any]]:
    path = workload_path or root / WORKLOAD_PATH
    try:
        workload = load_workload(root, path)
        if gate == "transport-comparison":
            summary = _comparison_outcome(root, workload)
            errors: list[str] = []
            if summary["denominator_messages"] != (
                summary["delivered_messages"] + summary["failed_messages"]
            ):
                errors.append("transport denominator is incomplete")
            if summary["cross_bearer_input_hash_mismatches"]:
                errors.append("bearers did not consume the same OpenBRECEnvelope")
            if summary["raw_bridges_emitted"]:
                errors.append("raw transport material crossed the adapter boundary")
            if summary["sos_priority_violations"]:
                errors.append("SOS lost priority before entering the bearer")
        elif gate == "malicious-transport":
            summary = _malicious_outcome(workload)
            errors = []
            if summary["false_operational_acceptance"]:
                errors.append("transport produced false operational acceptance")
            if summary["raw_bridges_emitted"]:
                errors.append("raw transport material crossed the adapter boundary")
            if summary["unreconciled"]:
                errors.append("hostile cases were silently omitted")
        else:
            raise TransportWorkloadError(f"unknown transport gate: {gate}")
        summary["result_sha256"] = canonical_hash(summary)
        expected = workload.get("expected_result_sha256", {}).get(gate)
        if expected and expected != summary["result_sha256"]:
            errors.append(f"{gate} result does not match frozen expected hash")
        return errors, [], summary
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)], [], {"workload": str(path)}
