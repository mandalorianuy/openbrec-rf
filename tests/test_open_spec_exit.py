from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md"
POLICY = ROOT / "config/open-spec/governance.json"
KIT = ROOT / "specs/openbrec/1.0.0-draft.1/conformance-kit.json"
SUBMISSION_SCHEMA = ROOT / "schemas/open-spec/conformance-submission.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/conformance/conformance-examples.json"
MATRIX = ROOT / "docs/decision-matrices/open-spec-functionality-matrix.json"
PUBLICATION = ROOT / "docs/open-spec/README.md"
RESIDUALS = ROOT / "docs/governance/open-spec-exit-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-08/os-08-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-08/acceptance.json"

ADDONS = {
    "energy",
    "machine_telemetry",
    "human_messaging",
    "beacon_sensing",
    "recursive_federation",
}
CONTRIBUTION_TYPES = {
    "core_conformance",
    "addon_profile",
    "reuse_adapter",
    "reference_build",
    "evidence_pack",
    "extension",
}
DECISIONS = {"build", "adapt", "evaluate", "defer", "prohibited"}


class OpenSpecExitTests(unittest.TestCase):
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

    def test_gate_is_registered_with_every_normative_input(self) -> None:
        result = self.run_verify("open-spec-exit", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--kit",
            "--submission-schema",
            "--fixtures",
            "--matrix",
            "--publication",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_open_spec_track_is_complete_without_starting_physical_validation(
        self,
    ) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("Estado: cerrado", source)
        self.assertIn("8 / 8", source)
        self.assertIn("OS-08 — aceptada", source)
        self.assertIn("P1a-01 no fue iniciada", source)
        policy = self.load_json(POLICY)
        self.assertEqual(
            policy["progress"],
            {"accepted_tasks": 8, "total_tasks": 8, "percent": 100.0},
        )
        self.assertEqual([task["status"] for task in policy["tasks"]], ["accepted"] * 8)
        self.assertEqual(policy["tasks"][7]["gate"], "open-spec-exit")
        self.assertEqual(
            policy["physical_validation_lane"]["progress"]["accepted_tasks"], 0
        )

    def test_kit_aggregates_all_prior_open_spec_gates_and_contribution_types(
        self,
    ) -> None:
        kit = self.load_json(KIT)
        self.assertEqual(kit["spec_version"], "1.0.0-draft.1")
        self.assertEqual(
            [row["task"] for row in kit["normative_gates"]],
            [f"OS-{index:02d}" for index in range(1, 8)],
        )
        self.assertEqual(
            {row["contribution_type"] for row in kit["conformance_classes"]},
            CONTRIBUTION_TYPES,
        )
        for row in kit["normative_gates"]:
            self.assertTrue(row["command"])
            self.assertTrue(row["normative_inputs"])
            self.assertTrue(row["proves"])
            self.assertTrue(row["does_not_prove"])

    def test_claim_ladder_never_promotes_physical_evidence_from_conformance(
        self,
    ) -> None:
        ladder = self.load_json(KIT)["claim_ladder"]
        self.assertEqual(
            [row["level"] for row in ladder],
            [
                "unverified",
                "specified",
                "simulated",
                "lab_validated",
                "field_validated",
            ],
        )
        by_level = {row["level"]: row for row in ladder}
        self.assertFalse(by_level["specified"]["physical_evidence_required"])
        self.assertFalse(by_level["simulated"]["physical_evidence_required"])
        self.assertTrue(by_level["lab_validated"]["physical_evidence_required"])
        self.assertTrue(by_level["field_validated"]["physical_evidence_required"])
        self.assertTrue(
            self.load_json(KIT)["publication_boundary"][
                "conformance_never_implies_field_readiness"
            ]
        )

    def test_submission_schema_is_closed_and_examples_conform(self) -> None:
        schema = self.load_json(SUBMISSION_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        examples = self.load_json(FIXTURES)["submissions"]
        self.assertGreaterEqual(len(examples), 6)
        self.assertEqual(
            {row["contribution_type"] for row in examples}, CONTRIBUTION_TYPES
        )
        for index, row in enumerate(examples):
            self.assertEqual(
                list(validator.iter_errors(row)), [], f"submission {index}"
            )

    def test_physical_claims_require_exact_configuration_and_real_evidence(
        self,
    ) -> None:
        rules = self.load_json(KIT)["physical_evidence_rules"]
        for field in (
            "exact_hardware_and_firmware",
            "measurement_protocol",
            "raw_or_derived_results",
            "limitations_and_negative_results",
            "custody_and_responsible_actor",
            "jurisdiction_and_environment",
        ):
            self.assertTrue(rules[field])
        self.assertFalse(rules["reference_candidate_becomes_requirement"])
        self.assertFalse(rules["evidence_pack_blocks_open_spec"])
        self.assertEqual(rules["scope"], "exact_combination_only")

    def test_matrix_covers_every_addon_and_requested_decision_fields(self) -> None:
        matrix = self.load_json(MATRIX)
        self.assertIsNone(matrix["method"]["aggregate_score"])
        self.assertIsNone(matrix["method"]["global_winner"])
        rows = matrix["functionalities"]
        self.assertGreaterEqual(len(rows), 10)
        self.assertEqual({row["addon"] for row in rows}, ADDONS)
        required = {
            "id",
            "functionality",
            "addon",
            "brec_value",
            "available_evidence",
            "decoupled_alternative",
            "hardware",
            "privacy",
            "safety_gate",
            "effort",
            "acceptance_criteria",
            "decision",
            "residual_refs",
        }
        for row in rows:
            self.assertEqual(set(row), required)
            self.assertIn(row["brec_value"], {"V1", "V2", "V3", "V4", "V5"})
            self.assertIn(row["decision"], DECISIONS)
            self.assertIn(row["effort"], {"S", "M", "L", "XL"})
            self.assertTrue(row["acceptance_criteria"])
            self.assertTrue(row["decoupled_alternative"])

    def test_matrix_keeps_hardware_optional_and_life_safety_before_minimization(
        self,
    ) -> None:
        rows = self.load_json(MATRIX)["functionalities"]
        for row in rows:
            self.assertFalse(row["hardware"]["required_for_spec"])
            self.assertTrue(row["hardware"]["substitution_allowed"])
            self.assertTrue(row["privacy"]["life_safety_precedes_minimization"])
            self.assertTrue(row["privacy"]["controls"])
            self.assertTrue(row["safety_gate"]["stop_condition"])
        distress_rows = [row for row in rows if row["safety_gate"]["possible_distress"]]
        self.assertTrue(distress_rows)
        self.assertTrue(
            all(row["safety_gate"]["preserve_for_review"] for row in distress_rows)
        )

    def test_publication_is_open_versioned_reproducible_and_not_vendor_owned(
        self,
    ) -> None:
        publication = self.load_json(KIT)["publication"]
        self.assertEqual(publication["license"], "Apache-2.0")
        self.assertTrue(publication["offline_bundle"])
        self.assertTrue(publication["versioned_normative_paths"])
        self.assertTrue(publication["checksums_required"])
        self.assertFalse(publication["cloud_required"])
        self.assertFalse(publication["vendor_certification_program"])
        self.assertFalse(publication["paywall_allowed"])

    def test_community_process_is_append_only_and_preserves_negative_results(
        self,
    ) -> None:
        process = self.load_json(KIT)["community_process"]
        self.assertEqual(
            process["states"],
            [
                "draft",
                "submitted",
                "validated",
                "accepted",
                "rejected_with_record",
                "superseded",
            ],
        )
        self.assertTrue(process["review_decisions_append_only"])
        self.assertTrue(process["negative_results_preserved"])
        self.assertTrue(process["rejected_submissions_preserved"])
        self.assertFalse(process["silent_deletion_allowed"])
        self.assertTrue(process["security_privacy_safety_review_required"])

    def test_publication_documents_explain_use_contribution_and_claim_boundaries(
        self,
    ) -> None:
        index = PUBLICATION.read_text(encoding="utf-8").lower()
        for token in (
            "1.0.0-draft.1",
            "conformance.md",
            "community-evidence.md",
            "publishing.md",
            "apache-2.0",
            "no acredita",
        ):
            self.assertIn(token, index)
        for path in (
            ROOT / "docs/open-spec/CONFORMANCE.md",
            ROOT / "docs/open-spec/COMMUNITY-EVIDENCE.md",
            ROOT / "docs/open-spec/PUBLISHING.md",
        ):
            self.assertTrue(path.is_file(), str(path))

    def test_mutation_rejects_lab_validation_without_exact_evidence(self) -> None:
        from openbrec.open_spec_exit import run_open_spec_exit_gate

        fixtures = copy.deepcopy(self.load_json(FIXTURES))
        fixtures["submissions"][0]["claimed_evidence_level"] = "lab_validated"
        fixtures["submissions"][0]["exact_configuration"] = None
        fixtures["submissions"][0]["evidence_refs"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixtures.json"
            path.write_text(json.dumps(fixtures), encoding="utf-8")
            errors, _, _, _ = run_open_spec_exit_gate(
                ROOT,
                kit_path=KIT,
                submission_schema_path=SUBMISSION_SCHEMA,
                fixtures_path=path,
                matrix_path=MATRIX,
                publication_path=PUBLICATION,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("physical evidence" in error for error in errors))

    def test_mutation_rejects_a_global_winner(self) -> None:
        from openbrec.open_spec_exit import run_open_spec_exit_gate

        matrix = copy.deepcopy(self.load_json(MATRIX))
        matrix["method"]["global_winner"] = "meshtastic"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.json"
            path.write_text(json.dumps(matrix), encoding="utf-8")
            errors, _, _, _ = run_open_spec_exit_gate(
                ROOT,
                kit_path=KIT,
                submission_schema_path=SUBMISSION_SCHEMA,
                fixtures_path=FIXTURES,
                matrix_path=path,
                publication_path=PUBLICATION,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("global winner" in error for error in errors))

    def test_residuals_are_resolved_controlled_planned_or_evidence_required(
        self,
    ) -> None:
        value = self.load_json(RESIDUALS)
        self.assertEqual(value["task"], "OS-08")
        self.assertGreaterEqual(len(value["residuals"]), 12)
        for row in value["residuals"]:
            self.assertIn(
                row["state"],
                {"resolved", "controlled", "planned", "evidence_required"},
            )
            self.assertFalse(row["blocks_open_spec"])
            for field in (
                "owner",
                "risk",
                "disposition",
                "gate_or_task",
                "stop_condition",
            ):
                self.assertTrue(row[field])

    def test_summary_closes_open_spec_and_only_points_to_optional_p1a(self) -> None:
        result = self.run_verify("open-spec-exit")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 8)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertTrue(summary["open_spec_complete"])
        self.assertEqual(summary["matrix_addons"], 5)
        self.assertGreaterEqual(summary["matrix_functionalities"], 10)
        self.assertEqual(summary["next_task"], "P1a-01")
        self.assertEqual(summary["next_task_lane"], "optional_physical_validation")
        self.assertFalse(summary["next_task_started"])
        self.assertFalse(summary["physical_evidence_blocks_publication"])

    def test_readme_board_and_ci_publish_open_spec_exit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec está `8 / 8`", readme)
        self.assertIn("Open Spec `8 / 8`", board)
        self.assertIn("open-spec-exit:", workflow)
        self.assertIn("tests.test_open_spec_exit", workflow)
        self.assertIn("openbrec.verify open-spec-exit", workflow)

    def test_acceptance_references_a_clean_passing_receipt(self) -> None:
        receipt = self.load_json(RECEIPT)
        acceptance = self.load_json(ACCEPTANCE)
        self.assertEqual(receipt["result"], "passed")
        self.assertFalse(receipt["dirty"])
        self.assertEqual(acceptance["task"], "OS-08")
        self.assertEqual(acceptance["status"], "accepted")
        self.assertEqual(
            acceptance["receipt"]["sha256"],
            hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
        )
        self.assertEqual(acceptance["next_task_lane"], "optional_physical_validation")
        self.assertEqual(acceptance["next_task"], "P1a-01")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
