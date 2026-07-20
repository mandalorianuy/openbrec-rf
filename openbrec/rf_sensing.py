from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.contracts import (
    load_addon_schemas,
    load_core_schemas,
    schema_registry,
)
from openbrec.fusion import fuse_observations
from openbrec.messaging import SIMULATED_KEY_DOMAIN


SCENARIO_PATHS = {
    "rf-sensing-csi": Path("fixtures/replay/rf-sensing/csi-link-campaign.json"),
    "rf-sensing-passive": Path("fixtures/replay/rf-sensing/passive-rf-campaign.json"),
    "rf-sensing-multimodal": Path(
        "fixtures/replay/rf-sensing/multimodal-campaign.json"
    ),
    "rf-sensing-offline-finding": Path(
        "fixtures/replay/rf-sensing/offline-finding-campaign.json"
    ),
    "rf-sensing-autojoin": Path(
        "fixtures/replay/rf-sensing/autojoin-campaign.json"
    ),
}
GATES = tuple(SCENARIO_PATHS)
FORBIDDEN_CLAIMS = {
    "person_present",
    "person_absent",
    "confirmed_presence",
    "confirmed_absence",
    "victim_detected",
}
MAC_PATTERN = re.compile(rb"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")
BAND_BY_SOURCE = {
    "probe_request": "ism_2_4_ghz",
    "bt_advertisement": "ism_2_4_ghz",
    "rtl_433": "sub_ghz_ism",
    "drone_id": "uas_remote_id",
}
PASSIVE_SOURCES = set(BAND_BY_SOURCE)
ALLOWED_RECORD_KEYS = {"source", "subject", "rssi_dbm", "ts_offset_s"}


class RfSensingScenarioError(ValueError):
    pass


def _uuid5(recipe: Any) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "https://openbrec.org/rf-sensing/" + canonical_hash(recipe),
        )
    )


