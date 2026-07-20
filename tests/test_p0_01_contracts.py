from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from openbrec import contracts


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ADDON_SCHEMAS = {
    "bearer-capability",
    "beacon-capability",
    "beacon-health",
    "beacon-observation",
    "beacon-placement",
    "capture-authorization-event",
    "clock-discipline-profile",
    "cot-bridge-profile",
    "csi-link-observation",
    "drone-deployment-event",
    "emergency-autojoin-profile",
    "energy-budget",
    "energy-capability",
    "energy-status",
    "federation-event",
    "federation-topology-event",
    "human-message",
    "human-message-event",
    "identity-key-lifecycle-profile",
    "interop-emergency-standards-profile",
    "offline-finding-observation",
    "offline-mapping-profile",
    "passive-rf-observation",
    "review-task-event",
    "rf-isolation-profile",
    "ruview-observation",
    "sdr-receive-profile",
    "terminal-capability",
    "transport-envelope",
    "transport-policy-decision",
    "transport-profile",
    "victim-record",
}


class P001AddonContractTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_passed(
        self, result: subprocess.CompletedProcess[str]
    ) -> dict[str, object]:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_addon_gates_are_registered(self) -> None:
        for gate in ("addon-contracts", "addon-fixtures"):
            result = self.run_verify(gate, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ci_runs_addon_contract_and_fixture_gates(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("openbrec.verify addon-contracts", workflow)
        self.assertIn("openbrec.verify addon-fixtures", workflow)

    def test_addon_catalog_is_complete_and_experimental(self) -> None:
        catalog_path = REPO_ROOT / "schemas/addons/catalog.json"
        self.assertTrue(catalog_path.is_file())
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        names = {
            Path(entry["path"]).name.removesuffix(".schema.json")
            for entry in catalog["entries"]
        }
        self.assertEqual(names, EXPECTED_ADDON_SCHEMAS)
        self.assertEqual(catalog["status"], "experimental")
        self.assertTrue(
            all(entry["status"] == "experimental" for entry in catalog["entries"])
        )

    def test_addon_contract_gate_validates_metaschema_and_catalog(self) -> None:
        output = self.assert_passed(self.run_verify("addon-contracts"))
        self.assertEqual(output["scope"], "addon_metaschema_and_catalog")
        self.assertEqual(output["summary"]["addon_schemas"], 32)
        self.assertEqual(output["summary"]["support_status"], "experimental")

    def test_addon_fixture_gate_reconciles_positive_and_negative_cases(self) -> None:
        output = self.assert_passed(self.run_verify("addon-fixtures"))
        self.assertEqual(output["scope"], "addon_schema_fixture_matrix")
        self.assertEqual(output["summary"]["schemas"], 32)
        self.assertEqual(output["summary"]["valid_fixtures"], 64)
        self.assertEqual(output["summary"]["invalid_fixtures"], 224)

    def test_generated_consumers_include_all_addon_contracts(self) -> None:
        output = self.assert_passed(self.run_verify("contracts-gen", "--check"))
        self.assertEqual(output["summary"]["addon_schemas"], 32)
        python_models = (
            REPO_ROOT / "packages/contracts/generated/addons/python/models.py"
        )
        typescript_models = (
            REPO_ROOT / "packages/contracts/generated/addons/typescript/models.d.ts"
        )
        self.assertTrue(python_models.is_file())
        self.assertTrue(typescript_models.is_file())
        python_source = python_models.read_text(encoding="utf-8")
        typescript_source = typescript_models.read_text(encoding="utf-8")
        self.assertIn("HumanMessage", python_source)
        self.assertIn("BeaconObservation", typescript_source)

    def test_addon_compatibility_baseline_is_frozen(self) -> None:
        output = self.assert_passed(self.run_verify("schema-compat"))
        self.assertEqual(output["summary"]["addon_schemas"], 32)
        self.assertEqual(output["summary"]["addon_status"], "experimental")

    def test_contracts_enforce_life_safety_and_transport_boundaries(self) -> None:
        self.assertTrue(hasattr(contracts, "load_addon_schemas"))
        addon_schemas = contracts.load_addon_schemas(REPO_ROOT)
        all_schemas = [*contracts.load_core_schemas(REPO_ROOT), *addon_schemas]
        registry = contracts.schema_registry(all_schemas)

        def schema(name: str) -> dict[str, object]:
            return next(
                item
                for item, path in addon_schemas
                if path.name == f"{name}.schema.json"
            )

        def errors(name: str, instance: object) -> list[object]:
            return list(
                Draft202012Validator(
                    schema(name),
                    registry=registry,
                    format_checker=FormatChecker(),
                ).iter_errors(instance)
            )

        message_event = copy.deepcopy(schema("human-message-event")["examples"][0])
        message_event["state"] = "accepted"
        self.assertTrue(errors("human-message-event", message_event))

        bearer = copy.deepcopy(schema("bearer-capability")["examples"][0])
        bearer["support_status"] = "supported"
        self.assertTrue(errors("bearer-capability", bearer))

        beacon = copy.deepcopy(schema("beacon-observation")["examples"][0])
        beacon["measurements"][0]["metric"] = "person_present"
        self.assertTrue(errors("beacon-observation", beacon))

        victim = copy.deepcopy(schema("victim-record")["examples"][0])
        victim["confirmation"]["method"] = "fusion_automatic"
        self.assertTrue(errors("victim-record", victim))
        victim = copy.deepcopy(schema("victim-record")["examples"][0])
        victim["silence_means_absence"] = True
        self.assertTrue(errors("victim-record", victim))
        victim = copy.deepcopy(schema("victim-record")["examples"][0])
        victim["updates_append_only"] = False
        self.assertTrue(errors("victim-record", victim))

        identity = copy.deepcopy(
            schema("identity-key-lifecycle-profile")["examples"][0]
        )
        identity["simulated_derivation"]["allowed_profiles"] = ["field"]
        self.assertTrue(errors("identity-key-lifecycle-profile", identity))

        clock = copy.deepcopy(schema("clock-discipline-profile")["examples"][0])
        clock["clock_jump_policy"]["silent_reorder_allowed"] = True
        self.assertTrue(errors("clock-discipline-profile", clock))

        mapping = copy.deepcopy(schema("offline-mapping-profile")["examples"][1])
        mapping["search_areas"][0]["pod"]["automatic"] = True
        self.assertTrue(errors("offline-mapping-profile", mapping))

        interop = copy.deepcopy(
            schema("interop-emergency-standards-profile")["examples"][0]
        )
        interop["invariants"]["gateway_received_means_rescue"] = True
        self.assertTrue(errors("interop-emergency-standards-profile", interop))
        interop = copy.deepcopy(
            schema("interop-emergency-standards-profile")["examples"][0]
        )
        interop["gateway_implemented"] = True
        self.assertTrue(errors("interop-emergency-standards-profile", interop))

        csi = copy.deepcopy(schema("csi-link-observation")["examples"][0])
        csi["silence_means_absence"] = True
        self.assertTrue(errors("csi-link-observation", csi))
        csi = copy.deepcopy(schema("csi-link-observation")["examples"][0])
        csi["automatic_person_detection_allowed"] = True
        self.assertTrue(errors("csi-link-observation", csi))

        passive = copy.deepcopy(schema("passive-rf-observation")["examples"][0])
        passive["subject_ref"] = "aa:bb:cc:dd:ee:ff"
        self.assertTrue(errors("passive-rf-observation", passive))
        passive = copy.deepcopy(schema("passive-rf-observation")["examples"][0])
        passive["payload_retained"] = True
        self.assertTrue(errors("passive-rf-observation", passive))
        passive = copy.deepcopy(schema("passive-rf-observation")["examples"][0])
        passive["content_interception"] = True
        self.assertTrue(errors("passive-rf-observation", passive))
        passive = copy.deepcopy(schema("passive-rf-observation")["examples"][0])
        passive["active_emulation"] = True
        self.assertTrue(errors("passive-rf-observation", passive))

        sdr = copy.deepcopy(schema("sdr-receive-profile")["examples"][0])
        sdr["demodulate_third_party_traffic"] = True
        self.assertTrue(errors("sdr-receive-profile", sdr))
        sdr = copy.deepcopy(schema("sdr-receive-profile")["examples"][0])
        sdr["mode"] = "transmit_in_field"
        self.assertTrue(errors("sdr-receive-profile", sdr))

        ruview = copy.deepcopy(schema("ruview-observation")["examples"][0])
        ruview["outputs_are_victim_detected"] = True
        self.assertTrue(errors("ruview-observation", ruview))

        drone = copy.deepcopy(schema("drone-deployment-event")["examples"][0])
        drone["release_mode"] = "automatic"
        self.assertTrue(errors("drone-deployment-event", drone))
        drone = copy.deepcopy(schema("drone-deployment-event")["examples"][0])
        drone["flight_authority_in_core"] = True
        self.assertTrue(errors("drone-deployment-event", drone))

        isolation = copy.deepcopy(schema("rf-isolation-profile")["examples"][0])
        isolation["measurements"] = []
        self.assertTrue(errors("rf-isolation-profile", isolation))
        isolation = copy.deepcopy(schema("rf-isolation-profile")["examples"][0])
        isolation["never_enclose_possible_victim_sector_without_analysis"] = False
        self.assertTrue(errors("rf-isolation-profile", isolation))

        finding = copy.deepcopy(
            schema("offline-finding-observation")["examples"][0]
        )
        finding["gatt_connection_attempted"] = True
        self.assertTrue(errors("offline-finding-observation", finding))
        finding = copy.deepcopy(
            schema("offline-finding-observation")["examples"][0]
        )
        finding["identification_attempted"] = True
        self.assertTrue(errors("offline-finding-observation", finding))
        finding = copy.deepcopy(
            schema("offline-finding-observation")["examples"][0]
        )
        finding["raw_identifier_retained"] = True
        self.assertTrue(errors("offline-finding-observation", finding))
        finding = copy.deepcopy(
            schema("offline-finding-observation")["examples"][0]
        )
        finding["alert_trigger_allowed"] = True
        self.assertTrue(errors("offline-finding-observation", finding))
        finding = copy.deepcopy(
            schema("offline-finding-observation")["examples"][0]
        )
        finding["silence_means_absence"] = True
        self.assertTrue(errors("offline-finding-observation", finding))

        def autojoin() -> dict[str, object]:
            return copy.deepcopy(
                schema("emergency-autojoin-profile")["examples"][0]
            )

        profile = autojoin()
        profile["regulatory_mode"] = "receive_only"
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["dual_authorization_required"] = False
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        del profile["expires_at"]
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["content_interception"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["traffic_rerouting_allowed"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["credential_capture"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["person_identification_allowed"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["portal_ack_means_person_located"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["default_profile_allowed"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))
        profile = autojoin()
        profile["silence_means_absence"] = True
        self.assertTrue(errors("emergency-autojoin-profile", profile))

        def cot_bridge() -> dict[str, object]:
            return copy.deepcopy(schema("cot-bridge-profile")["examples"][0])

        cot = cot_bridge()
        cot["direction"] = "bidirectional"
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["gateway_implemented"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["person_identification_allowed"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["raw_payload_allowed"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["external_ack_means_person_located"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["evidence_level_elevation_by_export"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))
        cot = cot_bridge()
        cot["silence_means_absence"] = True
        self.assertTrue(errors("cot-bridge-profile", cot))

        for item, _path in addon_schemas:
            validator = Draft202012Validator(
                item, registry=registry, format_checker=FormatChecker()
            )
            for example in item["examples"]:
                self.assertEqual(list(validator.iter_errors(example)), [])


if __name__ == "__main__":
    unittest.main()
