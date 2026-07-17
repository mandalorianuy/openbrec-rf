from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = "fixtures/p0/federation/50k-sites.json"


class P005FederationTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_gate_passed(self, gate: str, *args: str) -> dict[str, object]:
        result = self.run_verify(gate, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["result"], "passed")
        return output["summary"]

    def test_p0_05_gates_and_scenario_argument_are_registered(self) -> None:
        scale = self.run_verify("federation-scale", "--help")
        self.assertEqual(scale.returncode, 0, scale.stderr)
        self.assertIn("--scenario", scale.stdout)

        reconciliation = self.run_verify("federation-reconciliation", "--help")
        self.assertEqual(reconciliation.returncode, 0, reconciliation.stderr)

    def test_scenario_freezes_scale_partition_and_failure_campaign(self) -> None:
        path = REPO_ROOT / SCENARIO
        self.assertTrue(path.is_file())
        scenario = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(scenario["scenario_version"], "1.0.0")
        self.assertEqual(scenario["claim_scope"], "deterministic_simulation_only")
        self.assertEqual(scenario["generator"]["version"], "1.0.0")
        self.assertIsInstance(scenario["generator"]["seed"], int)
        self.assertEqual(
            scenario["scale"],
            {
                "sites": 50000,
                "response_cells": 60,
                "operational_areas": 5,
                "hubs": 2,
            },
        )
        self.assertEqual(scenario["partition"]["duration_s"], 86400)
        self.assertEqual(set(scenario["partition"]["unavailable_hubs"]), {"hub-a", "hub-b"})
        self.assertEqual(
            set(scenario["local_critical_operations"]),
            {"sos", "sensing", "messaging", "rf_decision"},
        )
        self.assertEqual(
            set(scenario["reconciliation_campaign"]),
            {
                "identical_duplicates",
                "same_id_conflicts",
                "handoff_conflicts",
                "resource_assignment_conflicts",
            },
        )
        self.assertTrue(scenario["gateway_policy"]["outbound_only"])
        self.assertTrue(scenario["gateway_policy"]["carry_bundle_fallback"])

    def test_scale_gate_materializes_hierarchy_and_proves_local_autonomy(self) -> None:
        summary = self.assert_gate_passed("federation-scale", "--scenario", SCENARIO)

        self.assertEqual(summary["generated_sites"], 50000)
        self.assertEqual(summary["unique_site_ids"], 50000)
        self.assertEqual(summary["assigned_sites"], 50000)
        self.assertEqual(summary["unassigned_sites"], 0)
        self.assertEqual(summary["response_cells"], 60)
        self.assertEqual(summary["operational_areas"], 5)
        self.assertEqual(summary["hubs"], 2)
        self.assertEqual(summary["generated_topology_entities"], 50126)
        self.assertEqual(summary["materialized_topology_events"], 50126)
        self.assertEqual(summary["schema_validated_topology_shapes"], 5)
        self.assertEqual(summary["signature_verified_topology_shapes"], 5)
        self.assertEqual(summary["site_distribution_min"], 833)
        self.assertEqual(summary["site_distribution_max"], 834)

        self.assertEqual(summary["partition_duration_s"], 86400)
        self.assertEqual(summary["unavailable_hubs"], 2)
        self.assertEqual(summary["autonomous_cells"], 60)
        self.assertEqual(summary["local_operations_denominator"], 240)
        self.assertEqual(summary["local_operations_executed"], 240)
        self.assertEqual(summary["local_operations_blocked_by_superior"], 0)
        self.assertEqual(summary["central_critical_path_dependencies"], 0)
        self.assertEqual(summary["autonomous_hierarchy_entities"], 50126)
        self.assertEqual(summary["hierarchy_operations_denominator"], 50126)
        self.assertEqual(summary["hierarchy_operations_executed"], 50126)
        self.assertEqual(summary["hierarchy_operations_blocked_by_superior"], 0)

        self.assertEqual(summary["outbound_gateways"], 60)
        self.assertEqual(summary["inbound_listeners"], 0)
        self.assertEqual(summary["federation_events_denominator"], 180)
        self.assertEqual(summary["federation_events_reconciled"], 180)
        self.assertEqual(summary["carry_bundles"], 60)
        self.assertEqual(summary["minimal_disclosure_violations"], 0)
        self.assertEqual(summary["raw_payloads_exported"], 0)
        self.assertEqual(summary["hub_cell_private_keys"], 0)
        self.assertFalse(summary["hub_can_decrypt_local_content"])
        self.assertFalse(summary["hub_can_order_tx"])
        self.assertEqual(summary["false_operational_acceptance"], 0)
        self.assertEqual(summary["unreconciled"], 0)

    def test_reconciliation_is_append_only_deterministic_and_hostile_hub_safe(self) -> None:
        summary = self.assert_gate_passed("federation-reconciliation")

        self.assertEqual(summary["replay_runs"], 10)
        self.assertEqual(summary["unique_replay_hashes"], 1)
        self.assertEqual(summary["identical_duplicates"], 10)
        self.assertEqual(summary["integrity_conflicts"], 5)
        self.assertEqual(summary["handoff_conflicts"], 5)
        self.assertEqual(summary["resource_assignment_conflicts"], 5)
        self.assertEqual(summary["visible_conflicts"], 15)
        self.assertEqual(summary["human_resolutions_pending"], 15)
        self.assertEqual(summary["overwritten_events"], 0)
        self.assertEqual(summary["silently_lost_events"], 0)
        self.assertFalse(summary["last_write_wins_used"])
        self.assertEqual(summary["monotonic_safety_violations"], 0)

        self.assertGreaterEqual(summary["hostile_hub_cases"], 8)
        self.assertEqual(summary["false_operational_acceptance"], 0)
        self.assertEqual(summary["hub_forged_cell_events_accepted"], 0)
        self.assertEqual(summary["hub_tx_orders_executed"], 0)
        self.assertEqual(summary["local_content_disclosures"], 0)
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["hostile_hub_cases"], len(summary["hostile_dispositions"]))

    def test_scenario_freezes_both_gate_hashes(self) -> None:
        scenario = json.loads((REPO_ROOT / SCENARIO).read_text(encoding="utf-8"))
        self.assertEqual(
            set(scenario["expected_result_sha256"]),
            {"federation-scale", "federation-reconciliation"},
        )
        for gate, expected in scenario["expected_result_sha256"].items():
            args = ("--scenario", SCENARIO) if gate == "federation-scale" else ()
            summary = self.assert_gate_passed(gate, *args)
            self.assertEqual(summary["result_sha256"], expected)

    def test_ci_runs_p0_05_gates_with_independent_receipts(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "openbrec.verify federation-scale --scenario " + SCENARIO,
            workflow,
        )
        self.assertIn(
            "evidence/p0/p0-05/federation-scale/p0-05-receipt.json",
            workflow,
        )
        self.assertIn("openbrec.verify federation-reconciliation", workflow)
        self.assertIn(
            "evidence/p0/p0-05/federation-reconciliation/p0-05-receipt.json",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