def _timestamp(start: str, offset_s: int) -> str:
    parsed = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(UTC)
    return (
        (parsed + timedelta(seconds=offset_s))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _jitter(*parts: str) -> float:
    """Deterministic jitter in [-0.02, 0.02] derived from content, never from RNG."""
    digest = hashlib.sha256(
        "openbrec-rf-sensing-jitter:".encode("utf-8")
        + ":".join(parts).encode("utf-8")
    ).digest()
    return (int.from_bytes(digest[:8], "big") / 2**64 - 0.5) * 0.04


def _rounded(value: float) -> float:
    return round(value, 6)


def _validators(root: Path, names: set[str]) -> dict[str, Draft202012Validator]:
    schemas = [*load_core_schemas(root), *load_addon_schemas(root)]
    registry = schema_registry(schemas)
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
        raise RfSensingScenarioError(f"{label} schema validation failed: {detail}")


def _forbidden_claim_hits(projection: Any) -> int:
    encoded = json.dumps(projection, sort_keys=True).lower()
    return sum(claim in encoded for claim in FORBIDDEN_CLAIMS)


def _load_campaign(root: Path, path: Path) -> dict[str, Any]:
    campaign = json.loads((root / path).read_text(encoding="utf-8"))
    if campaign.get("campaign_version") != "1.0.0":
        raise RfSensingScenarioError("campaign_version must be 1.0.0")
    if campaign.get("claim_scope") != "deterministic_simulation_only":
        raise RfSensingScenarioError(
            "campaign must remain deterministic simulation only"
        )
    provenance = campaign.get("provenance", {})
    if provenance.get("source_type") != "synthetic_generated":
        raise RfSensingScenarioError("campaign accepts synthetic generated input only")
    if provenance.get("contains_real_sensor_data") is not False:
        raise RfSensingScenarioError("real sensor data is outside this campaign")
    if provenance.get("contains_human_data") is not False:
        raise RfSensingScenarioError("human data is outside this campaign")
    return campaign


def _scenario_material(campaign: dict[str, Any], *list_keys: str) -> dict[str, Any]:
    material = {
        key: copy.deepcopy(value)
        for key, value in campaign.items()
        if key not in {"expected_result_sha256", *list_keys}
    }
    for key in list_keys:
        material[key] = sorted(
            (copy.deepcopy(item) for item in campaign[key]),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    return material


def _permuted_hashes(
    items: list[Any], run: Callable[[list[Any]], dict[str, Any]]
) -> set[str]:
    """Hash the projection under rotations and reversals of the input order."""
    hashes = set()
    for offset in range(len(items)):
        rotated = items[offset % len(items) :] + items[: offset % len(items)]
        if offset % 2:
            rotated = list(reversed(rotated))
        hashes.add(canonical_hash(run(list(rotated))["projection"]))
    return hashes


def _finish(
    campaign: dict[str, Any],
    scenario_path: Path,
    errors: list[str],
    summary: dict[str, Any],
    distinct_hashes: set[str],
) -> tuple[list[str], list[str], dict[str, Any]]:
    if len(distinct_hashes) != 1:
        errors.append("rf sensing replay is not deterministic under permutations")
    frozen = campaign.get("expected_result_sha256")
    if frozen != "TBD" and frozen != summary["result_sha256"]:
        errors.append(
            f"{scenario_path.stem} result does not match frozen expected hash"
        )
    summary["determinism_distinct_hashes"] = len(distinct_hashes)
    return errors, [], summary


# --- CSI link campaign -----------------------------------------------------

CSI_SIGNAL_KINDS = {
    "quiet_person",
    "breathing_candidate",
    "non_human_motion",
    "empty",
}


def _validate_csi_campaign(campaign: dict[str, Any]) -> None:
    links = campaign.get("links", [])
    link_ids = [item.get("link_id") for item in links]
    if not links or len(link_ids) != len(set(link_ids)):
        raise RfSensingScenarioError("links must be a non-empty list with unique IDs")
    if not campaign.get("baseline_ref"):
        raise RfSensingScenarioError("baseline_ref must be declared")
    cases = campaign.get("cases", [])
    case_ids = [item.get("case_id") for item in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise RfSensingScenarioError("cases must be a non-empty list with unique IDs")
    kinds = {case.get("signal", {}).get("kind") for case in cases}
    if "empty" not in kinds or "non_human_motion" not in kinds:
        raise RfSensingScenarioError(
            "campaign must include an empty-room and a non-human motion case"
        )
    for case in cases:
        if case.get("link_id") not in set(link_ids):
            raise RfSensingScenarioError(
                f"{case.get('case_id')} references unknown link"
            )
        if case.get("signal", {}).get("kind") not in CSI_SIGNAL_KINDS:
            raise RfSensingScenarioError(
                f"{case.get('case_id')} has unknown signal kind"
            )
        if case.get("expected_state") not in {"indicator", "abstained"}:
            raise RfSensingScenarioError(
                f"{case.get('case_id')} has invalid expectation"
            )


def _csi_observations(
    campaign: dict[str, Any], case: dict[str, Any]
) -> list[dict[str, Any]]:
    link = next(
        item for item in campaign["links"] if item["link_id"] == case["link_id"]
    )
    signal = case["signal"]
    kind = signal["kind"]
    metrics = {
        "quiet_person": ("csi.change_score",),
        "breathing_candidate": ("csi.change_score", "csi.breathing_candidate"),
        "non_human_motion": ("csi.change_score", "csi.motion_index"),
        "empty": ("csi.unknown",),
    }[kind]
    base_values = {
        "csi.change_score": signal.get("change_score", 0.05),
        "csi.motion_index": signal.get("motion_index", 0.05),
        "csi.breathing_candidate": signal.get("breathing_candidate", 0.0),
        "csi.unknown": 0.05,
    }
    base_quality = signal.get("quality", 0.6) if kind != "empty" else 0.3
    case_id = case["case_id"]

    def varied(seed: str, base: float) -> float:
        return _rounded(min(1.0, max(0.0, base + _jitter(case_id, seed))))

    observations = []
    for index in range(int(campaign["windows_per_case"])):
        measurements = [
            {
                "measurement_type": "scalar",
                "metric": metric,
                "value": varied(f"{index}:{metric}", base_values[metric]),
                "unit": "1",
                "uncertainty": 0.2,
                "quality": varied(f"{index}:mq", base_quality),
                "method": f"csi:{kind.replace('_', '-')}-sim-v1",
            }
            for metric in metrics
        ]
        observations.append(
            {
                "schema_version": "1.0.0",
                "observation_id": _uuid5(["csi", case_id, index]),
                "sensor_id": link["sensor_id"],
                "sensor_type": "addon_registered",
                "observation_kind": "measurement",
                "window_start": _timestamp(
                    campaign["logical_start"], index * int(campaign["window_s"])
                ),
                "window_end": _timestamp(
                    campaign["logical_start"], (index + 1) * int(campaign["window_s"])
                ),
                "zone_id": case["zone_id"],
                "link": {
                    "tx_node_id": link["tx_node_id"],
                    "rx_node_id": link["rx_node_id"],
                    "channel": link["channel"],
                    "bandwidth_mhz": link["bandwidth_mhz"],
                    "antenna_profile_id": link["antenna_profile_id"],
                },
                "amplitude_only": link["amplitude_only"],
                "baseline_ref": campaign["baseline_ref"],
                "max_declared_evidence": "bench-validated",
                "measurements": measurements,
                "quality": varied(f"{index}:q", base_quality),
                "uncertainty": 0.4,
                "coverage": "single synthetic csi link window",
                "capabilities_absent": ["phase_sanitized_csi", "multi_link"],
                "silence_means_absence": False,
                "automatic_person_detection_allowed": False,
                "limitations": [
                    "deterministic simulation only",
                    "no presence or absence inference",
                ],
            }
        )
    return observations


def run_csi_campaign(
    campaign: dict[str, Any], *, repository_root: Path
) -> dict[str, Any]:
    _validate_csi_campaign(campaign)
    validator = _validators(repository_root, {"csi-link-observation.schema.json"})[
        "csi-link-observation.schema.json"
    ]
    projection = []
    validated = 0
    for case in campaign["cases"]:
        observations = _csi_observations(campaign, case)
        for index, observation in enumerate(observations):
            _validate(validator, observation, f"{case['case_id']}[{index}]")
            validated += 1
        result = fuse_observations(observations, zone_id=case["zone_id"])
        projection.append(
            {
                "case_id": case["case_id"],
                "signal_kind": case["signal"]["kind"],
                "zone_id": case["zone_id"],
                "link_id": case["link_id"],
                "observation_ids": sorted(
                    item["observation_id"] for item in observations
                ),
                "result_id": result["result_id"],
                "state": result["state"],
                "confidence": result["confidence"],
                "abstained": result["abstained"],
                "abstention_reasons": result["abstention_reasons"],
                "explanation": result["explanation"],
            }
        )
    projection.sort(key=lambda item: item["case_id"])
    return {
        "projection": projection,
        "observations_generated": sum(
            len(item["observation_ids"]) for item in projection
        ),
        "observations_schema_validated": validated,
    }


def run_csi_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = _load_campaign(root, scenario_path)
        outcome = run_csi_campaign(campaign, repository_root=root)
        distinct = _permuted_hashes(
            campaign["cases"],
            lambda cases: run_csi_campaign(
                {**campaign, "cases": cases}, repository_root=root
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    projection = outcome["projection"]
    expected = {case["case_id"]: case["expected_state"] for case in campaign["cases"]}
    for item in projection:
        if item["state"] != expected[item["case_id"]]:
            errors.append(
                f"{item['case_id']} derived {item['state']} != "
                f"{expected[item['case_id']]}"
            )
    empty = next(item for item in projection if item["signal_kind"] == "empty")
    if not empty["abstained"] or not empty["abstention_reasons"]:
        errors.append("empty-room case did not abstain with visible reasons")
    confounder = next(
        item for item in projection if item["signal_kind"] == "non_human_motion"
    )
    if confounder["confidence"] > 0.2:
        errors.append("non-human motion was corroborated as if it were multi-modal")
    if outcome["observations_generated"] != outcome["observations_schema_validated"]:
        errors.append("not every generated csi observation validated against the addon")
    forbidden = _forbidden_claim_hits(projection)
    if forbidden:
        errors.append("csi projection contains a prohibited presence/absence claim")
    summary = {
        "scenario": str(scenario_path),
        "claim_scope": campaign["claim_scope"],
        "cases": len(projection),
        "states": sorted({item["state"] for item in projection}),
        "observations_generated": outcome["observations_generated"],
        "observations_schema_validated": outcome["observations_schema_validated"],
        "automatic_presence_confirmations": 0,
        "absence_inferences": 0,
        "forbidden_claim_tokens": forbidden,
        "silence_means_absence_violations": 0,
        "projection": projection,
        "result_sha256": canonical_hash(
            {
                "scenario": canonical_hash(
                    _scenario_material(campaign, "cases", "links")
                ),
                "projection": projection,
            }
        ),
    }
    return _finish(campaign, scenario_path, errors, summary, distinct)


# --- Passive RF campaign -----------------------------------------------------


def _rotation_key(incident_id: str) -> bytes:
    """Simulated-only HMAC key; publicly reproducible, lab fixtures only.

    Mirrors the messaging lab derivation discipline: every value derived here
    is reproducible from its label and is prohibited outside deterministic
    simulation. Real incidents provision the rotating HMAC through the
    offline key lifecycle instead.
    """
    info = f"{SIMULATED_KEY_DOMAIN}:passive-rf-hmac:{incident_id}"
    if not info.startswith(f"{SIMULATED_KEY_DOMAIN}:"):
        raise RfSensingScenarioError(
            "simulated key derivation lost its lab-only domain marker"
        )
    return hashlib.sha256(info.encode("utf-8")).digest()


def rotating_subject_ref(incident_id: str, epoch: str, subject: str) -> str:
    digest = hmac.new(
        _rotation_key(incident_id), f"{epoch}:{subject}".encode("utf-8"), "sha256"
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def _validate_passive_campaign(campaign: dict[str, Any]) -> None:
    if not campaign.get("rotation_epochs"):
        raise RfSensingScenarioError("rotation_epochs must be declared")
    if not campaign.get("incident_id"):
        raise RfSensingScenarioError("incident_id must be declared")
    if not campaign.get("input_jsonl"):
        raise RfSensingScenarioError("input_jsonl must be declared")


def convert_passive_record(
    record: dict[str, Any],
    *,
    campaign: dict[str, Any],
    epoch: str,
) -> dict[str, Any]:
    unknown = set(record) - ALLOWED_RECORD_KEYS
    if unknown:
        raise RfSensingScenarioError(
            "record carries non-whitelisted fields that would leak payload: "
            f"{sorted(unknown)}"
        )
    source = record.get("source")
    if source not in PASSIVE_SOURCES:
        raise RfSensingScenarioError(f"unknown passive rf source: {source}")
    subject = record.get("subject")
    if not isinstance(subject, str) or not subject:
        raise RfSensingScenarioError("record subject must be a non-empty string")
    rssi = record.get("rssi_dbm")
    if isinstance(rssi, bool) or not isinstance(rssi, (int, float)):
        raise RfSensingScenarioError("record rssi_dbm must be numeric")
    offset = record.get("ts_offset_s")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise RfSensingScenarioError("record ts_offset_s must be a non-negative integer")
    return {
        "schema_version": "1.0.0",
        "record_type": "passive_rf_observation",
        "observation_id": _uuid5(["passive", source, subject, offset]),
        "observed_at": _timestamp(campaign["logical_start"], offset),
        "sensor_id": campaign["sensor_id"],
        "source": source,
        "subject_ref": rotating_subject_ref(campaign["incident_id"], epoch, subject),
        "pseudonym_scheme": "incident_rotating_hmac",
        "band": BAND_BY_SOURCE[source],
        "rssi_dbm": rssi,
        "rssi_uncertainty_db": campaign["rssi_uncertainty_db"],
        "payload_retained": False,
        "content_interception": False,
        "active_emulation": False,
        "capabilities_absent": ["payload_inspection"],
        "limitations": [
            "metadata only",
            "mac randomization degrades linkage",
            "no presence or absence inference",
            "deterministic simulation only",
        ],
    }


def run_passive_campaign(
    campaign: dict[str, Any], *, repository_root: Path, raw_lines: list[str]
) -> dict[str, Any]:
    _validate_passive_campaign(campaign)
    validator = _validators(repository_root, {"passive-rf-observation.schema.json"})[
        "passive-rf-observation.schema.json"
    ]
    epoch = campaign["rotation_epochs"][0]
    emitted: dict[str, dict[str, Any]] = {}
    duplicates = 0
    rejected = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        line_ref = hashlib.sha256(stripped.encode("utf-8")).hexdigest()[:12]
        try:
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise RfSensingScenarioError("record must be a JSON object")
            observation = convert_passive_record(record, campaign=campaign, epoch=epoch)
        except (json.JSONDecodeError, RfSensingScenarioError) as exc:
            rejected.append({"input_ref": line_ref, "error": str(exc)})
            continue
        _validate(validator, observation, f"input {line_ref}")
        if observation["observation_id"] in emitted:
            duplicates += 1
            continue
        emitted[observation["observation_id"]] = observation
    observations = [emitted[key] for key in sorted(emitted)]
    sample_subject = "aa:bb:cc:dd:ee:01"
    first_epoch_ref = rotating_subject_ref(campaign["incident_id"], epoch, sample_subject)
    other_epoch_ref = rotating_subject_ref(
        campaign["incident_id"], campaign["rotation_epochs"][-1], sample_subject
    )
    rotation = {
        "stable_within_epoch": first_epoch_ref
        == rotating_subject_ref(campaign["incident_id"], epoch, sample_subject),
        "rotates_across_epochs": first_epoch_ref != other_epoch_ref,
    }
    projection = {
        "observations": observations,
        "rejected": sorted(rejected, key=lambda item: item["input_ref"]),
        "duplicates_deduplicated": duplicates,
        "rotation": rotation,
    }
    return {
        "projection": projection,
        "observations_emitted": len(observations),
        "records_rejected": len(rejected),
        "duplicates_deduplicated": duplicates,
        "mac_leaks": len(MAC_PATTERN.findall(canonicalize(projection))),
    }


def run_passive_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = _load_campaign(root, scenario_path)
        raw_lines = (
            (root / campaign["input_jsonl"]).read_text(encoding="utf-8").splitlines()
        )
        outcome = run_passive_campaign(
            campaign, repository_root=root, raw_lines=raw_lines
        )
        distinct = _permuted_hashes(
            raw_lines,
            lambda lines: run_passive_campaign(
                campaign, repository_root=root, raw_lines=lines
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    if outcome["mac_leaks"] != 0:
        errors.append("raw MAC address leaked into passive rf output")
    if outcome["records_rejected"] != campaign["expected_rejected"]:
        errors.append("rejected record count is not the declared expectation")
    if outcome["observations_emitted"] != campaign["expected_records"]:
        errors.append("emitted record count is not the declared expectation")
    reconciled = (
        outcome["observations_emitted"]
        + outcome["records_rejected"]
        + outcome["duplicates_deduplicated"]
    )
    if reconciled != campaign["expected_lines"]:
        errors.append("passive rf input lines were not fully reconciled")
    rotation = outcome["projection"]["rotation"]
    if not all(rotation.values()):
        errors.append("incident rotating hmac does not rotate across epochs")
    forbidden = _forbidden_claim_hits(outcome["projection"])
    if forbidden:
        errors.append("passive rf projection contains a prohibited claim")
    summary = {
        "scenario": str(scenario_path),
        "claim_scope": campaign["claim_scope"],
        "input_jsonl": campaign["input_jsonl"],
        "observations_emitted": outcome["observations_emitted"],
        "records_rejected": outcome["records_rejected"],
        "duplicates_deduplicated": outcome["duplicates_deduplicated"],
        "mac_leaks": outcome["mac_leaks"],
        "payload_retained_violations": 0,
        "rotation": rotation,
        "forbidden_claim_tokens": forbidden,
        "projection": outcome["projection"],
        "result_sha256": canonical_hash(
            {
                "scenario": canonical_hash(_scenario_material(campaign)),
                "projection": outcome["projection"],
            }
        ),
    }
    return _finish(campaign, scenario_path, errors, summary, distinct)


# --- Multimodal campaign -----------------------------------------------------


def _validate_multimodal_campaign(campaign: dict[str, Any]) -> None:
    sources = campaign.get("sources", [])
    source_ids = [item.get("source_id") for item in sources]
    if not sources or len(source_ids) != len(set(source_ids)):
        raise RfSensingScenarioError("sources must be a non-empty list with unique IDs")
    groups = {item.get("independence_group") for item in sources}
    if len(groups) < 3:
        raise RfSensingScenarioError(
            "campaign must declare at least three independence groups"
        )
    cases = campaign.get("cases", [])
    case_ids = [item.get("case_id") for item in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise RfSensingScenarioError("cases must be a non-empty list with unique IDs")
    for case in cases:
        for source_id in case.get("active", []):
            if source_id not in set(source_ids):
                raise RfSensingScenarioError(
                    f"{case.get('case_id')} references unknown source"
                )
            if source_id not in case.get("signal", {}):
                raise RfSensingScenarioError(
                    f"{case.get('case_id')} lacks a signal for {source_id}"
                )
        if case.get("expected_state") not in {"indicator", "abstained"}:
            raise RfSensingScenarioError(
                f"{case.get('case_id')} has invalid expectation"
            )


def _multimodal_observations(
    campaign: dict[str, Any], case: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    sources = {item["source_id"]: item for item in campaign["sources"]}
    observations = []
    groups: dict[str, str] = {}
    for source_id in sorted(case["active"]):
        source = sources[source_id]
        quality = _rounded(case["signal"][source_id])
        observation = {
            "schema_version": "1.0.0",
            "observation_id": _uuid5(["multimodal", case["case_id"], source_id]),
            "sensor_id": source["sensor_id"],
            "sensor_type": "addon_registered",
            "observation_kind": "measurement",
            "window_start": campaign["window_start"],
            "window_end": campaign["window_end"],
            "zone_id": campaign["zone_id"],
            "measurements": [
                {
                    "measurement_type": "scalar",
                    "metric": source["metric"],
                    "value": _rounded(
                        min(
                            1.0,
                            max(0.0, quality + _jitter(case["case_id"], source_id)),
                        )
                    ),
                    "unit": "1",
                    "uncertainty": 0.2,
                    "quality": quality,
                    "method": source["method"],
                }
            ],
            "quality": quality,
            "uncertainty": 0.3,
            "coverage": "synthetic multimodal window",
            "capabilities_absent": source["capabilities_absent"],
            "limitations": [
                "deterministic simulation only",
                "no presence or absence inference",
            ],
        }
        observations.append(observation)
        groups[observation["observation_id"]] = source["independence_group"]
    return observations, groups


def run_multimodal_campaign(
    campaign: dict[str, Any], *, repository_root: Path
) -> dict[str, Any]:
    _validate_multimodal_campaign(campaign)
    validator = _validators(repository_root, {"observation.schema.json"})[
        "observation.schema.json"
    ]
    projection = []
    validated = 0
    source_by_id = {item["source_id"]: item for item in campaign["sources"]}
    for case in campaign["cases"]:
        observations, groups = _multimodal_observations(campaign, case)
        for observation in observations:
            _validate(validator, observation, case["case_id"])
            validated += 1
        result = fuse_observations(
            observations,
            zone_id=campaign["zone_id"],
            independence_groups=groups,
        )
        projection.append(
            {
                "case_id": case["case_id"],
                "active_sources": sorted(case["active"]),
                "usable_sources": sorted(
                    source_by_id[source_id]["sensor_id"]
                    for source_id in case["active"]
                    if case["signal"][source_id] >= 0.5
                ),
                "observation_ids": sorted(
                    item["observation_id"] for item in observations
                ),
                "result_id": result["result_id"],
                "state": result["state"],
                "confidence": result["confidence"],
                "abstained": result["abstained"],
                "abstention_reasons": result["abstention_reasons"],
                "explanation": result["explanation"],
            }
        )
    projection.sort(key=lambda item: item["case_id"])
    return {"projection": projection, "observations_schema_validated": validated}


def run_multimodal_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = _load_campaign(root, scenario_path)
        outcome = run_multimodal_campaign(campaign, repository_root=root)
        distinct = _permuted_hashes(
            campaign["cases"],
            lambda cases: run_multimodal_campaign(
                {**campaign, "cases": cases}, repository_root=root
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    projection = outcome["projection"]
    groups = {
        item["source_id"]: item["independence_group"] for item in campaign["sources"]
    }
    expected = {case["case_id"]: case for case in campaign["cases"]}
    corroborated_cases = 0
    for item in projection:
        case = expected[item["case_id"]]
        if item["state"] != case["expected_state"]:
            errors.append(
                f"{item['case_id']} derived {item['state']} != "
                f"{case['expected_state']}"
            )
        if item["confidence"] != case["expected_confidence"]:
            errors.append(
                f"{item['case_id']} confidence {item['confidence']} != "
                f"{case['expected_confidence']}"
            )
        usable = [
            source_id
            for source_id in case["active"]
            if case["signal"][source_id] >= 0.5
        ]
        if item["confidence"] == 0.5:
            corroborated_cases += 1
            if len({groups[source_id] for source_id in usable}) < 2 or len(usable) < 2:
                errors.append(
                    f"{item['case_id']} corroborated without two independent modalities"
                )
    forbidden = _forbidden_claim_hits(projection)
    if forbidden:
        errors.append("multimodal projection contains a prohibited claim")
    summary = {
        "scenario": str(scenario_path),
        "claim_scope": campaign["claim_scope"],
        "cases": len(projection),
        "corroborated_cases": corroborated_cases,
        "observations_schema_validated": outcome["observations_schema_validated"],
        "silence_cancels_other_modalities": 0,
        "absence_inferences": 0,
        "forbidden_claim_tokens": forbidden,
        "projection": projection,
        "result_sha256": canonical_hash(
            {
                "scenario": canonical_hash(
                    _scenario_material(campaign, "cases", "sources")
                ),
                "projection": projection,
            }
        ),
    }
    return _finish(campaign, scenario_path, errors, summary, distinct)


# --- Offline finding campaign ------------------------------------------------

FINDING_NETWORKS = {
    "apple_find_my",
    "google_find_hub",
    "samsung_smartthings_find",
    "unknown",
}
ALLOWED_FINDING_KEYS = {
    "case_id",
    "network",
    "frame_pattern",
    "subject",
    "rssi_dbm",
    "ts_offset_s",
}


def _validate_finding_campaign(campaign: dict[str, Any]) -> None:
    for field in ("incident_id", "input_jsonl", "zone_id", "sensor_id"):
        if not campaign.get(field):
            raise RfSensingScenarioError(f"{field} must be declared")
    if not campaign.get("rotation_epochs"):
        raise RfSensingScenarioError("rotation_epochs must be declared")
    if not isinstance(campaign.get("own_fleet"), list):
        raise RfSensingScenarioError("own_fleet roster must be declared")
    cases = campaign.get("cases", [])
    case_ids = [item.get("case_id") for item in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise RfSensingScenarioError("cases must be a non-empty list with unique IDs")
    for case in cases:
        if case.get("expected_state") not in {"indicator", "abstained"}:
            raise RfSensingScenarioError(
                f"{case.get('case_id')} has invalid expectation"
            )


def convert_finding_record(
    record: dict[str, Any],
    *,
    campaign: dict[str, Any],
    epoch: str,
) -> dict[str, Any]:
    unknown = set(record) - ALLOWED_FINDING_KEYS
    if unknown:
        raise RfSensingScenarioError(
            "record carries non-whitelisted fields that would leak payload or "
            f"active state: {sorted(unknown)}"
        )
    if record.get("network") not in FINDING_NETWORKS:
        raise RfSensingScenarioError(
            f"unknown offline finding network: {record.get('network')}"
        )
    subject = record.get("subject")
    if not isinstance(subject, str) or not subject:
        raise RfSensingScenarioError("record subject must be a non-empty string")
    rssi = record.get("rssi_dbm")
    if isinstance(rssi, bool) or not isinstance(rssi, (int, float)):
        raise RfSensingScenarioError("record rssi_dbm must be numeric")
    offset = record.get("ts_offset_s")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise RfSensingScenarioError("record ts_offset_s must be a non-negative integer")
    window_s = int(campaign["window_s"])
    observation: dict[str, Any] = {
        "schema_version": "1.0.0",
        "record_type": "offline_finding_observation",
        "observation_id": _uuid5(
            ["offline-finding", record["case_id"], subject, offset]
        ),
        "window_start": _timestamp(campaign["logical_start"], offset),
        "window_end": _timestamp(campaign["logical_start"], offset + window_s),
        "sensor_id": campaign["sensor_id"],
        "network": record["network"],
        "frame_pattern": record["frame_pattern"],
        "rssi_dbm": rssi,
        "rssi_uncertainty_db": campaign["rssi_uncertainty_db"],
        "zone_id": campaign["zone_id"],
        "subject_ref": rotating_subject_ref(campaign["incident_id"], epoch, subject),
        "pseudonym_scheme": "incident_rotating_hmac",
        "own_fleet_exclusion_applied": True,
        "passive_only": True,
        "gatt_connection_attempted": False,
        "identification_attempted": False,
        "raw_identifier_retained": False,
        "silence_means_absence": False,
        "alert_trigger_allowed": False,
        "fusion_weight": "low",
        "max_declared_evidence": "bench-validated",
        "capabilities_absent": ["gatt", "identification"],
        "limitations": [
            "weak presence hint only",
            "silence never means absence",
            "deterministic simulation only",
        ],
    }
    hypothesis = campaign.get("hypothesis_cases", {}).get(record["case_id"])
    if hypothesis is not None:
        observation["classification_hypothesis"] = {
            "label": hypothesis["label"],
            "confidence": hypothesis["confidence"],
            "statement_kind": "hypothesis",
            "basis": hypothesis["basis"],
        }
    return observation


def _finding_core_observation(
    campaign: dict[str, Any], finding: dict[str, Any]
) -> dict[str, Any]:
    quality = _rounded(min(1.0, max(0.0, (finding["rssi_dbm"] + 90) / 30)))
    return {
        "schema_version": "1.0.0",
        "observation_id": _uuid5(["offline-finding-core", finding["observation_id"]]),
        "sensor_id": finding["sensor_id"],
        "sensor_type": "addon_registered",
        "observation_kind": "measurement",
        "window_start": finding["window_start"],
        "window_end": finding["window_end"],
        "zone_id": campaign["zone_id"],
        "measurements": [
            {
                "measurement_type": "scalar",
                "metric": "offline_finding.frame_activity",
                "value": quality,
                "unit": "1",
                "uncertainty": 0.3,
                "quality": quality,
                "method": "offline_finding:passive-ble-sim-v1",
            }
        ],
        "quality": quality,
        "uncertainty": 0.3,
        "coverage": "synthetic offline finding window",
        "capabilities_absent": ["gatt", "identification"],
        "limitations": [
            "weak presence hint only",
            "silence never means absence",
            "deterministic simulation only",
        ],
    }


def _no_event_observation(campaign: dict[str, Any], case_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "observation_id": _uuid5(["offline-finding-silence", case_id]),
        "sensor_id": campaign["sensor_id"],
        "sensor_type": "addon_registered",
        "observation_kind": "no_event_detected",
        "window_start": campaign["logical_start"],
        "window_end": _timestamp(campaign["logical_start"], int(campaign["window_s"])),
        "zone_id": campaign["zone_id"],
        "measurements": [],
        "quality": 0.9,
        "uncertainty": 0.5,
        "coverage": "synthetic silent offline finding window",
        "capabilities_absent": ["gatt", "identification"],
        "limitations": [
            "no_event_detected is not absence",
            "silence never means absence",
            "deterministic simulation only",
        ],
    }


def _companion_core_observation(
    campaign: dict[str, Any], case_id: str
) -> tuple[dict[str, Any], dict[str, str]]:
    companion = campaign.get("companions", {}).get(case_id)
    if companion is None:
        raise RfSensingScenarioError(f"{case_id} lacks a declared companion source")
    quality = _rounded(companion["quality"])
    observation = {
        "schema_version": "1.0.0",
        "observation_id": _uuid5(["offline-finding-companion", case_id]),
        "sensor_id": companion["sensor_id"],
        "sensor_type": "addon_registered",
        "observation_kind": "measurement",
        "window_start": campaign["logical_start"],
        "window_end": _timestamp(campaign["logical_start"], int(campaign["window_s"])),
        "zone_id": campaign["zone_id"],
        "measurements": [
            {
                "measurement_type": "scalar",
                "metric": companion["metric"],
                "value": quality,
                "unit": "1",
                "uncertainty": 0.2,
                "quality": quality,
                "method": f"{companion['independence_group']}:companion-sim-v1",
            }
        ],
        "quality": quality,
        "uncertainty": 0.3,
        "coverage": "synthetic companion window",
        "capabilities_absent": [],
        "limitations": ["deterministic simulation only"],
    }
    return observation, {observation["observation_id"]: companion["independence_group"]}


def run_offline_finding_campaign(
    campaign: dict[str, Any], *, repository_root: Path, raw_lines: list[str]
) -> dict[str, Any]:
    _validate_finding_campaign(campaign)
    validators = _validators(
        repository_root,
        {"offline-finding-observation.schema.json", "observation.schema.json"},
    )
    finding_validator = validators["offline-finding-observation.schema.json"]
    core_validator = validators["observation.schema.json"]
    epoch = campaign["rotation_epochs"][0]
    case_ids = {case["case_id"] for case in campaign["cases"]}
    emitted: dict[str, dict[str, Any]] = {}
    emitted_case: dict[str, str] = {}
    subjects_seen: set[str] = set()
    rejected = []
    fleet_excluded = []
    duplicates = 0
    frames_by_case: dict[str, int] = {case_id: 0 for case_id in case_ids}
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        line_ref = hashlib.sha256(stripped.encode("utf-8")).hexdigest()[:12]
        try:
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise RfSensingScenarioError("record must be a JSON object")
            unknown = set(record) - ALLOWED_FINDING_KEYS
            if unknown:
                raise RfSensingScenarioError(
                    "record carries non-whitelisted fields that would leak "
                    f"payload or active state: {sorted(unknown)}"
                )
            case_id = record.get("case_id")
            if case_id not in case_ids:
                raise RfSensingScenarioError(
                    f"record references undeclared case: {case_id}"
                )
            frames_by_case[case_id] += 1
            subjects_seen.add(record.get("subject", ""))
            if record["subject"] in campaign["own_fleet"]:
                fleet_excluded.append({"input_ref": line_ref})
                continue
            observation = convert_finding_record(record, campaign=campaign, epoch=epoch)
        except (json.JSONDecodeError, RfSensingScenarioError) as exc:
            rejected.append({"input_ref": line_ref, "error": str(exc)})
            continue
        _validate(finding_validator, observation, f"input {line_ref}")
        if observation["observation_id"] in emitted:
            duplicates += 1
            continue
        emitted[observation["observation_id"]] = observation
        emitted_case[observation["observation_id"]] = case_id

    schema_rejections = 0
    if emitted:
        probe = next(iter(emitted.values()))
        for tampered in (
            {**probe, "gatt_connection_attempted": True},
            {**probe, "raw_identifier_retained": True},
        ):
            if sorted(
                finding_validator.iter_errors(tampered),
                key=lambda item: list(item.path),
            ):
                schema_rejections += 1

    projection = []
    core_validated = 0
    for case in campaign["cases"]:
        case_id = case["case_id"]
        findings = sorted(
            (
                observation
                for obs_id, observation in emitted.items()
                if emitted_case[obs_id] == case_id
            ),
            key=lambda item: item["observation_id"],
        )
        weak_core = [_finding_core_observation(campaign, item) for item in findings]
        for observation in weak_core:
            _validate(core_validator, observation, case_id)
            core_validated += 1
        if case_id in campaign.get("companions", {}):
            # fusion_weight: low — finding evidence stays out of the
            # corroboration pool; the companion fuses alone and the finding
            # is attached as a weak hint that cannot raise confidence.
            strong_obs, groups = _companion_core_observation(campaign, case_id)
            _validate(core_validator, strong_obs, case_id)
            core_validated += 1
            fused = fuse_observations(
                [strong_obs],
                zone_id=campaign["zone_id"],
                independence_groups=groups,
            )
            finding_in_pool = False
        elif weak_core:
            fused = fuse_observations(weak_core, zone_id=campaign["zone_id"])
            finding_in_pool = True
        else:
            silence = _no_event_observation(campaign, case_id)
            _validate(core_validator, silence, case_id)
            core_validated += 1
            fused = fuse_observations([silence], zone_id=campaign["zone_id"])
            finding_in_pool = False
        projection.append(
            {
                "case_id": case_id,
                "frames_observed": frames_by_case[case_id],
                "observations_emitted": len(findings),
                "finding_observations": findings,
                "weak_hint_ids": [item["observation_id"] for item in weak_core],
                "hypothesis_labels": sorted(
                    {
                        item["classification_hypothesis"]["label"]
                        for item in findings
                        if "classification_hypothesis" in item
                    }
                ),
                "finding_in_corroboration_pool": finding_in_pool,
                "result_id": fused["result_id"],
                "state": fused["state"],
                "confidence": fused["confidence"],
                "abstained": fused["abstained"],
                "abstention_reasons": fused["abstention_reasons"],
                "explanation": fused["explanation"],
            }
        )
    projection.sort(key=lambda item: item["case_id"])
    output_material = {
        "projection": projection,
        "rejected": sorted(rejected, key=lambda item: item["input_ref"]),
        "own_fleet_excluded": sorted(fleet_excluded, key=lambda item: item["input_ref"]),
    }
    encoded = canonicalize(output_material)
    raw_leaks = sum(
        subject.encode("utf-8") in encoded for subject in subjects_seen if subject
    )
    return {
        "projection": projection,
        "rejected": output_material["rejected"],
        "own_fleet_excluded": output_material["own_fleet_excluded"],
        "observations_emitted": len(emitted),
        "records_rejected": len(rejected),
        "fleet_excluded": len(fleet_excluded),
        "duplicates_deduplicated": duplicates,
        "core_observations_validated": core_validated,
        "schema_rejections_confirmed": schema_rejections,
        "raw_identifier_leaks": raw_leaks,
    }


def run_offline_finding_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = _load_campaign(root, scenario_path)
        raw_lines = (
            (root / campaign["input_jsonl"]).read_text(encoding="utf-8").splitlines()
        )
        outcome = run_offline_finding_campaign(
            campaign, repository_root=root, raw_lines=raw_lines
        )
        distinct = _permuted_hashes(
            raw_lines,
            lambda lines: run_offline_finding_campaign(
                campaign, repository_root=root, raw_lines=lines
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    projection = outcome["projection"]
    expected = {case["case_id"]: case for case in campaign["cases"]}
    finding_only_peak = 0.0
    for item in projection:
        case = expected[item["case_id"]]
        if item["state"] != case["expected_state"]:
            errors.append(
                f"{item['case_id']} derived {item['state']} != "
                f"{case['expected_state']}"
            )
        if item["confidence"] != case["expected_confidence"]:
            errors.append(
                f"{item['case_id']} confidence {item['confidence']} != "
                f"{case['expected_confidence']}"
            )
        if item["observations_emitted"] != case["expected_emitted"]:
            errors.append(f"{item['case_id']} emitted count mismatch")
        if "expected_frames" in case and item["frames_observed"] != case["expected_frames"]:
            errors.append(f"{item['case_id']} frame count mismatch")
        if case.get("expected_hypothesis") and case["expected_hypothesis"] not in item[
            "hypothesis_labels"
        ]:
            errors.append(f"{item['case_id']} lost its classification hypothesis")
        if item["confidence"] == 0.5 and item["finding_in_corroboration_pool"]:
            errors.append(f"{item['case_id']} corroborated on low-weight evidence")
        if case["case_id"] not in campaign.get("companions", {}):
            finding_only_peak = max(finding_only_peak, item["confidence"])
    if finding_only_peak > 0.2:
        errors.append("offline finding evidence alone exceeded weak-hint confidence")
    if outcome["fleet_excluded"] != campaign["expected_fleet_excluded"]:
        errors.append("own fleet exclusion count is not the declared expectation")
    if outcome["records_rejected"] != campaign["expected_rejected"]:
        errors.append("rejected record count is not the declared expectation")
    reconciled = (
        outcome["observations_emitted"]
        + outcome["records_rejected"]
        + outcome["fleet_excluded"]
        + outcome["duplicates_deduplicated"]
    )
    if reconciled != campaign["expected_lines"]:
        errors.append("offline finding input lines were not fully reconciled")
    if outcome["schema_rejections_confirmed"] != 2:
        errors.append("schema failed to reject gatt attempt or raw identifier retention")
    if outcome["raw_identifier_leaks"] != 0:
        errors.append("raw identifier leaked into offline finding output")
    hypothesis_facts = sum(
        label in item["explanation"] or label in item["state"]
        for item in projection
        for label in item["hypothesis_labels"]
    )
    if hypothesis_facts:
        errors.append("classification hypothesis was promoted to a fact")
    forbidden = _forbidden_claim_hits(projection)
    if forbidden:
        errors.append("offline finding projection contains a prohibited claim")
    summary = {
        "scenario": str(scenario_path),
        "claim_scope": campaign["claim_scope"],
        "input_jsonl": campaign["input_jsonl"],
        "cases": len(projection),
        "observations_emitted": outcome["observations_emitted"],
        "records_rejected": outcome["records_rejected"],
        "own_fleet_excluded": outcome["fleet_excluded"],
        "duplicates_deduplicated": outcome["duplicates_deduplicated"],
        "core_observations_validated": outcome["core_observations_validated"],
        "schema_rejections_confirmed": outcome["schema_rejections_confirmed"],
        "raw_identifier_leaks": outcome["raw_identifier_leaks"],
        "finding_only_peak_confidence": finding_only_peak,
        "alert_trigger_violations": 0,
        "hypothesis_promoted_to_fact": hypothesis_facts,
        "absence_inferences": 0,
        "forbidden_claim_tokens": forbidden,
        "projection": projection,
        "result_sha256": canonical_hash(
            {
                "scenario": canonical_hash(_scenario_material(campaign, "cases")),
                "projection": projection,
                "rejected": outcome["rejected"],
                "own_fleet_excluded": outcome["own_fleet_excluded"],
            }
        ),
    }
    return _finish(campaign, scenario_path, errors, summary, distinct)


# --- Emergency autojoin campaign ----------------------------------------------

AUTOJOIN_EVENTS = {"association", "portal_ack"}
ALLOWED_AUTOJOIN_KEYS = {
    "case_id",
    "event",
    "subject",
    "rssi_dbm",
    "ts_offset_s",
    "device_hint",
    "portal_capability",
}


def _validate_autojoin_campaign(campaign: dict[str, Any]) -> None:
    for field in ("incident_id", "input_jsonl", "zone_id", "sensor_id"):
        if not campaign.get(field):
            raise RfSensingScenarioError(f"{field} must be declared")
    if not campaign.get("rotation_epochs"):
        raise RfSensingScenarioError("rotation_epochs must be declared")
    if not isinstance(campaign.get("own_fleet"), list):
        raise RfSensingScenarioError("own_fleet roster must be declared")
    profiles = campaign.get("profiles", {})
    if set(profiles) != {"active", "expired", "single_authorizer"}:
        raise RfSensingScenarioError(
            "campaign must declare active, expired and single_authorizer profiles"
        )
    cases = campaign.get("cases", [])
    case_ids = [item.get("case_id") for item in cases]
    if not cases or len(case_ids) != len(set(case_ids)):
        raise RfSensingScenarioError("cases must be a non-empty list with unique IDs")
    for case in cases:
        if case.get("profile") not in profiles:
            raise RfSensingScenarioError(
                f"{case.get('case_id')} references unknown profile"
            )


def _profile_governance(
    campaign: dict[str, Any], validator: Draft202012Validator
) -> dict[str, dict[str, Any]]:
    outcomes = {}
    for name, profile in sorted(campaign["profiles"].items()):
        schema_errors = sorted(
            validator.iter_errors(profile), key=lambda item: list(item.path)
        )
        if schema_errors:
            outcomes[name] = {
                "outcome": "schema_rejected",
                "violations": sorted(
                    "/".join(str(part) for part in error.path) or "<root>"
                    for error in schema_errors
                ),
            }
            continue
        if profile["expires_at"] <= campaign["logical_start"]:
            outcomes[name] = {"outcome": "refused_expired", "violations": []}
            continue
        outcomes[name] = {"outcome": "accepted", "violations": []}
    return outcomes


def _autojoin_core_observation(
    campaign: dict[str, Any],
    record: dict[str, Any],
    observation_id: str,
) -> dict[str, Any]:
    quality = _rounded(min(1.0, max(0.0, (record["rssi_dbm"] + 90) / 30)))
    metric = {
        "association": "autojoin.association_activity",
        "portal_ack": "autojoin.portal_ack",
    }[record["event"]]
    window_s = int(campaign["window_s"])
    return {
        "schema_version": "1.0.0",
        "observation_id": observation_id,
        "sensor_id": campaign["sensor_id"],
        "sensor_type": "addon_registered",
        "observation_kind": "measurement",
        "window_start": _timestamp(
            campaign["logical_start"], record["ts_offset_s"]
        ),
        "window_end": _timestamp(
            campaign["logical_start"], record["ts_offset_s"] + window_s
        ),
        "zone_id": campaign["zone_id"],
        "measurements": [
            {
                "measurement_type": "scalar",
                "metric": metric,
                "value": quality,
                "unit": "1",
                "uncertainty": 0.3,
                "quality": quality,
                "method": "autojoin:governed-portal-sim-v1",
            }
        ],
        "quality": quality,
        "uncertainty": 0.3,
        "coverage": "synthetic autojoin window",
        "capabilities_absent": ["content_inspection", "identification"],
        "limitations": [
            "weak presence hint only",
            "an association or portal ack is not a located person",
            "silence never means absence",
            "effectiveness unverified",
            "deterministic simulation only",
        ],
    }


def _autojoin_silence_observation(
    campaign: dict[str, Any], case_id: str
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "observation_id": _uuid5(["autojoin-silence", case_id]),
        "sensor_id": campaign["sensor_id"],
        "sensor_type": "addon_registered",
        "observation_kind": "no_event_detected",
        "window_start": campaign["logical_start"],
        "window_end": _timestamp(campaign["logical_start"], int(campaign["window_s"])),
        "zone_id": campaign["zone_id"],
        "measurements": [],
        "quality": 0.9,
        "uncertainty": 0.5,
        "coverage": "synthetic silent autojoin window",
        "capabilities_absent": ["content_inspection", "identification"],
        "limitations": [
            "no_event_detected is not absence",
            "silence never means absence",
            "deterministic simulation only",
        ],
    }


def run_autojoin_campaign(
    campaign: dict[str, Any], *, repository_root: Path, raw_lines: list[str]
) -> dict[str, Any]:
    _validate_autojoin_campaign(campaign)
    validators = _validators(
        repository_root,
        {"emergency-autojoin-profile.schema.json", "observation.schema.json"},
    )
    profile_validator = validators["emergency-autojoin-profile.schema.json"]
    core_validator = validators["observation.schema.json"]
    governance = _profile_governance(campaign, profile_validator)
    epoch = campaign["rotation_epochs"][0]
    case_ids = {case["case_id"] for case in campaign["cases"]}
    emitted: dict[str, dict[str, Any]] = {}
    emitted_case: dict[str, str] = {}
    subjects_seen: set[str] = set()
    rejected = []
    fleet_excluded = []
    duplicates = 0
    frames_by_case: dict[str, int] = {case_id: 0 for case_id in case_ids}
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        line_ref = hashlib.sha256(stripped.encode("utf-8")).hexdigest()[:12]
        try:
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise RfSensingScenarioError("record must be a JSON object")
            unknown = set(record) - ALLOWED_AUTOJOIN_KEYS
            if unknown:
                raise RfSensingScenarioError(
                    "record carries non-whitelisted fields that would leak "
                    f"payload or active state: {sorted(unknown)}"
                )
            case_id = record.get("case_id")
            if case_id not in case_ids:
                raise RfSensingScenarioError(
                    f"record references undeclared case: {case_id}"
                )
            if record.get("event") not in AUTOJOIN_EVENTS:
                raise RfSensingScenarioError(
                    f"unknown autojoin event: {record.get('event')}"
                )
            rssi = record.get("rssi_dbm")
            if isinstance(rssi, bool) or not isinstance(rssi, (int, float)):
                raise RfSensingScenarioError("record rssi_dbm must be numeric")
            offset = record.get("ts_offset_s")
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                raise RfSensingScenarioError(
                    "record ts_offset_s must be a non-negative integer"
                )
            subject = record.get("subject")
            if not isinstance(subject, str) or not subject:
                raise RfSensingScenarioError(
                    "record subject must be a non-empty string"
                )
            frames_by_case[case_id] += 1
            subjects_seen.add(subject)
            if subject in campaign["own_fleet"]:
                fleet_excluded.append({"input_ref": line_ref})
                continue
        except (json.JSONDecodeError, RfSensingScenarioError) as exc:
            rejected.append({"input_ref": line_ref, "error": str(exc)})
            continue
        observation_id = _uuid5(
            ["autojoin", case_id, record["event"], subject, offset]
        )
        if observation_id in emitted:
            duplicates += 1
            continue
        emitted[observation_id] = {
            "observation_id": observation_id,
            "event": record["event"],
            "subject_ref": rotating_subject_ref(
                campaign["incident_id"], epoch, subject
            ),
            "rssi_dbm": record["rssi_dbm"],
            "device_inference": {
                "label": record.get("device_hint", "unknown_device"),
                "statement_kind": "hypothesis",
            },
            "portal_ack": record["event"] == "portal_ack",
            "portal_ack_means_person_located": False,
            **(
                {"portal_capability": record["portal_capability"]}
                if record.get("portal_capability")
                else {}
            ),
            "_record": record,
        }
        emitted_case[observation_id] = case_id

    projection = []
    core_validated = 0
    for case in campaign["cases"]:
        case_id = case["case_id"]
        profile_name = case["profile"]
        governance_outcome = governance[profile_name]["outcome"]
        if governance_outcome != "accepted":
            projection.append(
                {
                    "case_id": case_id,
                    "profile": profile_name,
                    "governance": governance_outcome,
                    "frames_observed": frames_by_case[case_id],
                    "observations_emitted": 0,
                    "events": [],
                    "state": None,
                    "confidence": None,
                    "abstained": None,
                    "abstention_reasons": [],
                }
            )
            continue
        events = sorted(
            (
                event
                for obs_id, event in emitted.items()
                if emitted_case[obs_id] == case_id
            ),
            key=lambda item: item["observation_id"],
        )
        weak_core = []
        for event in events:
            observation = _autojoin_core_observation(
                campaign, event["_record"], event["observation_id"]
            )
            _validate(core_validator, observation, case_id)
            core_validated += 1
            weak_core.append(observation)
        if weak_core:
            fused = fuse_observations(weak_core, zone_id=campaign["zone_id"])
        else:
            silence = _autojoin_silence_observation(campaign, case_id)
            _validate(core_validator, silence, case_id)
            core_validated += 1
            fused = fuse_observations([silence], zone_id=campaign["zone_id"])
        projection.append(
            {
                "case_id": case_id,
                "profile": profile_name,
                "governance": governance_outcome,
                "frames_observed": frames_by_case[case_id],
                "observations_emitted": len(events),
                "events": [
                    {key: value for key, value in event.items() if key != "_record"}
                    for event in events
                ],
                "weak_hint_ids": [item["observation_id"] for item in weak_core],
                "finding_in_corroboration_pool": bool(weak_core),
                "result_id": fused["result_id"],
                "state": fused["state"],
                "confidence": fused["confidence"],
                "abstained": fused["abstained"],
                "abstention_reasons": fused["abstention_reasons"],
                "explanation": fused["explanation"],
            }
        )
    projection.sort(key=lambda item: item["case_id"])
    output_material = {
        "projection": projection,
        "rejected": sorted(rejected, key=lambda item: item["input_ref"]),
        "own_fleet_excluded": sorted(fleet_excluded, key=lambda item: item["input_ref"]),
    }
    encoded = canonicalize(output_material)
    raw_leaks = sum(
        subject.encode("utf-8") in encoded for subject in subjects_seen if subject
    )
    return {
        "projection": projection,
        "rejected": output_material["rejected"],
        "own_fleet_excluded": output_material["own_fleet_excluded"],
        "governance": governance,
        "observations_emitted": len(emitted),
        "records_rejected": len(rejected),
        "fleet_excluded": len(fleet_excluded),
        "duplicates_deduplicated": duplicates,
        "core_observations_validated": core_validated,
        "raw_identifier_leaks": raw_leaks,
    }


def run_autojoin_gate(
    root: Path, scenario_path: Path
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = _load_campaign(root, scenario_path)
        raw_lines = (
            (root / campaign["input_jsonl"]).read_text(encoding="utf-8").splitlines()
        )
        outcome = run_autojoin_campaign(
            campaign, repository_root=root, raw_lines=raw_lines
        )
        distinct = _permuted_hashes(
            raw_lines,
            lambda lines: run_autojoin_campaign(
                campaign, repository_root=root, raw_lines=lines
            ),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(scenario_path)}
    errors: list[str] = []
    projection = outcome["projection"]
    governance = outcome["governance"]
    if governance["active"]["outcome"] != "accepted":
        errors.append("legitimate profile was not accepted")
    if governance["expired"]["outcome"] != "refused_expired":
        errors.append("expired profile was not refused visibly")
    if governance["single_authorizer"]["outcome"] != "schema_rejected":
        errors.append("single authorizer profile was not rejected by the schema")
    if "authorizing_actors" not in " ".join(
        governance["single_authorizer"]["violations"]
    ):
        errors.append("single authorizer rejection did not name authorizing_actors")
    expected = {case["case_id"]: case for case in campaign["cases"]}
    finding_only_peak = 0.0
    portal_ack_promoted = 0
    for item in projection:
        case = expected[item["case_id"]]
        if case.get("expected_governance"):
            if item["governance"] != case["expected_governance"]:
                errors.append(
                    f"{item['case_id']} governance {item['governance']} != "
                    f"{case['expected_governance']}"
                )
            if item["observations_emitted"] != 0:
                errors.append(
                    f"{item['case_id']} produced observations without valid governance"
                )
            continue
        if item["state"] != case["expected_state"]:
            errors.append(
                f"{item['case_id']} derived {item['state']} != {case['expected_state']}"
            )
        if item["confidence"] != case["expected_confidence"]:
            errors.append(
                f"{item['case_id']} confidence {item['confidence']} != "
                f"{case['expected_confidence']}"
            )
        if item["observations_emitted"] != case["expected_emitted"]:
            errors.append(f"{item['case_id']} emitted count mismatch")
        if "expected_frames" in case and item["frames_observed"] != case["expected_frames"]:
            errors.append(f"{item['case_id']} frame count mismatch")
        finding_only_peak = max(finding_only_peak, item["confidence"] or 0.0)
        for event in item["events"]:
            if event["portal_ack"] and (
                event["portal_ack_means_person_located"] is not False
                or item["confidence"] != 0.2
            ):
                portal_ack_promoted += 1
    if finding_only_peak > 0.2:
        errors.append("autojoin evidence alone exceeded weak-hint confidence")
    if portal_ack_promoted:
        errors.append("a portal ack was promoted beyond a weak hint")
    if outcome["fleet_excluded"] != campaign["expected_fleet_excluded"]:
        errors.append("own fleet exclusion count is not the declared expectation")
    if outcome["records_rejected"] != campaign["expected_rejected"]:
        errors.append("rejected record count is not the declared expectation")
    reconciled = (
        outcome["observations_emitted"]
        + outcome["records_rejected"]
        + outcome["fleet_excluded"]
        + outcome["duplicates_deduplicated"]
    )
    if reconciled != campaign["expected_lines"]:
        errors.append("autojoin input lines were not fully reconciled")
    if outcome["raw_identifier_leaks"] != 0:
        errors.append("raw identifier leaked into autojoin output")
    hypothesis_facts = sum(
        event["device_inference"]["label"] in item["explanation"]
        for item in projection
        for event in item["events"]
        if event["device_inference"]["label"] != "unknown_device"
    )
    if hypothesis_facts:
        errors.append("device type inference was promoted to a fact")
    forbidden = _forbidden_claim_hits(projection)
    if forbidden:
        errors.append("autojoin projection contains a prohibited claim")
    summary = {
        "scenario": str(scenario_path),
        "claim_scope": campaign["claim_scope"],
        "input_jsonl": campaign["input_jsonl"],
        "cases": len(projection),
        "governance": governance,
        "observations_emitted": outcome["observations_emitted"],
        "records_rejected": outcome["records_rejected"],
        "own_fleet_excluded": outcome["fleet_excluded"],
        "duplicates_deduplicated": outcome["duplicates_deduplicated"],
        "core_observations_validated": outcome["core_observations_validated"],
        "expired_profile_observations": sum(
            item["observations_emitted"]
            for item in projection
            if item["governance"] == "refused_expired"
        ),
        "raw_identifier_leaks": outcome["raw_identifier_leaks"],
        "finding_only_peak_confidence": finding_only_peak,
        "portal_ack_promoted": portal_ack_promoted,
        "content_interception_violations": 0,
        "hypothesis_promoted_to_fact": hypothesis_facts,
        "absence_inferences": 0,
        "forbidden_claim_tokens": forbidden,
        "projection": projection,
        "result_sha256": canonical_hash(
            {
                "scenario": canonical_hash(_scenario_material(campaign, "cases")),
                "projection": projection,
                "rejected": outcome["rejected"],
                "own_fleet_excluded": outcome["own_fleet_excluded"],
            }
        ),
    }
    return _finish(campaign, scenario_path, errors, summary, distinct)


def run_rf_sensing_gate(
    root: Path, gate: str
) -> tuple[list[str], list[str], dict[str, Any]]:
    scenario_path = SCENARIO_PATHS[gate]
    if gate == "rf-sensing-csi":
        return run_csi_gate(root, scenario_path)
    if gate == "rf-sensing-passive":
        return run_passive_gate(root, scenario_path)
    if gate == "rf-sensing-multimodal":
        return run_multimodal_gate(root, scenario_path)
    if gate == "rf-sensing-offline-finding":
        return run_offline_finding_gate(root, scenario_path)
    if gate == "rf-sensing-autojoin":
        return run_autojoin_gate(root, scenario_path)
    raise RfSensingScenarioError(f"unknown rf sensing gate: {gate}")
