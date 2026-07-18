from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md"
POLICY = ROOT / "config/open-spec/governance.json"
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json"
ARCHITECTURE_SCHEMA = ROOT / "schemas/open-spec/energy-architecture.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/energy/architecture-examples.json"
RESIDUALS = ROOT / "docs/governance/open-spec-energy-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-02/os-02-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-02/acceptance.json"

ROLE_CATEGORIES = {
    "lorawan_gateway",
    "lorawan_endpoint",
    "meshtastic_node",
    "meshcore_node",
    "rnode",
    "offline_terminal",
    "trimodal_beacon",
    "energy_storage",
    "wired_cell_gateway",
}
TOPOLOGIES = {
    "component_local",
    "shared_site_hub",
    "hybrid_site_component",
    "logistics_replacement",
}
SOURCE_TYPES = {
    "storage",
    "portable_station",
    "replaceable_battery",
    "solar",
    "generator",
    "grid",
    "vehicle_dc",
    "manual_replacement",
}


class OpenSpecEnergyTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def load_json(self, path: Path) -> dict[str, object]:
        self.assertTrue(path.is_file(), f"missing normative artifact: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_energy_gate_is_registered_with_normative_inputs(self) -> None:
        result = self.run_verify("open-spec-energy", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--profiles",
            "--architecture-schema",
            "--fixtures",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_os_02_remains_accepted_after_os_05_closure(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("5 / 8", source)
        self.assertIn("OS-02 — aceptada", source)
        self.assertIn("OS-03 — aceptada", source)
        self.assertIn("OS-04 — aceptada", source)
        self.assertIn("OS-05 — aceptada", source)
        self.assertIn("OS-06 — no iniciada", source)
        policy = self.load_json(POLICY)
        self.assertEqual(
            policy["progress"],
            {"accepted_tasks": 5, "total_tasks": 8, "percent": 62.5},
        )
        tasks = policy["tasks"]
        self.assertEqual([task["status"] for task in tasks[:5]], ["accepted"] * 5)
        self.assertTrue(all(task["status"] == "not_started" for task in tasks[5:]))

    def test_energy_profiles_keep_solar_hardware_and_topology_optional(self) -> None:
        value = self.load_json(PROFILES)
        boundary = value["open_boundary"]
        self.assertFalse(boundary["requires_owned_hardware"])
        self.assertFalse(boundary["requires_solar"])
        self.assertFalse(boundary["requires_single_architecture"])
        self.assertFalse(boundary["physical_validation_blocks_spec"])
        self.assertFalse(boundary["perpetual_claim_allowed"])
        architectures = value["architectures"]
        self.assertEqual({row["topology"] for row in architectures}, TOPOLOGIES)
        for row in architectures:
            self.assertFalse(row["required_for_spec"])
            self.assertTrue(row["alternatives_allowed"])
            self.assertTrue(row["minimum_contracts"])
            self.assertTrue(row["alternatives"])

    def test_all_roles_and_source_adapters_are_openly_covered(self) -> None:
        value = self.load_json(PROFILES)
        mappings = value["role_mappings"]
        self.assertEqual({row["category"] for row in mappings}, ROLE_CATEGORIES)
        for row in mappings:
            self.assertTrue(row["allowed_architectures"])
            self.assertIn("L0_LIFE_SAFETY", row["critical_load_classes"])
            self.assertTrue(row["degradable_load_classes"])
            self.assertTrue(row["supply_alternatives"])
        adapters = value["source_adapters"]
        self.assertEqual({row["source_type"] for row in adapters}, SOURCE_TYPES)
        for row in adapters:
            self.assertFalse(row["required_for_spec"])
            self.assertTrue(row["safety_controls"])
            self.assertTrue(row["evidence_requirements"])

    def test_claims_are_bounded_and_life_safety_degrades_last(self) -> None:
        value = self.load_json(PROFILES)
        self.assertNotIn("indefinite", json.dumps(value).lower())
        self.assertEqual(
            value["claim_policy"]["allowed_claim_types"],
            [
                "unknown",
                "bounded_runtime",
                "storage_only_window",
                "sustainable_under_profile",
            ],
        )
        self.assertEqual(
            value["degradation_policy"]["shed_order"],
            ["L3_DEFERRABLE", "L2_MISSION_SUPPORT", "L1_MISSION_CRITICAL"],
        )
        self.assertTrue(
            value["degradation_policy"]["preserve_l0_until_hardware_cutoff"]
        )
        self.assertTrue(value["degradation_policy"]["hardware_safety_overrides_l0"])

    def test_architecture_schema_is_normative_and_examples_conform(self) -> None:
        schema = self.load_json(ARCHITECTURE_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        fixtures = self.load_json(FIXTURES)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        examples = fixtures["examples"]
        self.assertEqual(len(examples), 4)
        for example in examples:
            errors = sorted(
                validator.iter_errors(example), key=lambda error: list(error.path)
            )
            self.assertEqual(errors, [], "\n".join(error.message for error in errors))
            self.assertIn(example["evidence_level"], {"specified", "simulated"})
            self.assertNotIn("indefinite", json.dumps(example).lower())

    def test_examples_cover_component_central_hybrid_and_no_solar_paths(self) -> None:
        fixtures = self.load_json(FIXTURES)
        examples = fixtures["examples"]
        self.assertEqual({row["topology"] for row in examples}, TOPOLOGIES)
        self.assertEqual(
            {row["solar_mode"] for row in examples},
            {"none", "central", "per_component", "hybrid"},
        )
        for row in examples:
            budget = row["modeled_budget"]
            required = (budget["critical_load_Wh"] + budget["reserves_Wh"]) * budget[
                "margin_factor"
            ]
            self.assertEqual(
                budget["storage_only_pass"],
                budget["usable_storage_Wh"] >= required,
            )
            self.assertNotIn(
                budget["auxiliary_generation_Wh"],
                [budget["usable_storage_Wh"], budget["critical_load_Wh"]],
            )

    def test_gate_rejects_mandatory_solar(self) -> None:
        value = self.load_json(PROFILES)
        value["open_boundary"]["requires_solar"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            profiles = Path(directory) / "profiles.json"
            profiles.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify("open-spec-energy", "--profiles", str(profiles))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("solar cannot be mandatory", result.stderr)

    def test_energy_residuals_have_owner_gate_and_disposition(self) -> None:
        value = self.load_json(RESIDUALS)
        self.assertEqual(value["task"], "OS-02")
        self.assertGreaterEqual(len(value["residuals"]), 6)
        for row in value["residuals"]:
            self.assertIn(row["state"], {"controlled", "planned", "evidence_required"})
            self.assertFalse(row["blocks_open_spec"])
            for field in ("owner", "risk", "gate_or_task", "stop_condition"):
                self.assertTrue(row[field])

    def test_gate_accepts_open_energy_contract_without_physical_assets(self) -> None:
        result = self.run_verify("open-spec-energy")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 5)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["architectures"], 4)
        self.assertEqual(summary["role_mappings"], 9)
        self.assertEqual(summary["source_adapters"], 8)
        self.assertEqual(summary["conforming_examples"], 4)
        self.assertFalse(summary["physical_evidence_blocks_publication"])
        self.assertEqual(summary["next_task"], "OS-06")
        self.assertFalse(summary["next_task_started"])

    def test_board_readme_and_ci_publish_os_02_gate(self) -> None:
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec `5 / 8`", board)
        self.assertIn("[x] `OS-02`", board)
        self.assertIn("OS-06", board)
        self.assertIn("openbrec.verify open-spec-energy", readme)
        self.assertIn("energy-architecture-profiles.json", readme)
        self.assertIn("  open-spec-energy:", workflow)
        job = workflow.split("  open-spec-energy:", 1)[1]
        self.assertIn("tests.test_open_spec_energy", job)
        self.assertIn("openbrec.verify open-spec-energy", job)
        self.assertIn("evidence/open-spec/os-02", job)

    def test_os_02_acceptance_is_scoped_and_does_not_start_os_03(self) -> None:
        acceptance = self.load_json(ACCEPTANCE)
        receipt = self.load_json(RECEIPT)
        self.assertEqual(acceptance["task"], "OS-02")
        self.assertEqual(acceptance["status"], "accepted")
        self.assertEqual(acceptance["subject_git_sha"], receipt["git_sha"])
        self.assertEqual(acceptance["receipt"]["result"], "passed")
        self.assertFalse(acceptance["receipt"]["dirty"])
        self.assertEqual(
            acceptance["receipt"]["sha256"],
            hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            acceptance["open_spec_progress"],
            {"accepted_tasks": 2, "total_tasks": 8, "percent": 25.0},
        )
        self.assertFalse(acceptance["physical_validation_progress"]["blocks_open_spec"])
        self.assertEqual(acceptance["next_task"], "OS-03")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
