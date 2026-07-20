from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = REPO_ROOT / "fixtures/replay/interop/cot-export-campaign.json"
OBSERVATION = REPO_ROOT / "fixtures/contracts/core/1.0.0/observation/valid/complete.json"
FUSION_RESULT = REPO_ROOT / "fixtures/contracts/core/1.0.0/fusion-result/valid/minimal.json"
VICTIM_RECORD = REPO_ROOT / "fixtures/contracts/addons/1.0.0/victim-record/valid/complete.json"
HUMAN_MESSAGE = REPO_ROOT / "fixtures/contracts/addons/1.0.0/human-message/valid/minimal.json"
LOCATION = {
    "lat": -34.6037,
    "lon": -58.3816,
    "hae": 25.0,
    "ce": 15.0,
    "le": 20.0,
    "declared_by": "operator",
    "note": "sector anchor declared by operator, not sensor derived",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CotExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cot = load_module(
            "openbrec_cot_export_test", REPO_ROOT / "openbrec/cot_export.py"
        )
        self.campaign = load_json(CAMPAIGN)
        self.profile = self.campaign["profile"]
        self.incident_id = self.campaign["incident_id"]
        self.uid_epoch = self.campaign["uid_epoch"]

    def export(self, path: Path, contract: str, location: dict | None = None) -> bytes:
        return self.cot.export_document(
            load_json(path),
            contract=contract,
            profile=self.profile,
            incident_id=self.incident_id,
            uid_epoch=self.uid_epoch,
            declared_location=location,
        )

    def remarks(self, xml_bytes: bytes) -> dict:
        event = ET.fromstring(xml_bytes)
        return json.loads(event.find("detail/remarks").text)["openbrec_cot_export"]

    def test_xml_is_well_formed_and_byte_deterministic(self) -> None:
        first = self.export(OBSERVATION, "observation", LOCATION)
        second = self.export(OBSERVATION, "observation", LOCATION)
        self.assertEqual(first, second)
        event = ET.fromstring(first)
        self.assertEqual(event.tag, "event")
        self.assertEqual(event.get("how"), "m-g")
        self.assertIsNotNone(event.find("detail/usericon"))

    def test_uid_is_incident_scoped_and_stable(self) -> None:
        xml_bytes = self.export(OBSERVATION, "observation")
        uid = ET.fromstring(xml_bytes).get("uid")
        self.assertTrue(uid.startswith(f"openbrec-{self.incident_id}-"))
        other_incident = self.cot.export_document(
            load_json(OBSERVATION),
            contract="observation",
            profile=self.profile,
            incident_id="22222222-2222-4222-8222-222222222222",
            uid_epoch=self.uid_epoch,
        )
        self.assertNotEqual(uid, ET.fromstring(other_incident).get("uid"))

    def test_stale_honors_the_profile_ttl(self) -> None:
        event = ET.fromstring(self.export(OBSERVATION, "observation"))
        from openbrec.semantic import parse_timestamp

        delta = parse_timestamp(event.get("stale")) - parse_timestamp(event.get("time"))
        self.assertEqual(delta.total_seconds(), self.profile["stale_ttl_seconds"])
        self.assertEqual(event.get("start"), event.get("time"))

    def test_declared_location_maps_exactly_and_undeclared_omits_point(self) -> None:
        located = ET.fromstring(self.export(OBSERVATION, "observation", LOCATION))
        point = located.find("point")
        self.assertIsNotNone(point)
        self.assertEqual(float(point.get("lat")), LOCATION["lat"])
        self.assertEqual(float(point.get("lon")), LOCATION["lon"])
        self.assertEqual(float(point.get("ce")), LOCATION["ce"])
        self.assertEqual(
            self.remarks(ET.tostring(located))["position_source"], "operator_declared"
        )
        zoned = ET.fromstring(self.export(OBSERVATION, "observation"))
        self.assertIsNone(zoned.find("point"))
        self.assertEqual(
            self.remarks(ET.tostring(zoned))["position_source"], "none_declared"
        )

    def test_provenance_and_evidence_semantics_ride_in_remarks(self) -> None:
        semantics = self.remarks(self.export(OBSERVATION, "observation"))
        self.assertEqual(semantics["source_contract"], "observation")
        self.assertEqual(len(semantics["source_sha256"]), 64)
        self.assertFalse(semantics["silence_means_absence"])
        self.assertFalse(semantics["evidence_level_elevation_by_export"])
        self.assertIn("capabilities_absent", semantics)
        self.assertTrue(semantics["field_map_trace"])

    def test_abstained_fusion_result_keeps_abstention_not_absence(self) -> None:
        xml_bytes = self.export(FUSION_RESULT, "fusion-result")
        semantics = self.remarks(xml_bytes)
        self.assertEqual(semantics["state"], "abstained")
        self.assertTrue(semantics["abstained"])
        self.assertTrue(semantics["abstention_reasons"])
        self.assertFalse(semantics["silence_means_absence"])
        self.assertNotIn("person_absent", xml_bytes.decode("utf-8"))

    def test_victim_record_type_never_implies_a_state(self) -> None:
        document = load_json(VICTIM_RECORD)
        xml_bytes = self.cot.export_document(
            document,
            contract="victim-record",
            profile=self.profile,
            incident_id=self.incident_id,
            uid_epoch=self.uid_epoch,
        )
        event = ET.fromstring(xml_bytes)
        self.assertNotIn(document["status"], event.get("type"))
        self.assertEqual(self.remarks(xml_bytes)["status"], document["status"])

    def test_human_message_never_exports_raw_payload(self) -> None:
        document = load_json(HUMAN_MESSAGE)
        xml_text = self.export(HUMAN_MESSAGE, "human-message").decode("utf-8")
        for field in ("ciphertext", "nonce", "tag", "signature"):
            self.assertNotIn(document[field], xml_text)
        semantics = self.remarks(xml_text.encode("utf-8"))
        self.assertEqual(semantics["message_type"], "sos")
        self.assertEqual(semantics["priority"], "distress")

    def test_invalid_inputs_raise_typed_errors(self) -> None:
        document = load_json(OBSERVATION)
        with self.assertRaises(self.cot.CotExportError):
            self.cot.export_document(
                document,
                contract="telemetry",
                profile=self.profile,
                incident_id=self.incident_id,
                uid_epoch=self.uid_epoch,
            )
        broken_profile = {
            **self.profile,
            "field_map": [
                entry
                for entry in self.profile["field_map"]
                if not (
                    entry["source_contract"] == "observation"
                    and entry["cot_target"] == "time"
                )
            ],
        }
        with self.assertRaises(self.cot.CotExportError):
            self.cot.export_document(
                document,
                contract="observation",
                profile=broken_profile,
                incident_id=self.incident_id,
                uid_epoch=self.uid_epoch,
            )
        with self.assertRaises(self.cot.CotExportError):
            self.cot.export_document(
                document,
                contract="observation",
                profile=self.profile,
                incident_id=self.incident_id,
                uid_epoch=self.uid_epoch,
                declared_location={"lat": "north", "lon": -58.0},
            )

    def test_document_order_permutation_yields_same_event_set(self) -> None:
        validators = self.cot._validators(
            REPO_ROOT, set(self.cot.CONTRACT_SCHEMAS.values())
        )
        hashes = self.cot._permuted_event_hashes(
            self.campaign, root=REPO_ROOT, validators=validators
        )
        self.assertEqual(len(hashes), 1)


class CotGateCliTests(unittest.TestCase):
    def test_interop_cot_gate_passes_with_frozen_hash(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "openbrec.verify", "interop-cot"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["result"], "passed")
        self.assertEqual(outcome["summary"]["determinism_distinct_hashes"], 1)
        self.assertEqual(outcome["summary"]["forbidden_claim_tokens"], 0)
        self.assertEqual(outcome["summary"]["victim_status_in_type"], 0)
        self.assertTrue(outcome["summary"]["abstention_preserved"])
        self.assertIn("unverified", outcome["summary"]["scope_note"])


if __name__ == "__main__":
    unittest.main()
