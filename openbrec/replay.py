from __future__ import annotations

import copy
import hashlib
import uuid
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from openbrec.canonical import canonical_hash
from openbrec.semantic import SemanticValidationError, event_uuid, parse_timestamp
from openbrec.semantic import validate_event, validate_event_set


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ENGINE_NAME = "openbrec-core-replay"
ENGINE_VERSION = "1.0.0"


@dataclass(frozen=True)
class ReplayOutcome:
    events: list[dict[str, Any]]
    receipt: dict[str, Any]


def _receipt_uuid(prefix: str, material_hash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://openbrec.org/{prefix}/{material_hash}"))


def _format_timestamp(value) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _artifact_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdapterReplayRunner:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def run(self, bundle: dict[str, Any]) -> ReplayOutcome:
        observations = bundle.get("observations", [])
        actual_input_hash = canonical_hash(observations)
        errors: list[str] = []
        events: list[dict[str, Any]] = []
        if actual_input_hash != bundle.get("input_sha256"):
            errors.append("input hash mismatch")
        adapter = bundle["adapter"]
        configuration = bundle["configuration"]
        if configuration.get("source_namespace") != (
            f"urn:openbrec:adapter:{adapter['name']}"
        ):
            errors.append("adapter source namespace mismatch")

        if not errors:
            for sequence, observation in enumerate(observations):
                source_event_id = f"fixture:observation:{sequence}"
                recipe = {
                    "source_namespace": configuration["source_namespace"],
                    "source_event_id": source_event_id,
                    "boot_id": configuration["boot_id"],
                    "sequence": sequence,
                    "schema_ref": "https://openbrec.org/schemas/core/observation/1.0.0",
                }
                idempotency_id = "urn:sha256:" + canonical_hash(recipe)
                event = {
                    "schema_version": "1.0.0",
                    "schema_ref": "https://openbrec.org/schemas/core/observation/1.0.0",
                    "event_type": "observation",
                    "event_id": event_uuid(idempotency_id),
                    "idempotency_id": idempotency_id,
                    "correlation_id": configuration["correlation_id"],
                    "causation_event_ids": [],
                    "incident_id": configuration["incident_id"],
                    "deployment_id": configuration["deployment_id"],
                    "source_node_id": configuration["source_node_id"],
                    "origin": "adapter",
                    "source_event_id": source_event_id,
                    "boot_id": configuration["boot_id"],
                    "session_id": configuration["session_id"],
                    "sequence": sequence,
                    "captured_at": observation["window_start"],
                    "received_at": configuration["received_at"],
                    "clock_uncertainty_ms": 0,
                    "clock_source": "logical",
                    "provenance": {
                        "schema_version": "1.0.0",
                        "artifact_type": "adapter",
                        "name": adapter["name"],
                        "version": adapter["version"],
                        "artifact_sha256": adapter["artifact_sha256"],
                        "recorded_at": observation["window_start"],
                        "configuration_sha256": configuration[
                            "configuration_sha256"
                        ],
                        "capabilities_present": ["synthetic.observation"],
                        "capabilities_absent": observation["capabilities_absent"],
                        "limitations": ["synthetic replay only"],
                    },
                    "handling_policy": copy.deepcopy(bundle["handling_policy"]),
                    "retention_policy_id": "urn:openbrec:retention:lab:1.0.0",
                    "privacy_flags": {
                        "contains_direct_identifier": False,
                        "contains_raw_payload": False,
                        "life_safety_relevant": False,
                    },
                    "payload": copy.deepcopy(observation),
                }
                try:
                    validate_event(event, self.repository_root)
                except SemanticValidationError as exc:
                    errors.extend(exc.errors)
                    events = []
                    break
                events.append(event)

        normalized_hash = canonical_hash(events) if events else EMPTY_SHA256
        receipt_material_hash = canonical_hash(
            {
                "input_sha256": actual_input_hash,
                "normalized_events_sha256": normalized_hash,
                "errors": sorted(errors),
            }
        )
        receipt = {
            "schema_version": "1.0.0",
            "receipt_id": _receipt_uuid("adapter-replay", receipt_material_hash),
            "generated_at": bundle["logical_time"],
            "result": "failed" if errors else "passed",
            "input_sha256": actual_input_hash,
            "adapter_name": adapter["name"],
            "adapter_version": adapter["version"],
            "adapter_artifact_sha256": adapter["artifact_sha256"],
            "configuration_sha256": configuration["configuration_sha256"],
            "contract_set_sha256": bundle["contract_set_sha256"],
            "normalized_events_sha256": normalized_hash,
            "events_produced": len(events),
            "errors": sorted(errors),
            "handling_policy_ref": bundle["handling_policy"]["policy_id"],
        }
        return ReplayOutcome(events, receipt)


def _derived_event(
    *,
    cause: dict[str, Any],
    event_type: str,
    schema_ref: str,
    derivation_key: str,
    payload: dict[str, Any],
    sequence: int,
    configuration_sha256: str,
    artifact_sha256: str,
) -> dict[str, Any]:
    causes = sorted([cause["event_id"]])
    recipe = {
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "configuration_sha256": configuration_sha256,
        "event_type": event_type,
        "causation_event_ids": causes,
        "derivation_key": derivation_key,
    }
    idempotency_id = "urn:sha256:" + canonical_hash(recipe)
    derived_id = event_uuid(idempotency_id)
    payload = copy.deepcopy(payload)
    if event_type == "evidence":
        payload["evidence_id"] = derived_id
    elif event_type == "fusion_result":
        payload["result_id"] = derived_id
    event = {
        "schema_version": "1.0.0",
        "schema_ref": schema_ref,
        "event_type": event_type,
        "event_id": derived_id,
        "idempotency_id": idempotency_id,
        "correlation_id": cause["correlation_id"],
        "causation_event_ids": causes,
        "derivation_key": derivation_key,
        "incident_id": cause["incident_id"],
        "deployment_id": cause["deployment_id"],
        "origin": "core",
        "boot_id": cause["boot_id"],
        "session_id": cause["session_id"],
        "sequence": sequence,
        "captured_at": payload["window_end"],
        "received_at": cause["received_at"],
        "clock_uncertainty_ms": cause["clock_uncertainty_ms"],
        "clock_source": "logical",
        "provenance": {
            "schema_version": "1.0.0",
            "artifact_type": "engine",
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "artifact_sha256": artifact_sha256,
            "recorded_at": payload["window_end"],
            "configuration_sha256": configuration_sha256,
            "capabilities_present": ["deterministic.rules"],
            "capabilities_absent": payload.get("capabilities_absent", []),
            "limitations": ["M0 deterministic rules only"],
        },
        "handling_policy": copy.deepcopy(cause["handling_policy"]),
        "retention_policy_id": cause["retention_policy_id"],
        "privacy_flags": copy.deepcopy(cause["privacy_flags"]),
        "payload": payload,
    }
    if "zone_id" in cause:
        event["zone_id"] = cause["zone_id"]
    return event


class CoreReplayRunner:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root
        self.configuration = {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "confidence_scale": "0.001",
            "rule": "single-source-abstains",
        }
        self.configuration_sha256 = canonical_hash(self.configuration)
        self.artifact_sha256 = _artifact_sha256(Path(__file__))

    def run(
        self,
        events: list[dict[str, Any]],
        *,
        upstream_receipt_sha256: str,
    ) -> ReplayOutcome:
        errors: list[str] = []
        outputs: list[dict[str, Any]] = []
        try:
            inputs = validate_event_set(events, self.repository_root)
        except SemanticValidationError as exc:
            inputs = []
            errors.extend(exc.errors)

        if not errors:
            for observation_event in (
                item for item in inputs if item["event_type"] == "observation"
            ):
                observation = observation_event["payload"]
                confidence = (
                    Decimal(str(observation["quality"]))
                    * (Decimal("1") - Decimal(str(observation["uncertainty"])))
                ).quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
                valid_until = _format_timestamp(
                    parse_timestamp(observation["window_end"]) + timedelta(minutes=5)
                )
                evidence_payload = {
                    "schema_version": "1.0.0",
                    "evidence_id": "00000000-0000-4000-8000-000000000000",
                    "engine_name": "openbrec-rules",
                    "engine_version": ENGINE_VERSION,
                    "hypothesis": "possible_signal_of_interest",
                    "unsupported_claims": ["person_absent", "person_present"],
                    "source_observation_ids": [observation["observation_id"]],
                    "window_start": observation["window_start"],
                    "window_end": observation["window_end"],
                    "coverage": observation["coverage"],
                    "confidence": float(confidence),
                    "uncertainty": float(Decimal("1") - confidence),
                    "valid_until": valid_until,
                    "limitations": sorted(
                        set(observation["limitations"] + ["single source"])
                    ),
                    "explanation": "deterministic rule produced an indicator, not a person claim",
                }
                if "zone_id" in observation_event:
                    evidence_payload["zone_id"] = observation_event["zone_id"]
                evidence = _derived_event(
                    cause=observation_event,
                    event_type="evidence",
                    schema_ref="https://openbrec.org/schemas/core/evidence/1.0.0",
                    derivation_key=f"observation:{observation['observation_id']}/evidence:0",
                    payload=evidence_payload,
                    sequence=observation_event["sequence"] + 1,
                    configuration_sha256=self.configuration_sha256,
                    artifact_sha256=self.artifact_sha256,
                )
                validate_event(evidence, self.repository_root)
                outputs.append(evidence)

                fusion_payload = {
                    "schema_version": "1.0.0",
                    "result_id": "00000000-0000-4000-8000-000000000000",
                    "engine_name": "openbrec-fusion",
                    "engine_version": ENGINE_VERSION,
                    "configuration_sha256": self.configuration_sha256,
                    "state": "abstained",
                    "supporting_evidence_ids": [evidence["payload"]["evidence_id"]],
                    "contradicting_evidence_ids": [],
                    "window_start": observation["window_start"],
                    "window_end": observation["window_end"],
                    "coverage": observation["coverage"],
                    "confidence": 0.0,
                    "conflict_score": 0.0,
                    "abstained": True,
                    "abstention_reasons": ["insufficient independent evidence"],
                    "capabilities_absent": sorted(observation["capabilities_absent"]),
                    "valid_until": valid_until,
                    "limitations": sorted(
                        set(observation["limitations"] + ["single source"])
                    ),
                    "explanation": "no consolidated presence or absence claim",
                }
                if "zone_id" in observation_event:
                    fusion_payload["zone_id"] = observation_event["zone_id"]
                fusion = _derived_event(
                    cause=evidence,
                    event_type="fusion_result",
                    schema_ref="https://openbrec.org/schemas/core/fusion-result/1.0.0",
                    derivation_key=f"observation:{observation['observation_id']}/fusion:0",
                    payload=fusion_payload,
                    sequence=evidence["sequence"] + 1,
                    configuration_sha256=self.configuration_sha256,
                    artifact_sha256=self.artifact_sha256,
                )
                validate_event(fusion, self.repository_root)
                outputs.append(fusion)

        outputs = sorted(
            outputs,
            key=lambda event: (event["captured_at"], event["event_type"], event["event_id"]),
        )
        input_hash = canonical_hash(inputs) if inputs else EMPTY_SHA256
        outputs_hash = canonical_hash(outputs) if outputs else EMPTY_SHA256
        contract_set_sha256 = _contract_set_sha256(self.repository_root)
        material = {
            "replay_material_schema_ref": "https://openbrec.org/schemas/core/core-replay-material/1.0.0",
            "contract_set_sha256": contract_set_sha256,
            "upstream_receipt_sha256": upstream_receipt_sha256,
            "engine": {
                "name": ENGINE_NAME,
                "version": ENGINE_VERSION,
                "artifact_sha256": self.artifact_sha256,
                "configuration_sha256": self.configuration_sha256,
            },
            "input_events": inputs,
            "outputs": outputs,
        }
        result_hash = canonical_hash(material)
        generated_at = (
            max((event["received_at"] for event in inputs), default="2026-07-17T00:00:00.000000Z")
        )
        receipt = {
            "schema_version": "1.0.0",
            "receipt_id": _receipt_uuid("core-replay", result_hash),
            "generated_at": generated_at,
            "result": "failed" if errors else "passed",
            "contract_set_sha256": contract_set_sha256,
            "upstream_receipt_sha256": upstream_receipt_sha256,
            "engine_name": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "engine_artifact_sha256": self.artifact_sha256,
            "configuration_sha256": self.configuration_sha256,
            "input_events_sha256": input_hash,
            "outputs_sha256": outputs_hash,
            "result_sha256": result_hash,
            "errors": sorted(errors),
        }
        return ReplayOutcome([] if errors else outputs, receipt)


def _contract_set_sha256(repository_root: Path) -> str:
    import json

    catalog = json.loads(
        (repository_root / "schemas/core/catalog.json").read_text(encoding="utf-8")
    )
    return str(catalog["contract_set_sha256"])


__all__ = [
    "AdapterReplayRunner",
    "CoreReplayRunner",
    "ReplayOutcome",
    "event_uuid",
]
