from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "fixtures/p0/integrated/campaign.json"


class P008IntegratedCampaignTests(unittest.TestCase):
    _cached_summary: dict[str, object] | None = None

    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_gate_passed(self) -> dict[str, object]:
        if self.__class__._cached_summary is not None:
            return self.__class__._cached_summary
        result = self.run_verify("p0-integrated", "--scenario", SCENARIO)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["result"], "passed")
        self.__class__._cached_summary = output["summary"]
        return self.__class__._cached_summary

    def test_gate_and_scenario_argument_are_registered(self) -> None:
        result = self.run_verify("p0-integrated", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scenario", result.stdout)

    def test_campaign_freezes_complete_cross_domain_denominator(self) -> None:
        path = REPO_ROOT / SCENARIO
        self.assertTrue(path.is_file())
        campaign = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(campaign["campaign_version"], "1.0.0")
        self.assertEqual(campaign["claim_scope"], "deterministic_simulation_only")
        self.assertEqual(campaign["partition_duration_s"], 86400)
        self.assertEqual(len(campaign["component_scenarios"]), 6)
        self.assertEqual(len(campaign["cells"]), 3)
        self.assertEqual(
            {cell["bearer"] for cell in campaign["cells"]},
            {"meshtastic", "meshcore", "reticulum"},
        )
        self.assertTrue(all(cell["carry_bundle"] for cell in campaign["cells"]))
        self.assertEqual(
            {fault["kind"] for fault in campaign["faults"]},
            {
                "partition",
                "node_loss",
                "relay_loss",
                "source_loss",
                "hub_loss",
                "brownout",
                "forged_distress",
                "replay",
                "stolen_terminal",
                "spoofed_sensor",
                "malicious_hub",
            },
        )
        self.assertIsInstance(campaign["expected_result_sha256"], str)

    def test_gate_composes_all_accepted_addon_gates(self) -> None:
        summary = self.assert_gate_passed()

        self.assertEqual(summary["component_gates_denominator"], 13)
        self.assertEqual(summary["component_gates_passed"], 13)
        self.assertEqual(summary["component_gates_failed"], 0)
        self.assertEqual(summary["component_gaps_reported"], 6)
        self.assertEqual(summary["component_gaps_visible"], 6)
        self.assertEqual(summary["hidden_component_gaps"], 0)
        self.assertEqual(
            set(summary["offline_projection"]),
            {"energy", "communication", "messages", "beacon", "review"},
        )

    def test_faults_are_reconciled_without_false_safety_claims(self) -> None:
        summary = self.assert_gate_passed()

        self.assertEqual(summary["faults_denominator"], 11)
        self.assertEqual(summary["faults_reconciled"], 11)
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["silent_successes"], 0)
        self.assertEqual(summary["false_acceptance"], 0)
        self.assertEqual(summary["false_confirmation"], 0)
        self.assertEqual(summary["false_absence"], 0)
        self.assertEqual(summary["lost_accepted_log_events"], 0)
        self.assertEqual(summary["lost_vital_state_events"], 0)
        self.assertEqual(summary["sos_priority_inversions"], 0)
        self.assertEqual(summary["distress_preserved_for_review"], 4)

    def test_every_cell_operates_during_partition_and_degrades_visibly(self) -> None:
        summary = self.assert_gate_passed()

        self.assertEqual(summary["partition_duration_s"], 86400)
        self.assertEqual(summary["cells_denominator"], 3)
        self.assertEqual(summary["cells_operating_locally"], 3)
        self.assertEqual(summary["cells_blocked_by_superior"], 0)
        self.assertEqual(summary["carry_bundles_reconciled"], 3)
        self.assertEqual(summary["degraded_domains"], 3)
        self.assertEqual(summary["degraded_domains_visible"], 3)
        self.assertEqual(
            set(summary["degradation_states"]), {"energy", "radio", "sensing"}
        )

    def test_campaign_is_deterministic_and_frozen(self) -> None:
        campaign = json.loads((REPO_ROOT / SCENARIO).read_text(encoding="utf-8"))
        summary = self.assert_gate_passed()

        self.assertEqual(summary["order_variations"], 10)
        self.assertEqual(summary["distinct_projection_hashes"], 1)
        self.assertEqual(summary["result_sha256"], campaign["expected_result_sha256"])

    def test_ci_runs_integrated_gate_with_independent_receipt(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "openbrec.verify p0-integrated --scenario " + SCENARIO,
            workflow,
        )
        self.assertIn(
            "evidence/p0/p0-08/p0-integrated/p0-08-receipt.json",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
