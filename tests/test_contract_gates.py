from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.contracts import load_core_schemas, schema_registry

REPO_ROOT = Path(__file__).resolve().parents[1]


class ContractGateTests(unittest.TestCase):
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

    def test_schema_gate_validates_complete_core_catalog(self) -> None:
        result = self.run_verify("schema")

        output = self.assert_passed(result)
        self.assertEqual(output["scope"], "metaschema_and_catalog")
        self.assertEqual(output["summary"]["core_schemas"], 18)

    def test_fixtures_gate_reconciles_positive_and_negative_cases(self) -> None:
        result = self.run_verify("fixtures")

        output = self.assert_passed(result)
        self.assertEqual(output["summary"]["schemas"], 18)
        self.assertGreaterEqual(output["summary"]["valid_fixtures"], 36)
        self.assertGreaterEqual(output["summary"]["invalid_fixtures"], 126)

    def test_schema_compat_gate_freezes_legacy_and_core_baselines(self) -> None:
        result = self.run_verify("schema-compat")

        output = self.assert_passed(result)
        self.assertEqual(output["scope"], "immutable_baseline")
        self.assertEqual(output["summary"]["legacy_schemas"], 6)
        self.assertEqual(output["summary"]["core_schemas"], 18)

    def test_contracts_generation_is_reproducible(self) -> None:
        result = self.run_verify("contracts-gen", "--check")

        output = self.assert_passed(result)
        self.assertEqual(output["scope"], "generated_consumers")
        self.assertEqual(output["summary"].get("typescript_checked"), True)
        python_models = REPO_ROOT / "packages/contracts/generated/python/models.py"
        typescript_models = (
            REPO_ROOT / "packages/contracts/generated/typescript/models.d.ts"
        )
        self.assertIn("generated", python_models.read_text(encoding="utf-8").lower())
        self.assertIn(
            "generated", typescript_models.read_text(encoding="utf-8").lower()
        )

    def test_initial_incident_allows_missing_deployment_id(self) -> None:
        schemas = load_core_schemas(REPO_ROOT)
        registry = schema_registry(schemas)
        schema = next(
            item for item, path in schemas if path.name == "domain-event.schema.json"
        )
        event = copy.deepcopy(schema["examples"][0])
        event.pop("deployment_id")

        errors = list(
            Draft202012Validator(
                schema, registry=registry, format_checker=FormatChecker()
            ).iter_errors(event)
        )

        self.assertEqual(errors, [])

    def test_contract_loader_rejects_catalog_path_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog_path = root / "schemas/core/catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(
                json.dumps({"entries": [{"path": "../outside.schema.json"}]}),
                encoding="utf-8",
            )

            try:
                load_core_schemas(root)
            except Exception as exc:
                self.assertIsInstance(exc, ValueError)
                self.assertIn("outside repository root", str(exc))
            else:
                self.fail("catalog path outside repository root was accepted")


if __name__ == "__main__":
    unittest.main()
