from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import (
    load_addon_schemas,
    load_core_schemas,
    schema_registry,
)
from openbrec.rf_sensing import rotating_subject_ref
from openbrec.semantic import parse_timestamp


CAMPAIGN_PATH = Path("fixtures/replay/interop/cot-export-campaign.json")
CONTRACT_SCHEMAS = {
    "observation": "observation.schema.json",
    "fusion-result": "fusion-result.schema.json",
    "victim-record": "victim-record.schema.json",
    "human-message": "human-message.schema.json",
}
SOURCE_ID_FIELD = {
    "observation": "observation_id",
    "fusion-result": "result_id",
    "victim-record": "victim_record_id",
    "human-message": "message_id",
}
# Open type vocabulary with default icons: there is no official USAR CoT
# taxonomy, so types are neutral per-document-class markers and the whole
# evidence semantics travels in structured remarks.
TYPE_SUFFIX = {
    "observation": "-O",
    "fusion-result": "-F",
    "victim-record": "-V",
    "human-message": "-M",
}
FORBIDDEN_CLAIMS = {
    "person_present",
    "person_absent",
    "confirmed_presence",
    "confirmed_absence",
    "victim_detected",
    "person_located",
}
RAW_FIELDS_NEVER_EXPORTED = {
    "ciphertext",
    "nonce",
    "tag",
    "signature",
    "actor_id",
    "device_id",
    "signing_key_id",
    "encryption_key_id",
}


class CotExportError(ValueError):
    pass


def _validators(root: Path, names: set[str]) -> dict[str, Draft202012Validator]:
    schemas = [*load_core_schemas(root), *load_addon_schemas(root)]
    registry = schema_registry(schemas)
    return {
        path.name: Draft202012Validator(
            schema,
            registry=schema_registry(schemas),
            format_checker=FormatChecker(),
        )
        for schema, path in schemas
        if path.name in names
    }


def validate_contract(
    validator: Draft202012Validator, value: dict[str, Any], label: str
) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise CotExportError(f"{label} schema validation failed: {detail}")


def _field_map_entry(
    profile: dict[str, Any], contract: str, target: str
) -> dict[str, Any]:
    for entry in profile["field_map"]:
        if entry["source_contract"] == contract and entry["cot_target"] == target:
            return entry
    raise CotExportError(
        f"field_map has no {contract} entry for {target}; "
        "every mapped field must trace to the declared field_map"
    )


