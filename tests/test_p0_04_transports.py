from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = "fixtures/p0/transports/common-workload.json"


class P004TransportComparisonTests(unittest.TestCase):
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

    def test_p0_04_gates_and_workload_argument_are_registered(self) -> None:
        comparison = self.run_verify("transport-comparison", "--help")
        self.assertEqual(comparison.returncode, 0, comparison.stderr)
        self.assertIn("--workload", comparison.stdout)

        malicious = self.run_verify("malicious-transport", "--help")
        self.assertEqual(malicious.returncode, 0, malicious.stderr)

    def test_workload_pins_sources_profiles_scales_faults_and_traffic(self) -> None:
        path = REPO_ROOT / WORKLOAD
        self.assertTrue(path.is_file())
        workload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(workload["claim_scope"], "deterministic_simulation_only")
        self.assertEqual(
            set(workload["bearer_models"]),
            {"meshtastic", "meshcore", "reticulum"},
        )
        for model in workload["bearer_models"].values():
            self.assertRegex(model["source_pin"]["version"], r"\S+")
            self.assertRegex(model["source_pin"]["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(model["source_pin"]["url"].startswith("https://"))
            self.assertEqual(model["support_status"], "unverified")
            self.assertTrue(model["limitations"])

        self.assertEqual(
            set(workload["profiles"]),
            {
                "mobile_spontaneous_team",
                "planned_urban_response_cell",
                "heterogeneous_gateway_backbone",
            },
        )
        self.assertEqual(workload["node_scales"], [12, 40, 100])
        self.assertEqual(
            set(workload["faults"]),
            {"mobility", "relay_loss", "path_churn", "flood", "partition", "carry"},
        )
        self.assertEqual(
            {item["message_type"] for item in workload["traffic"]},
            {"sos", "status", "location"},
        )

    def test_comparison_uses_common_envelopes_and_complete_denominators(self) -> None:
        summary = self.assert_gate_passed(
            "transport-comparison", "--workload", WORKLOAD
        )

        self.assertEqual(summary["bearer_models"], 3)
        self.assertEqual(summary["profiles"], 3)
        self.assertEqual(summary["scales"], [12, 40, 100])
        self.assertEqual(summary["model_profile_scale_runs"], 27)
        self.assertEqual(summary["common_envelope_sets"], 9)
        self.assertEqual(summary["fault_classes_modeled"], 6)
        self.assertEqual(summary["fault_events_modeled"], 23)
        self.assertEqual(summary["fault_effects_applied"], 27)
        self.assertEqual(summary["cross_bearer_input_hash_mismatches"], 0)
        self.assertEqual(summary["raw_bridges_emitted"], 0)
        self.assertEqual(summary["sos_priority_violations"], 0)
        self.assertIsNone(summary["global_winner"])
        self.assertFalse(summary["physical_range_or_hop_claim"])

        required_metrics = {
            "pdr",
            "latency_ms_p50",
            "latency_ms_p95",
            "latency_ms_p99",
            "airtime_units",
            "retries",
            "duplicates",
            "convergence_ms",
            "modeled_energy_units",
            "metadata_disclosure_fields",
        }
        self.assertGreater(summary["denominator_messages"], 0)
        self.assertEqual(
            summary["denominator_messages"],
            summary["delivered_messages"] + summary["failed_messages"],
        )
        for result in summary["results"]:
            self.assertEqual(
                result["denominator_messages"],
                result["delivered_messages"] + result["failed_messages"],
            )
            self.assertTrue(required_metrics.issubset(result["metrics"]))
            self.assertEqual(result["claim_scope"], "deterministic_simulation_only")
            self.assertRegex(result["model_version"], r"\S+")
            self.assertIn(result["profile_id"], {
                "mobile_spontaneous_team",
                "planned_urban_response_cell",
                "heterogeneous_gateway_backbone",
            })

    def test_malicious_transport_has_zero_false_acceptance_and_no_silent_loss(self) -> None:
        summary = self.assert_gate_passed("malicious-transport")

        self.assertGreaterEqual(summary["hostile_cases"], 9)
        self.assertEqual(summary["false_operational_acceptance"], 0)
        self.assertEqual(summary["raw_bridges_emitted"], 0)
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["hostile_cases"], len(summary["dispositions"]))
        self.assertTrue(
            all(item["disposition"] in {"rejected", "review_quarantine"}
                for item in summary["dispositions"])
        )

    def test_workload_freezes_both_gate_hashes(self) -> None:
        workload = json.loads((REPO_ROOT / WORKLOAD).read_text(encoding="utf-8"))
        self.assertEqual(
            set(workload["expected_result_sha256"]),
            {"transport-comparison", "malicious-transport"},
        )
        for gate, expected in workload["expected_result_sha256"].items():
            args = ("--workload", WORKLOAD) if gate == "transport-comparison" else ()
            summary = self.assert_gate_passed(gate, *args)
            self.assertEqual(summary["result_sha256"], expected)

    def test_ci_runs_p0_04_gates_with_independent_receipts(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "openbrec.verify transport-comparison --workload " + WORKLOAD,
            workflow,
        )
        self.assertIn(
            "evidence/p0/p0-04/transport-comparison/p0-04-receipt.json",
            workflow,
        )
        self.assertIn("openbrec.verify malicious-transport", workflow)
        self.assertIn(
            "evidence/p0/p0-04/malicious-transport/p0-04-receipt.json",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
