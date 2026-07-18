from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md"
POLICY = ROOT / "config/open-spec/governance.json"
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/reference-capability-profiles.json"
CLAIM_SCHEMA = ROOT / "schemas/open-spec/evidence-claim.schema.json"
DISPOSITION = ROOT / "docs/governance/p1a-01-spec-disposition.json"
RESIDUALS = ROOT / "docs/governance/open-spec-residuals.json"
CATEGORIES = {
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


class OpenSpecTrackTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_open_spec_gate_is_registered(self) -> None:
        result = self.run_verify("open-spec", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--policy", result.stdout)
        self.assertIn("--profiles", result.stdout)
        self.assertIn("--claim-schema", result.stdout)
        self.assertIn("--disposition", result.stdout)

    def test_spec_plan_is_primary_and_accepts_through_os_07(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("Autoridad principal: Open Spec", source)
        self.assertIn("7 / 8", source)
        self.assertIn("OS-01 — aceptada", source)
        self.assertIn("OS-02 — aceptada", source)
        self.assertIn("OS-03 — aceptada", source)
        self.assertIn("OS-04 — aceptada", source)
        self.assertIn("OS-05 — aceptada", source)
        self.assertIn("OS-06 — aceptada", source)
        self.assertIn("OS-07 — aceptada", source)
        self.assertIn("OS-08 — no iniciada", source)
        self.assertIn("P1a es un carril opcional", source)

    def test_policy_separates_publication_from_physical_claims(self) -> None:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(value["main_lane"], "open_spec")
        self.assertEqual(
            value["progress"],
            {"accepted_tasks": 7, "total_tasks": 8, "percent": 87.5},
        )
        self.assertFalse(value["publication"]["requires_owned_hardware"])
        self.assertFalse(value["publication"]["requires_physical_evidence"])
        self.assertTrue(value["physical_claims"]["require_evidence_pack"])
        self.assertEqual(
            value["physical_validation_lane"]["progress"]["accepted_tasks"], 0
        )
        tasks = value["tasks"]
        self.assertEqual(
            [task["id"] for task in tasks], [f"OS-{index:02d}" for index in range(1, 9)]
        )
        self.assertTrue(all(task["status"] == "accepted" for task in tasks[:7]))
        self.assertTrue(all(task["status"] == "not_started" for task in tasks[7:]))

    def test_reference_profiles_are_open_and_hardware_agnostic(self) -> None:
        value = json.loads(PROFILES.read_text(encoding="utf-8"))
        profiles = value["profiles"]
        self.assertEqual({profile["category"] for profile in profiles}, CATEGORIES)
        self.assertEqual(len(profiles), 9)
        for profile in profiles:
            self.assertFalse(profile["hardware_required_for_spec"])
            self.assertTrue(profile["alternatives_allowed"])
            self.assertEqual(profile["default_evidence_level"], "unverified")
            self.assertTrue(profile["minimum_capabilities"])
            self.assertTrue(profile["reference_candidates"])
            self.assertTrue(profile["acceptance_criteria"])

    def test_evidence_claim_contract_is_normative_and_does_not_promote_spec_only(
        self,
    ) -> None:
        schema = json.loads(CLAIM_SCHEMA.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        level = schema["properties"]["evidence_level"]
        self.assertEqual(
            level["enum"],
            [
                "unverified",
                "specified",
                "simulated",
                "lab_validated",
                "field_validated",
            ],
        )
        self.assertIn("physical_evidence", schema["properties"])
        self.assertFalse(schema["additionalProperties"])

    def test_prior_physical_blocker_is_preserved_but_not_a_spec_blocker(self) -> None:
        value = json.loads(DISPOSITION.read_text(encoding="utf-8"))
        self.assertEqual(value["decision"], "preserved_as_optional_validation_lane")
        self.assertFalse(value["blocks_open_spec"])
        self.assertEqual(
            value["physical_validation_status"], "blocked_external_evidence"
        )
        for path in value["preserved_artifacts"]:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_open_spec_residuals_have_owner_gate_and_nonblocking_disposition(
        self,
    ) -> None:
        value = json.loads(RESIDUALS.read_text(encoding="utf-8"))
        self.assertEqual(value["lane"], "open_spec")
        self.assertGreaterEqual(len(value["residuals"]), 3)
        for row in value["residuals"]:
            self.assertIn(row["state"], {"controlled", "planned"})
            self.assertFalse(row["blocks_publication"])
            self.assertTrue(row["owner"])
            self.assertTrue(row["gate_or_task"])
            self.assertTrue(row["stop_condition"])

    def test_gate_accepts_spec_without_physical_assets(self) -> None:
        result = self.run_verify("open-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 7)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["reference_profiles"], 9)
        self.assertEqual(summary["physical_validation_tasks_accepted"], 0)
        self.assertFalse(summary["physical_evidence_blocks_publication"])

    def test_gate_rejects_policy_that_makes_hardware_a_publication_requirement(
        self,
    ) -> None:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        value["publication"]["requires_physical_evidence"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            policy = Path(temporary) / "governance.json"
            policy.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify("open-spec", "--policy", str(policy))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(
            "physical evidence cannot block open-spec publication", result.stderr
        )

    def test_board_readme_and_ci_use_spec_first_authority(self) -> None:
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn(str(PLAN.relative_to(ROOT)), board)
        self.assertIn("Open Spec `7 / 8`", board)
        self.assertIn("P1a física `0 / 8`", board)
        self.assertIn("OS-06", board)
        self.assertIn("spec-first", readme)
        self.assertIn("openbrec.verify open-spec", readme)
        self.assertIn("  open-spec:", workflow)
        job = workflow.split("  open-spec:", 1)[1]
        self.assertIn("openbrec.verify open-spec", job)
        self.assertIn("evidence/open-spec/os-01", job)


if __name__ == "__main__":
    unittest.main()
