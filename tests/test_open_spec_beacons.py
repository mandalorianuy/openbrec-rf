from __future__ import annotations

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
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/beacon-capability-profiles.json"
EXTENSION_SCHEMA = ROOT / "schemas/open-spec/beacon-modality-extension.schema.json"
DATASET_SCHEMA = ROOT / "schemas/open-spec/beacon-dataset-manifest.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/beacons/conformance-examples.json"
RESIDUALS = ROOT / "docs/governance/open-spec-beacon-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-05/os-05-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-05/acceptance.json"

CORE_MODALITIES = {
    "acoustic_features",
    "movement_change",
    "thermal_low_resolution",
}
PROHIBITED_CLAIMS = {
    "person_present",
    "person_absent",
    "identity",
    "biometric_match",
    "medical_diagnosis",
    "victim_count",
}


class OpenSpecBeaconTests(unittest.TestCase):
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

    def test_gate_is_registered_with_normative_inputs(self) -> None:
        result = self.run_verify("open-spec-beacons", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--profiles",
            "--extension-schema",
            "--dataset-schema",
            "--fixtures",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_os_05_is_accepted_without_starting_os_06(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("6 / 8", source)
        self.assertIn("OS-05 — aceptada", source)
        self.assertIn("OS-06 — aceptada", source)
        self.assertIn("OS-07 — no iniciada", source)
        policy = self.load_json(POLICY)
        self.assertEqual(
            policy["progress"],
            {"accepted_tasks": 6, "total_tasks": 8, "percent": 75.0},
        )
        tasks = policy["tasks"]
        self.assertEqual([task["status"] for task in tasks[:6]], ["accepted"] * 6)
        self.assertTrue(all(task["status"] == "not_started" for task in tasks[6:]))

    def test_profiles_require_one_modality_and_keep_three_optional(self) -> None:
        value = self.load_json(PROFILES)
        boundary = value["open_boundary"]
        self.assertEqual(boundary["minimum_modalities"], 1)
        self.assertEqual(boundary["reference_modalities"], 3)
        self.assertFalse(boundary["trimodal_required"])
        self.assertFalse(boundary["requires_owned_hardware"])
        self.assertFalse(boundary["physical_detection_blocks_spec"])
        self.assertTrue(boundary["modalities_are_replaceable_adapters"])
        profiles = value["core_modality_profiles"]
        self.assertEqual({row["modality"] for row in profiles}, CORE_MODALITIES)
        for row in profiles:
            self.assertFalse(row["required_for_spec"])
            self.assertTrue(row["alternatives_allowed"])
            self.assertTrue(row["observations"])
            self.assertTrue(row["limitations"])

    def test_observation_chain_reuses_core_and_never_promotes_silence(self) -> None:
        policy = self.load_json(PROFILES)["observation_policy"]
        self.assertEqual(
            policy["normative_chain"],
            "Observation -> Evidence -> FusionResult -> OperatorAnnotation",
        )
        self.assertFalse(policy["parallel_fact_chain_allowed"])
        self.assertFalse(policy["silence_means_absence"])
        self.assertFalse(policy["missing_sensor_means_absence"])
        self.assertFalse(policy["single_candidate_means_presence"])
        self.assertTrue(policy["unknown_and_abstention_required"])
        self.assertTrue(policy["missing_capabilities_visible"])

    def test_modality_semantics_prohibit_identity_presence_and_diagnosis(self) -> None:
        profiles = self.load_json(PROFILES)["core_modality_profiles"]
        encoded = json.dumps(profiles, sort_keys=True)
        for claim in PROHIBITED_CLAIMS:
            self.assertNotIn(f'"{claim}"', encoded)
        acoustic = next(
            row for row in profiles if row["modality"] == "acoustic_features"
        )
        self.assertEqual(acoustic["normal_mode"], "local_features_only")
        self.assertFalse(acoustic["continuous_audio_storage"])
        self.assertFalse(acoustic["speech_to_text"])
        self.assertFalse(acoustic["voiceprint"])
        movement = next(row for row in profiles if row["modality"] == "movement_change")
        self.assertFalse(movement["occupancy_claim"])
        self.assertFalse(movement["immobility_absence_claim"])
        thermal = next(
            row for row in profiles if row["modality"] == "thermal_low_resolution"
        )
        self.assertFalse(thermal["identifiable_image"])
        self.assertFalse(thermal["medical_temperature"])

    def test_raw_capture_is_local_authorized_bounded_and_reviewable(self) -> None:
        capture = self.load_json(PROFILES)["raw_capture_policy"]
        self.assertEqual(capture["default"], "disabled")
        self.assertTrue(capture["local_only_by_default"])
        self.assertTrue(capture["explicit_authorization_required"])
        self.assertTrue(capture["encryption_required"])
        self.assertTrue(capture["bounded_duration_required"])
        self.assertTrue(capture["audit_required"])
        self.assertTrue(capture["life_safety_hold_before_deletion"])
        self.assertFalse(capture["automatic_federation"])
        self.assertFalse(capture["live_stream_allowed_initially"])

    def test_extension_contract_is_closed_reviewed_and_claim_isolated(self) -> None:
        schema = self.load_json(EXTENSION_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        required = set(schema["required"])
        self.assertTrue(
            {
                "extension_id",
                "modality_namespace",
                "observation_schema_ref",
                "privacy_review_ref",
                "threat_review_ref",
                "dataset_manifest_refs",
                "capabilities_absent",
                "limitations",
            }.issubset(required)
        )
        fixtures = self.load_json(FIXTURES)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        extensions = fixtures["extensions"]
        self.assertGreaterEqual(len(extensions), 1)
        for index, row in enumerate(extensions):
            errors = list(validator.iter_errors(row))
            self.assertEqual(errors, [], f"extensions[{index}]: {errors}")
            self.assertFalse(row["inherits_presence_claims"])

    def test_dataset_manifests_are_reusable_but_do_not_claim_representativeness(
        self,
    ) -> None:
        schema = self.load_json(DATASET_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        fixtures = self.load_json(FIXTURES)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifests = fixtures["dataset_manifests"]
        self.assertGreaterEqual(len(manifests), 2)
        for index, row in enumerate(manifests):
            errors = list(validator.iter_errors(row))
            self.assertEqual(errors, [], f"dataset_manifests[{index}]: {errors}")
            self.assertTrue(row["license"])
            self.assertTrue(row["provenance"])
            self.assertTrue(row["negative_results_included"])
            self.assertTrue(row["omitted_environment_classes"])
            self.assertFalse(row["representativeness_claimed"])
            self.assertFalse(row["physical_performance_claimed"])

    def test_fixtures_cover_single_trimodal_and_extension_paths(self) -> None:
        fixtures = self.load_json(FIXTURES)
        deployments = fixtures["deployment_examples"]
        self.assertEqual(
            {row["composition"] for row in deployments},
            {"single_modality", "trimodal_reference", "extension_modality"},
        )
        single = next(
            row for row in deployments if row["composition"] == "single_modality"
        )
        tri = next(
            row for row in deployments if row["composition"] == "trimodal_reference"
        )
        self.assertEqual(len(single["modalities"]), 1)
        self.assertEqual(set(tri["modalities"]), CORE_MODALITIES)
        self.assertFalse(tri["triangulation_available"])
        self.assertFalse(tri["presence_confirmation_available"])

    def test_replay_is_deterministic_abstaining_and_capability_driven(self) -> None:
        result = self.run_verify("open-spec-beacons")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["replay_orders"], 10)
        self.assertEqual(summary["replay_hashes"], 1)
        self.assertEqual(summary["automatic_presence_confirmations"], 0)
        self.assertEqual(summary["absence_inferences"], 0)
        self.assertGreaterEqual(summary["abstained_cases"], 3)
        self.assertEqual(summary["shared_cause_counted_independent"], 0)
        self.assertEqual(summary["raw_material_fact_promotions"], 0)
        self.assertGreaterEqual(summary["missing_capabilities_visible"], 1)

    def test_gate_rejects_mandatory_trimodal_hardware(self) -> None:
        profiles = self.load_json(PROFILES)
        profiles["open_boundary"]["trimodal_required"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            result = self.run_verify("open-spec-beacons", "--profiles", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tri-modal reference cannot be mandatory", result.stderr)

    def test_gate_rejects_presence_claims(self) -> None:
        fixtures = self.load_json(FIXTURES)
        fixtures["replay_cases"][0]["expected_output"] = "person_present"
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "fixtures.json"
            path.write_text(json.dumps(fixtures), encoding="utf-8")
            result = self.run_verify("open-spec-beacons", "--fixtures", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("prohibited beacon claim", result.stderr)

    def test_residuals_are_governed_and_nonblocking(self) -> None:
        register = self.load_json(RESIDUALS)
        self.assertEqual(register["task"], "OS-05")
        self.assertGreaterEqual(len(register["residuals"]), 10)
        for row in register["residuals"]:
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

    def test_gate_reports_os_05_acceptance_without_physical_claims(self) -> None:
        result = self.run_verify("open-spec-beacons")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 6)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["core_modality_profiles"], 3)
        self.assertEqual(summary["minimum_modalities"], 1)
        self.assertEqual(summary["reference_modalities"], 3)
        self.assertFalse(summary["physical_detection_blocks_publication"])
        self.assertEqual(summary["next_task"], "OS-07")
        self.assertFalse(summary["next_task_started"])

    def test_board_readme_and_ci_publish_os_05_gate(self) -> None:
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec `6 / 8`", board)
        self.assertIn("[x] `OS-05`", board)
        self.assertIn("OS-06", board)
        self.assertIn("openbrec.verify open-spec-beacons", readme)
        self.assertIn("beacon-capability-profiles.json", readme)
        self.assertIn("  open-spec-beacons:", workflow)
        job = workflow.split("  open-spec-beacons:", 1)[1]
        self.assertIn("tests.test_open_spec_beacons", job)
        self.assertIn("openbrec.verify open-spec-beacons", job)
        self.assertIn("evidence/open-spec/os-05", job)

    def test_os_05_acceptance_is_scoped_and_does_not_start_os_06(self) -> None:
        acceptance = self.load_json(ACCEPTANCE)
        receipt = self.load_json(RECEIPT)
        self.assertEqual(acceptance["task"], "OS-05")
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
            {"accepted_tasks": 5, "total_tasks": 8, "percent": 62.5},
        )
        self.assertFalse(acceptance["physical_validation_progress"]["blocks_open_spec"])
        self.assertEqual(acceptance["next_task"], "OS-06")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
