from __future__ import annotations

import uuid
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import load_core_schemas, schema_registry
from openbrec.semantic import parse_timestamp


ENGINE_NAME = "openbrec-fusion"
ENGINE_VERSION = "1.0.0"
FUSION_OUTPUTS = {
    "single_modality_candidate",
    "corroborated_candidate",
    "sensor_artifact_likely",
    "insufficient_coverage",
    "unknown",
}
CANDIDATE_LIMITATIONS = ("candidate only", "never confirms presence or absence")

MIN_EVIDENCE_QUALITY = 0.5
SINGLE_SOURCE_CONFIDENCE = 0.2
CORROBORATED_CONFIDENCE = 0.5
RESULT_TTL_S = 300
EVIDENCE_LOOKBACK_S = 300


class FusionError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def classify_fusion_case(
    case: dict[str, Any], observations: dict[str, dict[str, Any]]
) -> str:
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


def engine_configuration() -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "rules": "deterministic",
        "min_evidence_quality": MIN_EVIDENCE_QUALITY,
        "single_source_confidence": SINGLE_SOURCE_CONFIDENCE,
        "corroborated_confidence": CORROBORATED_CONFIDENCE,
        "result_ttl_s": RESULT_TTL_S,
        "corroboration": "distinct_sensors>=2 and distinct_sensor_types>=2",
    }


@lru_cache(maxsize=1)
def _fusion_result_validator() -> Draft202012Validator:
    root = Path(__file__).resolve().parents[1]
    schemas = load_core_schemas(root)
    schema = next(
        value for value, path in schemas if path.name == "fusion-result.schema.json"
    )
    return Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )


def validate_fusion_result(payload: Any) -> dict[str, Any]:
    errors = sorted(
        _fusion_result_validator().iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        messages = [
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        ]
        raise FusionError(messages)
    if not isinstance(payload, dict):
        raise FusionError(["/: fusion result must be an object"])
    return payload


def _result_id(
    evidence_ids: list[str],
    *,
    zone_id: str | None,
    window_start: str,
    window_end: str,
) -> str:
    recipe = {
        "configuration": engine_configuration(),
        "supporting_evidence_ids": evidence_ids,
        "window_start": window_start,
        "window_end": window_end,
        "zone_id": zone_id,
    }
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "https://openbrec.org/fusion-result/" + canonical_hash(recipe),
        )
    )


def fuse_observations(
    observations: list[dict[str, Any]], *, zone_id: str | None = None
) -> dict[str, Any]:
    ordered = sorted(observations, key=lambda item: item["observation_id"])
    if not ordered:
        raise FusionError(["at least one observation is required"])
    usable = [
        item
        for item in ordered
        if item["observation_kind"] == "measurement"
        and item["quality"] >= MIN_EVIDENCE_QUALITY
    ]
    window_start = min(item["window_start"] for item in ordered)
    window_end = max(item["window_end"] for item in ordered)
    valid_until = (
        parse_timestamp(window_end) + timedelta(seconds=RESULT_TTL_S)
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    evidence_ids = [item["observation_id"] for item in usable]

    if not usable:
        state = "abstained"
        abstained = True
        abstention_reasons = ["insufficient independent evidence"]
        confidence = 0.0
        coverage = "insufficient"
        explanation = (
            "no usable evidence in window; abstaining instead of "
            "inferring presence or absence"
        )
        limitations = [
            "no consolidated claim",
            "silence does not imply absence",
            "deterministic rules without ML",
        ]
        capabilities_absent = sorted(
            {
                capability
                for item in ordered
                for capability in item["capabilities_absent"]
            }
        )
    else:
        sensors = {item["sensor_id"] for item in usable}
        groups = {item["sensor_type"] for item in usable}
        corroborated = len(sensors) >= 2 and len(groups) >= 2
        state = "indicator"
        abstained = False
        abstention_reasons = []
        confidence = (
            CORROBORATED_CONFIDENCE if corroborated else SINGLE_SOURCE_CONFIDENCE
        )
        coverage = "sufficient" if corroborated else "single-source"
        explanation = (
            "corroborated candidate across independent sources"
            if corroborated
            else "single-source candidate"
        )
        limitations = [
            *CANDIDATE_LIMITATIONS,
            "silence does not imply absence",
            "deterministic rules without ML",
        ]
        capabilities_absent = sorted(
            {
                capability
                for item in usable
                for capability in item["capabilities_absent"]
            }
        )

    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "result_id": _result_id(
            evidence_ids,
            zone_id=zone_id,
            window_start=window_start,
            window_end=window_end,
        ),
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "configuration_sha256": canonical_hash(engine_configuration()),
        "state": state,
        "supporting_evidence_ids": evidence_ids,
        "contradicting_evidence_ids": [],
        "window_start": window_start,
        "window_end": window_end,
        "coverage": coverage,
        "confidence": confidence,
        "conflict_score": 0.0,
        "abstained": abstained,
        "abstention_reasons": abstention_reasons,
        "capabilities_absent": capabilities_absent,
        "valid_until": valid_until,
        "limitations": limitations,
        "explanation": explanation,
    }
    if zone_id is not None:
        result["zone_id"] = zone_id
    return validate_fusion_result(result)
