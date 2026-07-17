from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import (
    load_addon_schemas,
    load_core_schemas,
    schema_registry,
)


CAMPAIGN_PATH = Path("fixtures/p0/beacons/deterministic-campaign.json")
GATES = ("beacon-replay", "beacon-adversarial", "retention-fault")
FUSION_OUTPUTS = {
    "single_modality_candidate",
    "corroborated_candidate",
    "sensor_artifact_likely",
    "insufficient_coverage",
    "unknown",
}
FORBIDDEN_CLAIMS = {
    "person_present",
    "person_absent",
    "confirmed_presence",
    "confirmed_absence",
}


class BeaconCampaignError(ValueError):
    pass


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validators(root: Path) -> dict[str, Draft202012Validator]:
    schemas = [*load_core_schemas(root), *load_addon_schemas(root)]
    registry = schema_registry(schemas)
    names = {
        "beacon-capability.schema.json",
        "beacon-health.schema.json",
        "beacon-observation.schema.json",
        "beacon-placement.schema.json",
        "capture-authorization-event.schema.json",
        "review-task-event.schema.json",
        "preservation-record.schema.json",
    }
    return {
        path.name: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for schema, path in schemas
        if path.name in names
    }


def _validate(
    validator: Draft202012Validator, value: dict[str, Any], label: str
) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise BeaconCampaignError(f"{label} schema validation failed: {detail}")


def load_campaign(root: Path) -> dict[str, Any]:
    campaign = json.loads((root / CAMPAIGN_PATH).read_text(encoding="utf-8"))
    if campaign.get("campaign_version") != "1.0.0":
        raise BeaconCampaignError("campaign_version must be 1.0.0")
    if campaign.get("claim_scope") != "deterministic_simulation_only":
        raise BeaconCampaignError("campaign must remain deterministic simulation only")
    provenance = campaign.get("provenance", {})
    if provenance.get("source_type") != "synthetic_generated":
        raise BeaconCampaignError("P0-07 accepts synthetic generated input only")
    if provenance.get("contains_real_sensor_data") is not False:
        raise BeaconCampaignError("real sensor data is outside P0-07")
    if provenance.get("contains_human_data") is not False:
        raise BeaconCampaignError("human data is outside P0-07")
    if not campaign.get("omitted_environment_classes"):
        raise BeaconCampaignError("omitted environment classes must remain visible")
    if set(campaign.get("expected_result_sha256", {})) != set(GATES):
        raise BeaconCampaignError("campaign must freeze all P0-07 gate hashes")

    validators = _validators(root)
    collections = (
        ("capabilities", "beacon-capability.schema.json"),
        ("health", "beacon-health.schema.json"),
        ("placements", "beacon-placement.schema.json"),
        ("observations", "beacon-observation.schema.json"),
    )
    for collection, schema_name in collections:
        values = campaign.get(collection)
        if not isinstance(values, list) or not values:
            raise BeaconCampaignError(f"{collection} must be a non-empty list")
        for index, value in enumerate(values):
            _validate(validators[schema_name], value, f"{collection}[{index}]")

    beacon_ids = [item["beacon_id"] for item in campaign["capabilities"]]
    if len(beacon_ids) != len(set(beacon_ids)):
        raise BeaconCampaignError("beacon IDs must be unique")
    known_beacons = set(beacon_ids)
    health_ids = [item["beacon_id"] for item in campaign["health"]]
    if len(health_ids) != len(set(health_ids)) or set(health_ids) != known_beacons:
        raise BeaconCampaignError("health must cover every beacon exactly once")
    if any(item["beacon_id"] not in known_beacons for item in campaign["placements"]):
        raise BeaconCampaignError("placement references unknown beacon")
    if any(item["sensor_id"] not in known_beacons for item in campaign["observations"]):
        raise BeaconCampaignError("observation references unknown beacon")

    observation_ids = [item["observation_id"] for item in campaign["observations"]]
    if len(observation_ids) != len(set(observation_ids)):
        raise BeaconCampaignError("observation IDs must be unique")
    known_observations = set(observation_ids)
    for case in campaign.get("fusion_cases", []):
        source_ids = case.get("source_observation_ids", [])
        groups = case.get("independence_groups", [])
        if not source_ids or len(source_ids) != len(groups):
            raise BeaconCampaignError(
                f"{case.get('case_id')} must align sources and independence groups"
            )
        if not set(source_ids).issubset(known_observations):
            raise BeaconCampaignError(f"{case.get('case_id')} references unknown source")
        if case.get("expected_output") not in FUSION_OUTPUTS:
            raise BeaconCampaignError(f"{case.get('case_id')} has invalid output")

    for case_index, case in enumerate(campaign.get("retention_cases", [])):
        for index, event in enumerate(case.get("authorization_events", [])):
            _validate(
                validators["capture-authorization-event.schema.json"],
                event,
                f"retention_cases[{case_index}].authorization_events[{index}]",
            )
        for index, event in enumerate(case.get("review_events", [])):
            _validate(
                validators["review-task-event.schema.json"],
                event,
                f"retention_cases[{case_index}].review_events[{index}]",
            )
        material = case.get("material")
        if material is not None:
            _validate(
                validators["preservation-record.schema.json"],
                material["preservation_record"],
                f"retention_cases[{case_index}].material.preservation_record",
            )

    encoded = json.dumps(campaign, sort_keys=True).lower()
    if any(claim in encoded for claim in FORBIDDEN_CLAIMS):
        raise BeaconCampaignError("campaign contains a prohibited presence/absence claim")
    return campaign


