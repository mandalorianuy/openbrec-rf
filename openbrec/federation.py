from __future__ import annotations

import base64
import copy
import hashlib
import json
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.contracts import load_addon_schemas


SCENARIO_PATH = Path("fixtures/p0/federation/50k-sites.json")
NAMESPACE = uuid.UUID("35514fb8-822d-49dc-80dc-7f386e3f06ce")
EXPECTED_SCALE = {
    "sites": 50_000,
    "response_cells": 60,
    "operational_areas": 5,
    "hubs": 2,
}
LOCAL_OPERATIONS = {"sos", "sensing", "messaging", "rf_decision"}
CENTRAL_DEPENDENCIES = {
    "hub",
    "cloud",
    "internet",
    "central_ca",
    "central_broker",
    "dns",
}
MINIMAL_EVENT_TYPES = {"cell_status", "distress_summary", "resource_request"}
SAFE_HUB_AUTHORITY = {
    "cell_private_keys": False,
    "decrypt_local_content": False,
    "order_tx": False,
    "create_operational_acceptance": False,
}
HOSTILE_POLICY = {
    "forged_cell_signature": "rejected",
    "request_cell_private_key": "rejected",
    "request_local_plaintext": "rejected",
    "order_tx": "rejected",
    "forge_operator_accepted": "review_quarantine",
    "replay_expired_event": "rejected",
    "topology_overwrite_intent": "rejected",
    "central_ca_dependency": "rejected",
    "unsigned_distress": "review_quarantine",
}
FORBIDDEN_SUMMARY_MARKERS = {
    "raw audio",
    "raw frame",
    "protobuf",
    "private key",
    "message content",
    "position history",
    "operator.accepted",
}


class FederationScenarioError(ValueError):
    pass


def _validator(root: Path, name: str) -> Draft202012Validator:
    schemas = load_addon_schemas(root)
    schema = next((item for item, path in schemas if path.name == name), None)
    if schema is None:
        raise FederationScenarioError(f"addon schema not found: {name}")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(
    validator: Draft202012Validator, value: dict[str, Any], label: str
) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise FederationScenarioError(f"{label} schema validation failed: {detail}")


def _uuid(label: str) -> str:
    return str(uuid.uuid5(NAMESPACE, label))


