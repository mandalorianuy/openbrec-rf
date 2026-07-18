from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = REPO_ROOT / "fixtures/p0/beacons/deterministic-campaign.json"


class P007BeaconTests(unittest.TestCase):
    def run_verify(self, gate: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", gate],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_gate_passed(self, gate: str) -> dict[str, object]:
        result = self.run_verify(gate)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["result"], "passed")
        return output["summary"]

    def test_p0_07_gates_are_registered(self) -> None:
        for gate in ("beacon-replay", "beacon-adversarial", "retention-fault"):
            result = subprocess.run(
                [sys.executable, "-m", "openbrec.verify", gate, "--help"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_campaign_is_synthetic_provenanced_and_complete(self) -> None:
        self.assertTrue(CAMPAIGN.is_file())
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))

        self.assertEqual(campaign["campaign_version"], "1.0.0")
        self.assertEqual(campaign["claim_scope"], "deterministic_simulation_only")
        self.assertEqual(campaign["provenance"]["source_type"], "synthetic_generated")
        self.assertEqual(campaign["provenance"]["license"], "CC0-1.0")
        self.assertEqual(
            campaign["provenance"]["consent_basis"],
            "not_applicable_no_human_data",
        )
        self.assertTrue(campaign["omitted_environment_classes"])
        self.assertEqual(len(campaign["capabilities"]), 3)
        self.assertEqual(len(campaign["health"]), 3)
        self.assertGreaterEqual(len(campaign["placements"]), 4)
        self.assertGreaterEqual(len(campaign["observations"]), 12)
        self.assertGreaterEqual(len(campaign["fusion_cases"]), 5)
        self.assertGreaterEqual(len(campaign["hostile_cases"]), 10)
        self.assertGreaterEqual(len(campaign["retention_cases"]), 6)

    def test_beacon_replay_is_deterministic_safe_and_capability_driven(self) -> None:
        summary = self.assert_gate_passed("beacon-replay")

        self.assertEqual(summary["beacons"], 3)
        self.assertEqual(
            set(summary["modalities"]),
            {"acoustic_features", "pir_motion", "thermal_low_resolution"},
        )
        self.assertEqual(
            set(summary["fusion_outputs"]),
            {
                "single_modality_candidate",
                "corroborated_candidate",
                "sensor_artifact_likely",
                "insufficient_coverage",
                "unknown",
            },
        )
        self.assertEqual(
            summary["observations_denominator"], summary["observations_reconciled"]
        )
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["automatic_presence_confirmations"], 0)
        self.assertEqual(summary["absence_inferences"], 0)
        self.assertEqual(summary["raw_or_transport_bytes_promoted"], 0)
        self.assertEqual(summary["colocated_independence_violations"], 0)
        self.assertGreaterEqual(summary["missing_capabilities_visible"], 1)
        self.assertGreaterEqual(summary["baseline_invalidations_visible"], 1)
        self.assertGreaterEqual(summary["node_moves_visible"], 1)
        self.assertEqual(summary["order_variations"], 10)
        self.assertEqual(summary["distinct_projection_hashes"], 1)

    def test_adversarial_gate_governs_spoofing_ood_and_shared_causes(self) -> None:
        summary = self.assert_gate_passed("beacon-adversarial")

        self.assertGreaterEqual(summary["hostile_cases"], 10)
        self.assertEqual(summary["hostile_cases"], summary["cases_reconciled"])
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["false_presence_confirmations"], 0)
        self.assertEqual(summary["false_absence_inferences"], 0)
        self.assertEqual(summary["raw_material_fact_promotions"], 0)
        self.assertEqual(summary["shared_cause_counted_independent"], 0)
        self.assertGreaterEqual(summary["ood_or_unknown_visible"], 1)
        self.assertGreaterEqual(summary["artifacts_visible"], 1)
        self.assertTrue(
            all(
                item["disposition"]
                in {
                    "sensor_artifact_likely",
                    "insufficient_coverage",
                    "unknown",
                    "single_modality_candidate",
                }
                for item in summary["dispositions"]
            )
        )

    def test_retention_fault_preserves_life_safety_before_minimization(self) -> None:
        summary = self.assert_gate_passed("retention-fault")

        self.assertGreaterEqual(summary["capture_cases"], 6)
        self.assertEqual(summary["capture_cases"], summary["cases_reconciled"])
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["unauthorized_snippets_captured"], 0)
        self.assertEqual(summary["unencrypted_snippets_preserved"], 0)
        self.assertEqual(summary["over_cap_snippets_preserved"], 0)
        self.assertEqual(summary["unreviewed_material_deleted"], 0)
        self.assertEqual(summary["deletions_without_disposition_receipt"], 0)
        self.assertGreaterEqual(summary["life_safety_items_preserved"], 1)
        self.assertGreaterEqual(summary["holds_created"], 1)
        self.assertGreaterEqual(summary["disposition_receipts"], 1)
        self.assertEqual(
            summary["material_items"], summary["material_items_traced_to_disposition"]
        )

    def test_campaign_freezes_all_gate_hashes(self) -> None:
        self.assertTrue(CAMPAIGN.is_file())
        campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
        self.assertEqual(
            set(campaign["expected_result_sha256"]),
            {"beacon-replay", "beacon-adversarial", "retention-fault"},
        )
        for gate, expected in campaign["expected_result_sha256"].items():
            summary = self.assert_gate_passed(gate)
            self.assertEqual(summary["result_sha256"], expected)

    def test_ci_runs_p0_07_gates_with_independent_receipts(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        for gate in ("beacon-replay", "beacon-adversarial", "retention-fault"):
            self.assertIn(f"openbrec.verify {gate}", workflow)
            self.assertIn(f"evidence/p0/p0-07/{gate}/p0-07-receipt.json", workflow)


if __name__ == "__main__":
    unittest.main()