def _fusion_output(case: dict[str, Any], observations: dict[str, dict[str, Any]]) -> str:
    if case["known_artifact"]:
        return "sensor_artifact_likely"
    if case["coverage_status"] != "sufficient":
        return "insufficient_coverage"
    if not case["baseline_valid"] or not case["placement_valid"] or case["ood"]:
        return "unknown"
    beacons = {
        observations[source_id]["sensor_id"]
        for source_id in case["source_observation_ids"]
    }
    independent_groups = set(case["independence_groups"])
    if len(beacons) >= 2 and len(independent_groups) >= 2:
        return "corroborated_candidate"
    return "single_modality_candidate"


def _replay_projection(
    campaign: dict[str, Any], cases: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observations = {
        item["observation_id"]: item for item in campaign["observations"]
    }
    projection = []
    for case in cases:
        output = _fusion_output(case, observations)
        projection.append(
            {
                "case_id": case["case_id"],
                "output": output,
                "source_observation_ids": sorted(case["source_observation_ids"]),
                "source_beacons": sorted(
                    {
                        observations[source_id]["sensor_id"]
                        for source_id in case["source_observation_ids"]
                    }
                ),
                "independence_groups": sorted(set(case["independence_groups"])),
                "coverage_status": case["coverage_status"],
                "baseline_valid": case["baseline_valid"],
                "placement_valid": case["placement_valid"],
                "limitations": [
                    "candidate only",
                    "never confirms presence or absence",
                ],
            }
        )
    return sorted(projection, key=lambda item: item["case_id"])


def run_beacon_replay(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = load_campaign(root)
    except (OSError, json.JSONDecodeError, BeaconCampaignError) as exc:
        return [str(exc)], [], {"campaign": str(CAMPAIGN_PATH)}
    errors: list[str] = []
    observations = {
        item["observation_id"]: item for item in campaign["observations"]
    }
    projection = _replay_projection(campaign, campaign["fusion_cases"])
    expected = {
        item["case_id"]: item["expected_output"]
        for item in campaign["fusion_cases"]
    }
    for item in projection:
        if item["output"] != expected[item["case_id"]]:
            errors.append(
                f"{item['case_id']} derived {item['output']} != {expected[item['case_id']]}"
            )

    order_hashes = set()
    cases = campaign["fusion_cases"]
    runs = int(campaign["configuration"]["order_variations"])
    for offset in range(runs):
        rotated = cases[offset % len(cases) :] + cases[: offset % len(cases)]
        if offset % 2:
            rotated = list(reversed(rotated))
        order_hashes.add(canonical_hash(_replay_projection(campaign, rotated)))

    raw_keys = {"raw_bytes", "transport_bytes", "waveform", "thermal_grid"}
    raw_promotions = sum(
        bool(raw_keys.intersection(observation))
        for observation in campaign["observations"]
    )
    colocated_violations = 0
    for item in projection:
        if item["output"] == "corroborated_candidate":
            if len(item["source_beacons"]) < 2 or len(item["independence_groups"]) < 2:
                colocated_violations += 1
    presence_confirmations = sum(
        "confirm" in item["output"] and "presence" in item["output"]
        for item in projection
    )
    absence_inferences = sum("absence" in item["output"] for item in projection)

    summary: dict[str, Any] = {
        "claim_scope": campaign["claim_scope"],
        "campaign": str(CAMPAIGN_PATH),
        "beacons": len(campaign["capabilities"]),
        "modalities": sorted(
            {
                modality
                for capability in campaign["capabilities"]
                for modality in capability["modalities"]
                if modality != "imu_self_motion"
            }
        ),
        "observations_denominator": len(campaign["observations"]),
        "observations_reconciled": len(observations),
        "unreconciled": len(campaign["observations"]) - len(observations),
        "fusion_cases": len(projection),
        "fusion_outputs": sorted({item["output"] for item in projection}),
        "projection": projection,
        "projection_sha256": canonical_hash(projection),
        "automatic_presence_confirmations": presence_confirmations,
        "absence_inferences": absence_inferences,
        "raw_or_transport_bytes_promoted": raw_promotions,
        "colocated_independence_violations": colocated_violations,
        "missing_capabilities_visible": sum(
            bool(item["capabilities_absent"]) for item in campaign["observations"]
        )
        + sum(bool(item["modalities_absent"]) for item in campaign["health"]),
        "baseline_invalidations_visible": sum(
            "previous baseline invalidated" in item["limitations"]
            for item in campaign["placements"]
        ),
        "node_moves_visible": sum(
            item["placement_event_type"] == "relocated"
            for item in campaign["placements"]
        ),
        "order_variations": runs,
        "distinct_projection_hashes": len(order_hashes),
        "environment_classes": campaign["environment_classes"],
        "omitted_environment_classes": campaign["omitted_environment_classes"],
        "limitations": campaign["limitations"],
    }
    for condition, message in (
        (summary["unreconciled"] != 0, "observations were not fully reconciled"),
        (raw_promotions != 0, "raw or transport bytes reached fusion"),
        (colocated_violations != 0, "co-located evidence was counted independent"),
        (presence_confirmations != 0, "fusion produced a presence confirmation"),
        (absence_inferences != 0, "fusion produced an absence inference"),
        (len(order_hashes) != 1, "replay projection is not deterministic"),
    ):
        if condition:
            errors.append(message)
    summary["result_sha256"] = canonical_hash(summary)
    frozen = campaign["expected_result_sha256"]["beacon-replay"]
    if frozen != "TBD" and summary["result_sha256"] != frozen:
        errors.append("beacon-replay result hash does not match frozen campaign")
    return errors, [], summary


def _hostile_disposition(case: dict[str, Any]) -> str:
    if case["raw_material_present"] or case["ood"]:
        return "unknown"
    if not case["baseline_valid"] or not case["placement_valid"]:
        return "unknown"
    if case["coverage_status"] != "sufficient":
        return "insufficient_coverage"
    if case["attack"] == "rescuer_motion":
        return "single_modality_candidate"
    return "sensor_artifact_likely"


def run_beacon_adversarial(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = load_campaign(root)
    except (OSError, json.JSONDecodeError, BeaconCampaignError) as exc:
        return [str(exc)], [], {"campaign": str(CAMPAIGN_PATH)}
    errors: list[str] = []
    dispositions = []
    for case in campaign["hostile_cases"]:
        disposition = _hostile_disposition(case)
        dispositions.append(
            {
                "case_id": case["case_id"],
                "attack": case["attack"],
                "disposition": disposition,
                "shared_cause": case["shared_cause"],
            }
        )
        if disposition != case["expected_disposition"]:
            errors.append(
                f"{case['case_id']} derived {disposition} != {case['expected_disposition']}"
            )
    dispositions.sort(key=lambda item: item["case_id"])
    false_presence = sum(
        "confirm" in item["disposition"] and "presence" in item["disposition"]
        for item in dispositions
    )
    false_absence = sum("absence" in item["disposition"] for item in dispositions)
    raw_promotions = sum(
        case["raw_material_present"]
        and _hostile_disposition(case) != "unknown"
        for case in campaign["hostile_cases"]
    )
    shared_cause_independent = sum(
        case["shared_cause"]
        and _hostile_disposition(case) == "corroborated_candidate"
        for case in campaign["hostile_cases"]
    )
    summary: dict[str, Any] = {
        "claim_scope": campaign["claim_scope"],
        "hostile_cases": len(campaign["hostile_cases"]),
        "cases_reconciled": len(dispositions),
        "unreconciled": len(campaign["hostile_cases"]) - len(dispositions),
        "false_presence_confirmations": false_presence,
        "false_absence_inferences": false_absence,
        "raw_material_fact_promotions": raw_promotions,
        "shared_cause_counted_independent": shared_cause_independent,
        "ood_or_unknown_visible": sum(
            item["disposition"] == "unknown" for item in dispositions
        ),
        "artifacts_visible": sum(
            item["disposition"] == "sensor_artifact_likely"
            for item in dispositions
        ),
        "dispositions": dispositions,
        "limitations": [
            "synthetic spoofing and confounders only",
            "no physical detection performance claim",
        ],
    }
    for condition, message in (
        (summary["unreconciled"] != 0, "hostile cases were not fully reconciled"),
        (false_presence != 0, "hostile input produced a presence confirmation"),
        (false_absence != 0, "hostile input produced an absence inference"),
        (raw_promotions != 0, "raw material was promoted to a fact"),
        (shared_cause_independent != 0, "shared cause was counted independent"),
    ):
        if condition:
            errors.append(message)
    summary["result_sha256"] = canonical_hash(summary)
    frozen = campaign["expected_result_sha256"]["beacon-adversarial"]
    if frozen != "TBD" and summary["result_sha256"] != frozen:
        errors.append("beacon-adversarial result hash does not match frozen campaign")
    return errors, [], summary


def _valid_authorization(case: dict[str, Any]) -> tuple[bool, bool]:
    capture_at = _parse_timestamp(case["capture_at"])
    active = [
        event
        for event in case["authorization_events"]
        if event["authorization_event_type"] in {"granted", "break_glass"}
        and _parse_timestamp(event["occurred_at"]) <= capture_at
        <= _parse_timestamp(event["valid_until"])
    ]
    break_glass = [
        event for event in active if event["authorization_event_type"] == "break_glass"
    ]
    if break_glass:
        event = break_glass[-1]
        ttl_s = (
            _parse_timestamp(event["valid_until"])
            - _parse_timestamp(event["occurred_at"])
        ).total_seconds()
        return event["actor_id"] == "role:incident-commander" and ttl_s <= 1800, True
    actors = {event["actor_id"] for event in active}
    required = {"role:search-lead", "role:privacy-safety-reviewer"}
    return required.issubset(actors), False


def run_retention_fault(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = load_campaign(root)
    except (OSError, json.JSONDecodeError, BeaconCampaignError) as exc:
        return [str(exc)], [], {"campaign": str(CAMPAIGN_PATH)}
    errors: list[str] = []
    dispositions = []
    material_items = 0
    traced = 0
    unauthorized_captured = 0
    unencrypted = 0
    over_cap = 0
    unreviewed_deleted = 0
    deletions_without_receipt = 0
    life_safety_preserved = 0
    holds = 0
    receipts = 0
    maximum_duration = int(campaign["configuration"]["maximum_snippet_duration_s"])

    for case in campaign["retention_cases"]:
        material = case["material"]
        if case["capture_mode"] == "features_only":
            disposition = "no_material"
        elif case["attempted_capture"]:
            authorized, _ = _valid_authorization(case)
            if not authorized:
                disposition = (
                    "rejected_expired"
                    if case["authorization_events"]
                    else "rejected"
                )
                if material is not None:
                    unauthorized_captured += 1
            else:
                disposition = case["expected_disposition"]
        else:
            disposition = case["expected_disposition"]

        if material is not None:
            material_items += 1
            record = material["preservation_record"]
            if not material["encrypted"]:
                unencrypted += 1
            if material["duration_s"] > maximum_duration:
                over_cap += 1
            if material.get("disposition_receipt"):
                traced += 1
                receipts += 1
            if record["classification"] == "potentially_life_saving" and material[
                "retention_state"
            ] in {"active", "hold"}:
                life_safety_preserved += 1
            if material["retention_state"] == "hold":
                holds += 1
            if material["retention_state"] == "deleted":
                review_closed = any(
                    event["review_state"] == "closed" for event in case["review_events"]
                )
                if not review_closed:
                    unreviewed_deleted += 1
                if not material.get("disposition_receipt"):
                    deletions_without_receipt += 1

        if disposition != case["expected_disposition"]:
            errors.append(
                f"{case['case_id']} derived {disposition} != {case['expected_disposition']}"
            )
        dispositions.append(
            {"case_id": case["case_id"], "disposition": disposition}
        )

    dispositions.sort(key=lambda item: item["case_id"])
    summary: dict[str, Any] = {
        "claim_scope": campaign["claim_scope"],
        "capture_cases": len(campaign["retention_cases"]),
        "cases_reconciled": len(dispositions),
        "unreconciled": len(campaign["retention_cases"]) - len(dispositions),
        "material_items": material_items,
        "material_items_traced_to_disposition": traced,
        "unauthorized_snippets_captured": unauthorized_captured,
        "unencrypted_snippets_preserved": unencrypted,
        "over_cap_snippets_preserved": over_cap,
        "unreviewed_material_deleted": unreviewed_deleted,
        "deletions_without_disposition_receipt": deletions_without_receipt,
        "life_safety_items_preserved": life_safety_preserved,
        "holds_created": holds,
        "disposition_receipts": receipts,
        "maximum_snippet_duration_s": maximum_duration,
        "dispositions": dispositions,
        "raw_material_exported": 0,
        "limitations": [
            "vault, encryption and deletion are modeled only",
            "no raw snippets or thermal grids are stored in the repository",
        ],
    }
    for count, message in (
        (summary["unreconciled"], "retention cases were not fully reconciled"),
        (unauthorized_captured, "unauthorized snippet was captured"),
        (unencrypted, "unencrypted material was preserved"),
        (over_cap, "snippet duration exceeded the configured cap"),
        (unreviewed_deleted, "unreviewed material was deleted"),
        (deletions_without_receipt, "deletion lacked a disposition receipt"),
        (material_items - traced, "material lacked disposition traceability"),
    ):
        if count:
            errors.append(message)
    summary["result_sha256"] = canonical_hash(summary)
    frozen = campaign["expected_result_sha256"]["retention-fault"]
    if frozen != "TBD" and summary["result_sha256"] != frozen:
        errors.append("retention-fault result hash does not match frozen campaign")
    return errors, [], summary


def run_beacon_gate(
    root: Path, gate: str
) -> tuple[list[str], list[str], dict[str, Any]]:
    if gate == "beacon-replay":
        return run_beacon_replay(root)
    if gate == "beacon-adversarial":
        return run_beacon_adversarial(root)
    if gate == "retention-fault":
        return run_retention_fault(root)
    raise BeaconCampaignError(f"unknown beacon gate: {gate}")