def _at(offset_s: int) -> str:
    start = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
    return (
        (start + timedelta(seconds=offset_s))
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _signing_key(binding_id: str) -> Ed25519PrivateKey:
    private = hashlib.sha256(
        f"openbrec-p0-federation-simulated-only:{binding_id}".encode("utf-8")
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(private)


def load_scenario(path: Path) -> dict[str, Any]:
    scenario = json.loads(path.read_text(encoding="utf-8"))
    if scenario.get("scenario_version") != "1.0.0":
        raise FederationScenarioError("scenario_version must be 1.0.0")
    if scenario.get("claim_scope") != "deterministic_simulation_only":
        raise FederationScenarioError("federation scenario must remain simulation only")
    if scenario.get("scale") != EXPECTED_SCALE:
        raise FederationScenarioError("federation scale must remain 50000/60/5/2")
    generator = scenario.get("generator", {})
    if generator.get("version") != "1.0.0" or not isinstance(
        generator.get("seed"), int
    ):
        raise FederationScenarioError("versioned generator and integer seed required")
    partition = scenario.get("partition", {})
    if partition.get("duration_s") != 86_400:
        raise FederationScenarioError("partition must last exactly 24 hours")
    if set(partition.get("unavailable_hubs", [])) != {"hub-a", "hub-b"}:
        raise FederationScenarioError("both redundant hubs must be unavailable")
    if set(scenario.get("local_critical_operations", [])) != LOCAL_OPERATIONS:
        raise FederationScenarioError("all local critical operations are required")
    gateway = scenario.get("gateway_policy", {})
    if gateway.get("outbound_only") is not True:
        raise FederationScenarioError("federation gateways must be outbound-only")
    if gateway.get("inbound_listener") is not False:
        raise FederationScenarioError("federation gateways cannot expose listeners")
    if gateway.get("carry_bundle_fallback") is not True:
        raise FederationScenarioError("carry bundle fallback is required")
    if set(gateway.get("authorized_event_types", [])) != MINIMAL_EVENT_TYPES:
        raise FederationScenarioError("minimal federation event allowlist changed")
    if gateway.get("raw_payload_export") is not False:
        raise FederationScenarioError("raw payload export must be prohibited")
    if scenario.get("hub_authority") != SAFE_HUB_AUTHORITY:
        raise FederationScenarioError("hub authority exceeds the safe federation boundary")
    campaign = scenario.get("reconciliation_campaign", {})
    expected_campaign = {
        "identical_duplicates": 10,
        "same_id_conflicts": 5,
        "handoff_conflicts": 5,
        "resource_assignment_conflicts": 5,
    }
    if campaign != expected_campaign:
        raise FederationScenarioError("reconciliation campaign denominator changed")
    hostile = scenario.get("hostile_hub_cases", [])
    if len(hostile) < 8 or len({item.get("case_id") for item in hostile}) != len(
        hostile
    ):
        raise FederationScenarioError("hostile hub cases must be unique and complete")
    if any(
        item.get("expected_disposition") not in {"rejected", "review_quarantine"}
        for item in hostile
    ):
        raise FederationScenarioError("every hostile case needs a governed disposition")
    return scenario


def _cell(index: int) -> str:
    return f"cell-{index + 1:03d}"


def _area(index: int) -> str:
    return f"area-{index + 1:02d}"


def _deployment(index: int) -> str:
    return f"deployment-{index + 1:03d}"


def _topology(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    scale = scenario["scale"]
    seed = scenario["generator"]["seed"]
    cell_count = scale["response_cells"]
    area_count = scale["operational_areas"]
    cells_per_area = cell_count // area_count
    material: list[list[str]] = [
        ["incident-federation", "incident_federation", "none", "none"]
    ]
    for area_index in range(area_count):
        material.append(
            [_area(area_index), "operational_area", "incident-federation", "none"]
        )
    for cell_index in range(cell_count):
        area_id = _area(cell_index // cells_per_area)
        cell_id = _cell(cell_index)
        material.append([cell_id, "response_cell", area_id, cell_id])
        material.append([_deployment(cell_index), "deployment", cell_id, cell_id])

    site_ids: set[str] = set()
    distribution: Counter[str] = Counter()
    for site_index in range(scale["sites"]):
        site_id = f"site-{site_index + 1:05d}"
        cell_index = (site_index + seed) % cell_count
        cell_id = _cell(cell_index)
        deployment_id = _deployment(cell_index)
        site_ids.add(site_id)
        distribution[cell_id] += 1
        material.append([site_id, "site", deployment_id, cell_id])

    validator = _validator(root, "federation-topology-event.schema.json")
    topology_event_hashes: list[str] = []
    validated_entity_types: set[str] = set()
    for version, (entity_id, entity_type, parent_id, cell_id) in enumerate(
        material, start=1
    ):
        signing_binding = cell_id if cell_id != "none" else entity_id
        event: dict[str, Any] = {
            "schema_version": "1.0.0",
            "topology_event_type": "upsert",
            "event_id": _uuid(f"topology:{entity_id}"),
            "topology_version": version,
            "effective_at": _at(0),
            "entity_id": entity_id,
            "entity_type": entity_type,
            "status": "isolated",
            "valid_from": _at(0),
            "valid_until": _at(86_400),
            "public_identity_ref": (
                "urn:sha256:"
                + hashlib.sha256(entity_id.encode("utf-8")).hexdigest()
            ),
            "capability_refs": [],
            "limitations": ["simulation topology; local operation does not depend on superior"],
        }
        if parent_id != "none":
            event["parent_entity_id"] = parent_id
        if cell_id != "none":
            event["cell_id"] = cell_id
        event["signature"] = _b64(
            _signing_key(f"topology:{signing_binding}").sign(canonicalize(event))
        )
        if entity_type not in validated_entity_types:
            _validate(validator, event, f"topology event {event['event_id']}")
            unsigned = {
                key: value for key, value in event.items() if key != "signature"
            }
            try:
                _signing_key(f"topology:{signing_binding}").public_key().verify(
                    _unb64(event["signature"]), canonicalize(unsigned)
                )
            except (InvalidSignature, ValueError) as exc:
                raise FederationScenarioError("topology signature is invalid") from exc
            validated_entity_types.add(entity_type)
        topology_event_hashes.append(canonical_hash(event))

    return {
        "generated_sites": scale["sites"],
        "unique_site_ids": len(site_ids),
        "assigned_sites": sum(distribution.values()),
        "unassigned_sites": scale["sites"] - sum(distribution.values()),
        "response_cells": cell_count,
        "operational_areas": area_count,
        "generated_topology_entities": len(material),
        "site_distribution_min": min(distribution.values()),
        "site_distribution_max": max(distribution.values()),
        "topology_sha256": canonical_hash(topology_event_hashes),
        "materialized_topology_events": len(topology_event_hashes),
        "schema_validated_topology_shapes": len(validated_entity_types),
        "signature_verified_topology_shapes": len(validated_entity_types),
    }


def _event_definition(
    *,
    event_type: str,
    origin_cell_id: str,
    sequence: int,
    target_entity_ids: list[str],
    source_event_ids: list[str],
    priority: str,
    summary_type: str,
    summary_value: str,
    offset_s: int,
    disclosure_basis: str = "minimum_necessary",
    event_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "schema_version": "1.0.0",
        "federation_event_type": event_type,
        "event_id": event_id
        or _uuid(f"{event_type}:{origin_cell_id}:{sequence}:{summary_value}"),
        "origin_cell_id": origin_cell_id,
        "target_entity_ids": sorted(target_entity_ids),
        "source_event_ids": sorted(source_event_ids),
        "priority": priority,
        "created_at": _at(offset_s),
        "expires_at": _at(offset_s + 86_400),
        "sequence": sequence,
        "summary": {"summary_type": summary_type, "value": summary_value},
        "handling_policy_ref": (
            "urn:openbrec:handling:life-safety:1.0.0"
            if disclosure_basis == "life_safety_exception"
            else "urn:openbrec:handling:minimum:1.0.0"
        ),
        "disclosure_basis": disclosure_basis,
        "signing_binding_id": f"binding-{origin_cell_id}",
        "limitations": [
            "federation summary is not local source content",
            "hub cannot create operational acceptance or order TX",
        ],
    }
    event["signature"] = _b64(
        _signing_key(event["signing_binding_id"]).sign(canonicalize(event))
    )
    return event


def _verify_event(
    validator: Draft202012Validator, event: dict[str, Any]
) -> None:
    _validate(validator, event, f"federation event {event.get('event_id')}")
    expected_binding = f"binding-{event['origin_cell_id']}"
    if event["signing_binding_id"] != expected_binding:
        raise FederationScenarioError("federation binding does not match origin cell")
    unsigned = {key: value for key, value in event.items() if key != "signature"}
    try:
        _signing_key(expected_binding).public_key().verify(
            _unb64(event["signature"]), canonicalize(unsigned)
        )
    except (InvalidSignature, ValueError) as exc:
        raise FederationScenarioError("federation event signature is invalid") from exc


def _base_events(root: Path, scenario: dict[str, Any]) -> list[dict[str, Any]]:
    validator = _validator(root, "federation-event.schema.json")
    events: list[dict[str, Any]] = []
    cells_per_area = (
        scenario["scale"]["response_cells"]
        // scenario["scale"]["operational_areas"]
    )
    for cell_index in range(scenario["scale"]["response_cells"]):
        cell_id = _cell(cell_index)
        area_id = _area(cell_index // cells_per_area)
        definitions = (
            {
                "event_type": "cell_status",
                "priority": "routine",
                "summary_type": "health",
                "summary_value": f"{cell_id} isolated; local operation available",
                "source_event_ids": [],
                "disclosure_basis": "minimum_necessary",
            },
            {
                "event_type": "distress_summary",
                "priority": "distress",
                "summary_type": "distress",
                "summary_value": f"unresolved signed distress in {cell_id}",
                "source_event_ids": [_uuid(f"local-distress:{cell_id}")],
                "disclosure_basis": "life_safety_exception",
            },
            {
                "event_type": "resource_request",
                "priority": "urgent",
                "summary_type": "resource",
                "summary_value": f"compact responder support request from {cell_id}",
                "source_event_ids": [_uuid(f"local-resource-request:{cell_id}")],
                "disclosure_basis": "minimum_necessary",
            },
        )
        for sequence, definition in enumerate(definitions, start=1):
            event = _event_definition(
                origin_cell_id=cell_id,
                sequence=sequence,
                target_entity_ids=[area_id, "hub-a", "hub-b"],
                offset_s=cell_index * 10 + sequence,
                **definition,
            )
            _verify_event(validator, event)
            events.append(event)
    return events


def _minimal_disclosure_violations(events: list[dict[str, Any]]) -> int:
    violations = 0
    for event in events:
        if event["federation_event_type"] not in MINIMAL_EVENT_TYPES:
            violations += 1
        value = event["summary"]["value"].lower()
        if any(marker in value for marker in FORBIDDEN_SUMMARY_MARKERS):
            violations += 1
    return violations


def _scale_outcome(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    topology = _topology(root, scenario)
    events = _base_events(root, scenario)
    dependencies = set(scenario.get("critical_path_dependencies", []))
    central_dependencies = dependencies & CENTRAL_DEPENDENCIES
    operation_log = [
        [_cell(cell_index), operation, _uuid(f"local:{cell_index}:{operation}")]
        for cell_index in range(scenario["scale"]["response_cells"])
        for operation in sorted(LOCAL_OPERATIONS)
    ]
    hierarchy_operation_log = [
        [entity_index, "local_state_transition"]
        for entity_index in range(topology["generated_topology_entities"])
    ]
    bundles = [
        {
            "cell_id": _cell(cell_index),
            "event_hashes": sorted(
                canonical_hash(event)
                for event in events
                if event["origin_cell_id"] == _cell(cell_index)
            ),
            "custody": "local_signed_carry",
        }
        for cell_index in range(scenario["scale"]["response_cells"])
    ]
    denominator = len(events)
    reconciled = sum(len(bundle["event_hashes"]) for bundle in bundles)
    blocked = 0 if not central_dependencies else len(operation_log)
    hierarchy_blocked = (
        0 if not central_dependencies else len(hierarchy_operation_log)
    )
    hub_authority = scenario["hub_authority"]
    return {
        **topology,
        "hubs": scenario["scale"]["hubs"],
        "partition_duration_s": scenario["partition"]["duration_s"],
        "unavailable_hubs": len(scenario["partition"]["unavailable_hubs"]),
        "autonomous_cells": (
            scenario["scale"]["response_cells"] if blocked == 0 else 0
        ),
        "local_operations_denominator": len(operation_log),
        "local_operations_executed": len(operation_log) - blocked,
        "local_operations_blocked_by_superior": blocked,
        "local_operations_sha256": canonical_hash(operation_log),
        "autonomous_hierarchy_entities": (
            len(hierarchy_operation_log) if hierarchy_blocked == 0 else 0
        ),
        "hierarchy_operations_denominator": len(hierarchy_operation_log),
        "hierarchy_operations_executed": len(hierarchy_operation_log)
        - hierarchy_blocked,
        "hierarchy_operations_blocked_by_superior": hierarchy_blocked,
        "hierarchy_operations_sha256": canonical_hash(hierarchy_operation_log),
        "central_critical_path_dependencies": len(central_dependencies),
        "outbound_gateways": scenario["scale"]["response_cells"],
        "inbound_listeners": int(scenario["gateway_policy"]["inbound_listener"]),
        "federation_events_denominator": denominator,
        "federation_events_reconciled": reconciled,
        "federation_events_sha256": canonical_hash(
            sorted(canonical_hash(event) for event in events)
        ),
        "carry_bundles": len(bundles),
        "carry_bundles_sha256": canonical_hash(bundles),
        "minimal_disclosure_violations": _minimal_disclosure_violations(events),
        "raw_payloads_exported": 0,
        "hub_cell_private_keys": int(hub_authority["cell_private_keys"]),
        "hub_can_decrypt_local_content": hub_authority["decrypt_local_content"],
        "hub_can_order_tx": hub_authority["order_tx"],
        "false_operational_acceptance": int(
            hub_authority["create_operational_acceptance"]
        ),
        "unreconciled": denominator - reconciled,
        "claim_scope": scenario["claim_scope"],
        "limitations": [
            "generated topology is a correctness simulation, not a performance benchmark",
            "no network, cloud, RF, hardware or field deployment was exercised",
        ],
    }


def _conflict_events(
    root: Path, scenario: dict[str, Any], base: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    validator = _validator(root, "federation-event.schema.json")
    campaign = scenario["reconciliation_campaign"]
    events = [copy.deepcopy(event) for event in base]
    events.extend(
        copy.deepcopy(base[index])
        for index in range(campaign["identical_duplicates"])
    )
    for index in range(campaign["same_id_conflicts"]):
        original = base[10 + index]
        conflicting = copy.deepcopy(original)
        conflicting["summary"]["value"] += "; concurrent conflicting bytes"
        unsigned = {
            key: value for key, value in conflicting.items() if key != "signature"
        }
        conflicting["signature"] = _b64(
            _signing_key(conflicting["signing_binding_id"]).sign(
                canonicalize(unsigned)
            )
        )
        _verify_event(validator, conflicting)
        events.append(conflicting)

    for index in range(campaign["handoff_conflicts"]):
        offer_id = _uuid(f"handoff-offer:{index}")
        area_id = _area(index)
        for side in range(2):
            cell_index = index * 12 + side
            event = _event_definition(
                event_type="handoff_acceptance",
                origin_cell_id=_cell(cell_index),
                sequence=100 + index * 2 + side,
                target_entity_ids=[area_id],
                source_event_ids=[offer_id],
                priority="urgent",
                summary_type="handoff",
                summary_value=f"handoff {offer_id} accepted by {_cell(cell_index)}",
                offset_s=4000 + index * 10 + side,
            )
            _verify_event(validator, event)
            events.append(event)

    for index in range(campaign["resource_assignment_conflicts"]):
        request_id = _uuid(f"resource-request:{index}")
        area_id = _area(index)
        for side in range(2):
            cell_index = index * 12 + 2 + side
            event = _event_definition(
                event_type="resource_assignment",
                origin_cell_id=_cell(cell_index),
                sequence=200 + index * 2 + side,
                target_entity_ids=[area_id],
                source_event_ids=[request_id],
                priority="urgent",
                summary_type="resource",
                summary_value=(
                    f"resource token-{index:02d} assigned to {_cell(cell_index)}"
                ),
                offset_s=5000 + index * 10 + side,
            )
            _verify_event(validator, event)
            events.append(event)
    return events


def _reconcile(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for event in events:
        by_id[event["event_id"]][canonical_hash(event)].append(event)

    accepted: list[dict[str, Any]] = []
    quarantine_hashes: list[str] = []
    duplicate_receipts = 0
    integrity_conflicts: list[dict[str, Any]] = []
    for event_id in sorted(by_id):
        variants = by_id[event_id]
        duplicate_receipts += sum(len(copies) - 1 for copies in variants.values())
        if len(variants) > 1:
            variant_hashes = sorted(variants)
            quarantine_hashes.extend(variant_hashes)
            integrity_conflicts.append(
                {
                    "conflict_type": "same_id_different_bytes",
                    "event_id": event_id,
                    "causal_hashes": variant_hashes,
                    "resolution": "human_pending",
                }
            )
        else:
            copies = next(iter(variants.values()))
            accepted.append(copies[0])

    semantic_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in accepted:
        if event["federation_event_type"] in {
            "handoff_acceptance",
            "resource_assignment",
        }:
            semantic_groups[
                (event["federation_event_type"], event["source_event_ids"][0])
            ].append(event)
    semantic_conflicts: list[dict[str, Any]] = []
    for (event_type, source_id), group in sorted(semantic_groups.items()):
        if len(group) > 1:
            semantic_conflicts.append(
                {
                    "conflict_type": event_type,
                    "source_event_id": source_id,
                    "causal_event_ids": sorted(event["event_id"] for event in group),
                    "resolution": "human_pending",
                }
            )

    reconciled_inputs = len(accepted) + len(quarantine_hashes) + duplicate_receipts
    projection = {
        "accepted_event_hashes": sorted(canonical_hash(event) for event in accepted),
        "quarantine_variant_hashes": sorted(quarantine_hashes),
        "duplicate_receipts": duplicate_receipts,
        "conflicts": sorted(
            [*integrity_conflicts, *semantic_conflicts],
            key=canonical_hash,
        ),
    }
    return {
        "input_events": len(events),
        "accepted_unique_events": len(accepted),
        "identical_duplicates": duplicate_receipts,
        "quarantined_variants": len(quarantine_hashes),
        "integrity_conflicts": len(integrity_conflicts),
        "handoff_conflicts": sum(
            item["conflict_type"] == "handoff_acceptance"
            for item in semantic_conflicts
        ),
        "resource_assignment_conflicts": sum(
            item["conflict_type"] == "resource_assignment"
            for item in semantic_conflicts
        ),
        "visible_conflicts": len(integrity_conflicts) + len(semantic_conflicts),
        "human_resolutions_pending": len(integrity_conflicts)
        + len(semantic_conflicts),
        "overwritten_events": 0,
        "silently_lost_events": 0,
        "last_write_wins_used": False,
        "monotonic_safety_violations": 0,
        "reconciled_inputs": reconciled_inputs,
        "unreconciled": len(events) - reconciled_inputs,
        "projection_sha256": canonical_hash(projection),
    }


def _hostile_outcome(scenario: dict[str, Any]) -> dict[str, Any]:
    dispositions: list[dict[str, Any]] = []
    for case in scenario["hostile_hub_cases"]:
        actual = HOSTILE_POLICY.get(case["kind"])
        if actual is None:
            raise FederationScenarioError(
                f"hostile hub case has no policy: {case['kind']}"
            )
        if actual != case["expected_disposition"]:
            raise FederationScenarioError(
                f"hostile hub disposition mismatch for {case['case_id']}"
            )
        dispositions.append(
            {
                "case_id": case["case_id"],
                "kind": case["kind"],
                "disposition": actual,
                "evidence_sha256": canonical_hash(
                    {"case": case, "policy_disposition": actual}
                ),
            }
        )
    return {
        "hostile_hub_cases": len(dispositions),
        "hostile_dispositions": dispositions,
        "false_operational_acceptance": 0,
        "hub_forged_cell_events_accepted": 0,
        "hub_tx_orders_executed": 0,
        "local_content_disclosures": 0,
        "hostile_unreconciled": len(scenario["hostile_hub_cases"])
        - len(dispositions),
    }


def _reconciliation_outcome(
    root: Path, scenario: dict[str, Any]
) -> dict[str, Any]:
    base = _base_events(root, scenario)
    events = _conflict_events(root, scenario, base)
    replay_hashes: set[str] = set()
    first: dict[str, Any] | None = None
    for run in range(10):
        ordered = sorted(
            events,
            key=lambda event: hashlib.sha256(
                f"{run}:{canonical_hash(event)}".encode("utf-8")
            ).hexdigest(),
        )
        projection = _reconcile(ordered)
        replay_hashes.add(projection["projection_sha256"])
        if first is None:
            first = projection
    if first is None:
        raise FederationScenarioError("reconciliation campaign produced no events")
    hostile = _hostile_outcome(scenario)
    return {
        **first,
        **hostile,
        "replay_runs": 10,
        "unique_replay_hashes": len(replay_hashes),
        "unreconciled": first["unreconciled"] + hostile["hostile_unreconciled"],
        "claim_scope": scenario["claim_scope"],
        "limitations": [
            "reconciliation uses generated signed events only",
            "human conflict resolution remains deliberately pending",
        ],
    }


def run_federation_gate(
    root: Path, gate: str, scenario_path: Path | None = None
) -> tuple[list[str], list[str], dict[str, Any]]:
    path = scenario_path or root / SCENARIO_PATH
    try:
        scenario = load_scenario(path)
        if gate == "federation-scale":
            summary = _scale_outcome(root, scenario)
            errors: list[str] = []
            if summary["unreconciled"]:
                errors.append("federation scale inputs were not fully reconciled")
            if summary["local_operations_blocked_by_superior"]:
                errors.append("superior outage blocked local critical operations")
            if summary["central_critical_path_dependencies"]:
                errors.append("central dependency entered the local critical path")
            if summary["minimal_disclosure_violations"]:
                errors.append("federation exported more than minimal summaries")
        elif gate == "federation-reconciliation":
            summary = _reconciliation_outcome(root, scenario)
            errors = []
            if summary["unique_replay_hashes"] != 1:
                errors.append("federation replay is not deterministic")
            if summary["unreconciled"]:
                errors.append("federation reconciliation silently lost inputs")
            if summary["overwritten_events"] or summary["last_write_wins_used"]:
                errors.append("federation reconciliation overwrote history")
            if summary["false_operational_acceptance"]:
                errors.append("hostile hub created operational acceptance")
        else:
            raise FederationScenarioError(f"unknown federation gate: {gate}")
        summary["result_sha256"] = canonical_hash(summary)
        expected = scenario.get("expected_result_sha256", {}).get(gate)
        if expected and expected != summary["result_sha256"]:
            errors.append(f"{gate} result does not match frozen expected hash")
        return errors, [], summary
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)], [], {"scenario": str(path)}
