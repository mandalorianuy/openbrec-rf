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
    "energy-budget",
    "energy-capability",
    "energy-status",
    "federation-event",
    "federation-topology-event",
    "human-message",
    "human-message-event",
    "review-task-event",
    "terminal-capability",
    "transport-envelope",
    "transport-policy-decision",
    "transport-profile",
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
        self.assertEqual(output["summary"]["addon_schemas"], 18)
        self.assertEqual(output["summary"]["support_status"], "experimental")

    def test_addon_fixture_gate_reconciles_positive_and_negative_cases(self) -> None:
        output = self.assert_passed(self.run_verify("addon-fixtures"))
        self.assertEqual(output["scope"], "addon_schema_fixture_matrix")
        self.assertEqual(output["summary"]["schemas"], 18)
        self.assertEqual(output["summary"]["valid_fixtures"], 36)
        self.assertEqual(output["summary"]["invalid_fixtures"], 126)

    def test_generated_consumers_include_all_addon_contracts(self) -> None:
        output = self.assert_passed(self.run_verify("contracts-gen", "--check"))
        self.assertEqual(output["summary"]["addon_schemas"], 18)
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
        self.assertEqual(output["summary"]["addon_schemas"], 18)
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

        for item, _path in addon_schemas:
            validator = Draft202012Validator(
                item, registry=registry, format_checker=FormatChecker()
            )
            for example in item["examples"]:
                self.assertEqual(list(validator.iter_errors(example)), [])


if __name__ == "__main__":
    unittest.main()
