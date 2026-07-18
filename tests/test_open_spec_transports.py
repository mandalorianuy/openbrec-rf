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
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json"
DECISION_SCHEMA = ROOT / "schemas/open-spec/transport-decision.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/transports/decision-examples.json"
SOURCE_REVIEW = ROOT / "docs/research/2026-07-18-multi-bearer-source-review.json"
RESIDUALS = ROOT / "docs/governance/open-spec-transport-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-03/os-03-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-03/acceptance.json"

BEARERS = {
    "lorawan_private",
    "meshtastic",
    "meshcore",
    "reticulum_rnode",
    "carry_bundle",
}
REGULATORY_MODES = {
    "receive_only",
    "conducted_only",
    "jurisdiction_validated",
    "emergency_assumed_risk",
}


class OpenSpecTransportTests(unittest.TestCase):
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

    def test_gate_is_registered_with_all_normative_inputs(self) -> None:
        result = self.run_verify("open-spec-transports", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--profiles",
            "--decision-schema",
            "--fixtures",
            "--source-review",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_os_03_remains_accepted_after_os_05_closure(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("5 / 8", source)
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

    def test_five_profiles_are_open_and_have_no_global_winner(self) -> None:
        value = self.load_json(PROFILES)
        self.assertIsNone(value["selection_policy"]["global_winner"])
        self.assertFalse(value["open_boundary"]["requires_single_bearer"])
        self.assertFalse(value["open_boundary"]["requires_owned_hardware"])
        self.assertFalse(value["open_boundary"]["physical_rf_validation_blocks_spec"])
        profiles = value["profiles"]
        self.assertEqual({row["bearer"] for row in profiles}, BEARERS)
        for row in profiles:
            self.assertFalse(row["required_for_spec"])
            self.assertTrue(row["alternatives_allowed"])
            self.assertEqual(row["trust_boundary"], "untrusted_transport")
            self.assertTrue(row["selection_dimensions"])
            self.assertTrue(row["failure_modes"])

    def test_application_overlay_is_bearer_independent(self) -> None:
        overlay = self.load_json(PROFILES)["application_overlay"]
        self.assertEqual(overlay["envelope_authority"], "openbrec_application")
        self.assertTrue(overlay["signed_integrity"])
        self.assertTrue(overlay["stable_message_id_across_bearers"])
        self.assertTrue(overlay["deduplicate_before_semantic_acceptance"])
        self.assertTrue(overlay["anti_loop_required"])
        self.assertTrue(overlay["priority_assigned_before_bearer"])
        self.assertTrue(overlay["per_path_receipts"])
        self.assertFalse(overlay["raw_frame_bridge_allowed"])
        self.assertFalse(overlay["transport_ack_is_semantic_delivery"])
        self.assertFalse(overlay["transport_ack_is_operator_acceptance"])

    def test_protocol_specific_boundaries_match_reviewed_state_of_art(self) -> None:
        profiles = {row["bearer"]: row for row in self.load_json(PROFILES)["profiles"]}
        meshtastic = profiles["meshtastic"]["protocol_constraints"]
        self.assertIn("managed_flooding", meshtastic["routing_modes"])
        self.assertIn("direct_next_hop", meshtastic["routing_modes"])
        self.assertTrue(meshtastic["known_default_channel_key_forbidden"])
        self.assertFalse(meshtastic["channel_authenticity_trusted"])

        meshcore = profiles["meshcore"]["protocol_constraints"]
        self.assertEqual(set(meshcore["roles"]), {"companion", "repeater"})
        self.assertTrue(meshcore["flood_discovery_then_explicit_path"])
        self.assertTrue(meshcore["path_width_version_compatibility_required"])

        reticulum = profiles["reticulum_rnode"]["protocol_constraints"]
        self.assertTrue(reticulum["heterogeneous_interfaces"])
        self.assertTrue(reticulum["application_priority_precedes_interface"])

        lorawan = profiles["lorawan_private"]["protocol_constraints"]
        self.assertEqual(lorawan["activation"], "OTAA")
        self.assertTrue(lorawan["unique_root_keys"])
        self.assertTrue(lorawan["persistent_nonces_and_frame_counters"])
        self.assertTrue(lorawan["network_server_dependency_declared"])

        carry = profiles["carry_bundle"]["protocol_constraints"]
        self.assertTrue(carry["store_carry_forward"])
        self.assertTrue(carry["expiry_deduplication_and_custody_required"])
        self.assertFalse(carry["bpv7_conformance_implied"])

    def test_source_review_uses_primary_sources_and_requires_repinning(self) -> None:
        review = self.load_json(SOURCE_REVIEW)
        self.assertEqual(review["reviewed_at"], "2026-07-18")
        self.assertEqual(
            review["version_policy"], "pin_per_implementation_and_rereview"
        )
        sources = review["sources"]
        self.assertGreaterEqual(len(sources), 7)
        self.assertEqual(
            {row["technology"] for row in sources},
            {"meshtastic", "meshcore", "reticulum", "lorawan", "carry_bundle"},
        )
        for row in sources:
            self.assertTrue(row["official_url"].startswith("https://"))
            self.assertTrue(row["observations"])
            self.assertTrue(row["implementation_action"])
            self.assertFalse(row["proves_field_performance"])

    def test_decision_schema_is_closed_and_fixtures_cover_all_bearers_and_modes(
        self,
    ) -> None:
        schema = self.load_json(DECISION_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        examples = self.load_json(FIXTURES)["examples"]
        self.assertGreaterEqual(len(examples), 5)
        selected: set[str] = set()
        modes: set[str] = set()
        for index, example in enumerate(examples):
            errors = sorted(
                validator.iter_errors(example), key=lambda error: list(error.path)
            )
            self.assertEqual(
                errors,
                [],
                f"examples[{index}]: " + "; ".join(e.message for e in errors),
            )
            selected.add(example["selected_bearer"])
            modes.add(example["regulatory_mode"])
            self.assertIn(example["evidence_level"], {"specified", "simulated"})
            self.assertTrue(example["rejected_alternatives"])
            self.assertTrue(example["known_gaps"])
        self.assertEqual(selected, BEARERS)
        self.assertEqual(modes, REGULATORY_MODES)

    def test_emergency_assumed_risk_requires_a_bounded_expiring_decision(self) -> None:
        schema = self.load_json(DECISION_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        emergency = next(
            row
            for row in self.load_json(FIXTURES)["examples"]
            if row["regulatory_mode"] == "emergency_assumed_risk"
        )
        required = {
            "jurisdiction",
            "frequency_or_band",
            "tx_power_and_eirp",
            "antenna",
            "airtime_budget",
            "geography",
            "responsible_actor",
            "reason",
            "starts_at",
            "expires_at",
            "monitoring",
            "stop_condition",
            "kill_switch",
            "dual_authorization",
        }
        self.assertEqual(set(emergency["assumed_risk_decision"]), required)
        broken = json.loads(json.dumps(emergency))
        del broken["assumed_risk_decision"]["expires_at"]
        self.assertTrue(list(validator.iter_errors(broken)))

    def test_gate_rejects_a_universal_winner(self) -> None:
        profiles = self.load_json(PROFILES)
        profiles["selection_policy"]["global_winner"] = "meshtastic"
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            result = self.run_verify("open-spec-transports", "--profiles", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("universal transport winner", result.stderr)

    def test_residuals_are_resolved_controlled_or_planned(self) -> None:
        register = self.load_json(RESIDUALS)
        self.assertEqual(register["task"], "OS-03")
        self.assertGreaterEqual(len(register["residuals"]), 9)
        for row in register["residuals"]:
            self.assertIn(
                row["state"], {"resolved", "controlled", "planned", "evidence_required"}
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

    def test_gate_accepts_profiles_without_physical_assets(self) -> None:
        result = self.run_verify("open-spec-transports")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 5)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["bearer_profiles"], 5)
        self.assertEqual(summary["conforming_examples"], 5)
        self.assertEqual(summary["source_records"], 7)
        self.assertFalse(summary["global_winner_selected"])
        self.assertFalse(summary["physical_rf_validation_blocks_publication"])
        self.assertEqual(summary["next_task"], "OS-06")
        self.assertFalse(summary["next_task_started"])

    def test_board_readme_and_ci_publish_os_03_gate(self) -> None:
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec `5 / 8`", board)
        self.assertIn("[x] `OS-03`", board)
        self.assertIn("OS-06", board)
        self.assertIn("openbrec.verify open-spec-transports", readme)
        self.assertIn("multi-bearer-transport-profiles.json", readme)
        self.assertIn("  open-spec-transports:", workflow)
        job = workflow.split("  open-spec-transports:", 1)[1]
        self.assertIn("tests.test_open_spec_transports", job)
        self.assertIn("openbrec.verify open-spec-transports", job)
        self.assertIn("evidence/open-spec/os-03", job)

    def test_os_03_acceptance_is_scoped_and_does_not_start_os_04(self) -> None:
        acceptance = self.load_json(ACCEPTANCE)
        receipt = self.load_json(RECEIPT)
        self.assertEqual(acceptance["task"], "OS-03")
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
            {"accepted_tasks": 3, "total_tasks": 8, "percent": 37.5},
        )
        self.assertFalse(acceptance["physical_validation_progress"]["blocks_open_spec"])
        self.assertEqual(acceptance["next_task"], "OS-04")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