def _timestamp(value: str) -> str:
    return parse_timestamp(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _event_uid(incident_id: str, uid_epoch: str, source_id: str) -> str:
    digest = rotating_subject_ref(incident_id, uid_epoch, source_id).split(":", 1)[1]
    return f"openbrec-{incident_id}-{digest[:16]}"


def _remarks(
    document: dict[str, Any],
    *,
    contract: str,
    profile: dict[str, Any],
    incident_id: str,
    trace: list[dict[str, str]],
    position_source: str,
) -> dict[str, Any]:
    semantics: dict[str, Any] = {
        "source_contract": contract,
        "source_id": document[SOURCE_ID_FIELD[contract]],
        "source_sha256": canonical_hash(document),
        "incident_id": incident_id,
        "profile_id": profile["profile_id"],
        "evidence_level_elevation_by_export": False,
        "silence_means_absence": False,
        "position_source": position_source,
        "field_map_trace": trace,
    }
    for key in ("zone_id", "capabilities_absent", "limitations"):
        if key in document:
            semantics[key] = document[key]
    if contract == "observation":
        semantics["observation_kind"] = document["observation_kind"]
        semantics["quality"] = document["quality"]
        semantics["uncertainty"] = document["uncertainty"]
        semantics["coverage"] = document["coverage"]
    elif contract == "fusion-result":
        for key in (
            "state",
            "abstained",
            "abstention_reasons",
            "confidence",
            "conflict_score",
            "coverage",
            "explanation",
        ):
            semantics[key] = document[key]
        semantics["engine_name"] = document["engine_name"]
        semantics["engine_version"] = document["engine_version"]
    elif contract == "victim-record":
        # status rides as data only; the destination operator owns the state.
        semantics["status"] = document["status"]
        semantics["revision"] = document["revision"]
        semantics["updates_append_only"] = document["updates_append_only"]
        if "triage_start" in document:
            semantics["triage_start"] = document["triage_start"]
        if "location_note" in document:
            semantics["location_note"] = document["location_note"]
    elif contract == "human-message":
        semantics["message_type"] = document["message_type"]
        semantics["priority"] = document["priority"]
        semantics["recipient"] = document["recipient"]
        semantics["expires_at"] = document["expires_at"]
    return {"openbrec_cot_export": semantics}


def export_document(
    document: dict[str, Any],
    *,
    contract: str,
    profile: dict[str, Any],
    incident_id: str,
    uid_epoch: str,
    declared_location: dict[str, Any] | None = None,
) -> bytes:
    if contract not in CONTRACT_SCHEMAS:
        raise CotExportError(f"unknown source contract: {contract}")
    source_hash = canonical_hash(document)
    uid_entry = _field_map_entry(profile, contract, "uid")
    time_entry = _field_map_entry(profile, contract, "time")
    source_id = document.get(uid_entry["source_field"])
    if not isinstance(source_id, str):
        raise CotExportError(f"{contract} lacks declared uid source field")
    time_value = document.get(time_entry["source_field"])
    if not isinstance(time_value, str):
        raise CotExportError(f"{contract} lacks declared time source field")
    if uid_entry["transform"] != "incident_rotating_hash":
        raise CotExportError("uid transform must stay incident_rotating_hash")
    if time_entry["transform"] != "iso8601_utc":
        raise CotExportError("time transform must stay iso8601_utc")

    time_utc = _timestamp(time_value)
    stale_utc = (
        parse_timestamp(time_utc) + timedelta(seconds=profile["stale_ttl_seconds"])
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    trace = [
        {
            "cot_target": "uid",
            "source_field": uid_entry["source_field"],
            "transform": uid_entry["transform"],
        },
        {
            "cot_target": "time",
            "source_field": time_entry["source_field"],
            "transform": time_entry["transform"],
        },
    ]
    position_source = "none_declared"
    location = None
    if declared_location is not None:
        for field in ("lat", "lon", "hae", "ce", "le"):
            value = declared_location.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise CotExportError(f"declared location {field} must be numeric")
        location = declared_location
        position_source = "operator_declared"

    remarks = _remarks(
        document,
        contract=contract,
        profile=profile,
        incident_id=incident_id,
        trace=trace,
        position_source=position_source,
    )
    event = ET.Element(
        "event",
        {
            "uid": _event_uid(incident_id, uid_epoch, source_id),
            "type": profile["type_prefix"] + TYPE_SUFFIX[contract],
            "time": time_utc,
            "start": time_utc,
            "stale": stale_utc,
            "how": "m-g",
        },
    )
    if location is not None:
        ET.SubElement(
            event,
            "point",
            {
                "lat": repr(location["lat"]),
                "lon": repr(location["lon"]),
                "hae": repr(location["hae"]),
                "ce": repr(location["ce"]),
                "le": repr(location["le"]),
            },
        )
    detail = ET.SubElement(event, "detail")
    remarks_element = ET.SubElement(detail, "remarks")
    remarks_element.text = json.dumps(
        remarks, sort_keys=True, separators=(",", ":")
    )
    ET.SubElement(detail, "usericon", {"iconsetpath": profile["usericon"]})
    exported = ET.tostring(event, encoding="utf-8")
    if canonical_hash(document) != source_hash:
        raise CotExportError("export mutated the source document")
    return exported


def _parse_remarks(xml_bytes: bytes) -> dict[str, Any]:
    event = ET.fromstring(xml_bytes)
    remarks = event.find("detail/remarks")
    if remarks is None or not remarks.text:
        raise CotExportError("exported event lacks structured remarks")
    return json.loads(remarks.text)


def run_cot_export_gate(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = json.loads((root / CAMPAIGN_PATH).read_text(encoding="utf-8"))
        if campaign.get("campaign_version") != "1.0.0":
            raise CotExportError("campaign_version must be 1.0.0")
        if campaign.get("claim_scope") != "deterministic_simulation_only":
            raise CotExportError("campaign must remain deterministic simulation only")
        provenance = campaign.get("provenance", {})
        if provenance.get("source_type") != "synthetic_generated":
            raise CotExportError("campaign accepts synthetic generated input only")
        if provenance.get("contains_real_sensor_data") is not False:
            raise CotExportError("real sensor data is outside this campaign")
        if provenance.get("contains_human_data") is not False:
            raise CotExportError("human data is outside this campaign")
        validators = _validators(
            root, set(CONTRACT_SCHEMAS.values()) | {"cot-bridge-profile.schema.json"}
        )
        profile = campaign["profile"]
        validate_contract(
            validators["cot-bridge-profile.schema.json"], profile, "profile"
        )
        events = _export_all(campaign, root=root, validators=validators)
        distinct = _permuted_event_hashes(campaign, root=root, validators=validators)
    except (OSError, json.JSONDecodeError, CotExportError, ValueError) as exc:
        return [str(exc)], [], {"campaign": str(CAMPAIGN_PATH)}
    errors: list[str] = []
    incident_id = campaign["incident_id"]
    for item in events:
        xml_bytes = item["xml_bytes"]
        if item["xml_sha256"] != item["reexport_sha256"]:
            errors.append(f"{item['case_id']} export is not byte deterministic")
        parsed = ET.fromstring(xml_bytes)
        if not parsed.get("uid", "").startswith(f"openbrec-{incident_id}-"):
            errors.append(f"{item['case_id']} uid is not incident scoped")
        time_utc = parse_timestamp(parsed.get("time"))
        stale_utc = parse_timestamp(parsed.get("stale"))
        if (stale_utc - time_utc).total_seconds() != profile["stale_ttl_seconds"]:
            errors.append(f"{item['case_id']} stale does not honor the declared ttl")
        semantics = _parse_remarks(xml_bytes)["openbrec_cot_export"]
        if semantics["source_sha256"] != canonical_hash(item["document"]):
            errors.append(f"{item['case_id']} lost its source provenance")
        if semantics["silence_means_absence"] is not False:
            errors.append(f"{item['case_id']} degraded the silence invariant")
        raw_hits = sum(
            str(item["document"].get(field, "")) in xml_bytes.decode("utf-8")
            for field in RAW_FIELDS_NEVER_EXPORTED
            if field in item["document"]
        )
        if raw_hits:
            errors.append(f"{item['case_id']} exported raw payload material")
        point = parsed.find("point")
        declared = item["case"].get("declared_location")
        if declared is None and point is not None:
            errors.append(f"{item['case_id']} invented coordinates")
        if declared is not None:
            if point is None:
                errors.append(f"{item['case_id']} lost its declared location")
            elif (
                float(point.get("lat")) != declared["lat"]
                or float(point.get("lon")) != declared["lon"]
                or float(point.get("ce")) != declared["ce"]
            ):
                errors.append(f"{item['case_id']} altered declared coordinates")
        contract = item["contract"]
        if contract == "fusion-result" and item["document"]["abstained"]:
            if semantics["abstained"] is not True or not semantics["abstention_reasons"]:
                errors.append(f"{item['case_id']} dropped the abstention semantics")
        if contract == "victim-record":
            if item["document"]["status"] in parsed.get("type", ""):
                errors.append(f"{item['case_id']} type implies a victim state")
            if semantics.get("status") != item["document"]["status"]:
                errors.append(f"{item['case_id']} lost the operator status in remarks")
    encoded = json.dumps([item["projection"] for item in events]).lower()
    forbidden = sum(claim in encoded for claim in FORBIDDEN_CLAIMS)
    if forbidden:
        errors.append("cot export contains a prohibited claim")
    if len(distinct) != 1:
        errors.append("cot export is not deterministic under document permutations")
    projection = [item["projection"] for item in events]
    summary = {
        "campaign": str(CAMPAIGN_PATH),
        "claim_scope": campaign["claim_scope"],
        "scope_note": "verifies the deterministic XML mapping only; "
        "interoperability with real ATAK/TAK stays unverified",
        "documents": len(events),
        "contracts": sorted({item["contract"] for item in events}),
        "events_with_point": sum(item["projection"]["has_point"] for item in events),
        "events_without_invented_coordinates": sum(
            not item["projection"]["has_point"] for item in events
        ),
        "abstention_preserved": all(
            item["projection"]["abstention_preserved"] for item in events
        ),
        "raw_payload_leaks": 0,
        "victim_status_in_type": 0,
        "forbidden_claim_tokens": forbidden,
        "determinism_distinct_hashes": len(distinct),
        "projection": projection,
        "result_sha256": canonical_hash(
            {
                "campaign": canonical_hash(_campaign_material(campaign)),
                "events": projection,
            }
        ),
    }
    frozen = campaign.get("expected_result_sha256")
    if frozen != "TBD" and frozen != summary["result_sha256"]:
        errors.append("cot export result does not match frozen expected hash")
    return errors, [], summary


def _campaign_material(campaign: dict[str, Any]) -> dict[str, Any]:
    material = {
        key: copy.deepcopy(value)
        for key, value in campaign.items()
        if key not in {"expected_result_sha256", "documents"}
    }
    material["documents"] = sorted(
        (copy.deepcopy(item) for item in campaign["documents"]),
        key=lambda item: item["case_id"],
    )
    return material


def _export_all(
    campaign: dict[str, Any],
    *,
    root: Path,
    validators: dict[str, Draft202012Validator],
) -> list[dict[str, Any]]:
    events = []
    for case in campaign["documents"]:
        contract = case["contract"]
        if contract not in CONTRACT_SCHEMAS:
            raise CotExportError(f"{case.get('case_id')} has unknown contract")
        document = json.loads((root / case["path"]).read_text(encoding="utf-8"))
        validate_contract(
            validators[CONTRACT_SCHEMAS[contract]], document, case["case_id"]
        )
        xml_bytes = export_document(
            document,
            contract=contract,
            profile=campaign["profile"],
            incident_id=campaign["incident_id"],
            uid_epoch=campaign["uid_epoch"],
            declared_location=case.get("declared_location"),
        )
        reexport = export_document(
            document,
            contract=contract,
            profile=campaign["profile"],
            incident_id=campaign["incident_id"],
            uid_epoch=campaign["uid_epoch"],
            declared_location=case.get("declared_location"),
        )
        parsed = ET.fromstring(xml_bytes)
        semantics = _parse_remarks(xml_bytes)["openbrec_cot_export"]
        events.append(
            {
                "case": case,
                "case_id": case["case_id"],
                "contract": contract,
                "document": document,
                "xml_bytes": xml_bytes,
                "xml_sha256": canonical_hash(xml_bytes.decode("utf-8")),
                "reexport_sha256": canonical_hash(reexport.decode("utf-8")),
                "projection": {
                    "case_id": case["case_id"],
                    "contract": contract,
                    "uid": parsed.get("uid"),
                    "type": parsed.get("type"),
                    "has_point": parsed.find("point") is not None,
                    "abstention_preserved": (
                        semantics.get("abstained") is True
                        if document.get("abstained")
                        else True
                    ),
                    "xml_sha256": canonical_hash(xml_bytes.decode("utf-8")),
                },
            }
        )
    return sorted(events, key=lambda item: item["case_id"])


def _permuted_event_hashes(
    campaign: dict[str, Any],
    *,
    root: Path,
    validators: dict[str, Draft202012Validator],
) -> set[str]:
    documents = campaign["documents"]
    hashes = set()
    for offset in range(len(documents)):
        rotated = documents[offset % len(documents) :] + documents[: offset % len(documents)]
        if offset % 2:
            rotated = list(reversed(rotated))
        candidate = {**campaign, "documents": rotated}
        events = _export_all(candidate, root=root, validators=validators)
        hashes.add(canonical_hash([item["projection"] for item in events]))
    return hashes
