from __future__ import annotations

import subprocess
import sys
import unittest
import tempfile
import json
import copy

from openbrec.energy import EnergyScenarioError, run_energy_scenario
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class P002EnergyReplayTests(unittest.TestCase):
    def load_scenario(self) -> dict[str, object]:
        return json.loads(
            (REPO_ROOT / "fixtures/p0/energy/three-domains.json").read_text(
                encoding="utf-8"
            )
        )

    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_energy_replay_gate_is_registered(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "openbrec.verify", "energy-replay", "--help"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scenario", result.stdout)

    def test_normative_scenario_has_three_autonomous_domains_and_load_classes(
        self,
    ) -> None:
        scenario_path = REPO_ROOT / "fixtures/p0/energy/three-domains.json"
        self.assertTrue(scenario_path.is_file())
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))

        self.assertEqual(len(scenario["domains"]), 3)
        self.assertEqual(
            {
                load["class"]
                for domain in scenario["domains"]
                for load in domain["loads"]
            },
            {
                "L0_LIFE_SAFETY",
                "L1_MISSION_CRITICAL",
                "L2_MISSION_SUPPORT",
                "L3_DEFERRABLE",
            },
        )
        self.assertTrue(all(domain["autonomous"] for domain in scenario["domains"]))
        self.assertTrue(
            any(
                event["kind"] == "brownout"
                for domain in scenario["domains"]
                for event in domain["events"]
            )
        )

    def test_energy_gate_replays_conservatively_and_deterministically(self) -> None:
        result = self.run_verify(
            "energy-replay",
            "--scenario",
            "fixtures/p0/energy/three-domains.json",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        summary = output["summary"]
        self.assertEqual(summary["domains"], 3)
        self.assertEqual(summary["determinism_runs"], 10)
        self.assertEqual(len(summary["unique_result_hashes"]), 1)
        self.assertEqual(summary["unknown_soc_domains"], 1)
        self.assertTrue(summary["brownout_state_preserved"])
        self.assertTrue(summary["source_loss_local_reserve_preserved"])
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["claim_scope"], "simulation_only")
        self.assertIn("domain_evidence", summary)
        self.assertEqual(
            summary["domain_evidence"]["energy-cell-a"]["state_path"],
            ["normal", "normal", "conserve", "survival", "critical"],
        )
        self.assertEqual(
            summary["domain_evidence"]["energy-beacon-a"]["remaining_usable_Wh_lower"],
            None,
        )

    def test_budget_excludes_auxiliary_generation_and_unknown_soc_stays_unknown(
        self,
    ) -> None:
        outcome = run_energy_scenario(self.load_scenario(), repository_root=REPO_ROOT)
        by_domain = {item["domain_id"]: item for item in outcome["domains"]}
        cell = by_domain["energy-cell-a"]
        beacon = by_domain["energy-beacon-a"]

        self.assertIn("auxiliary_credited_to_storage_reserve_Wh", cell["conservation"])
        self.assertEqual(
            cell["conservation"]["auxiliary_credited_to_storage_reserve_Wh"], 0
        )
        self.assertEqual(
            cell["conservation"]["storage_only_margin_Wh"],
            round(
                cell["conservation"]["remaining_usable_Wh_lower"]
                - cell["conservation"]["required_with_margin_Wh"],
                6,
            ),
        )
        self.assertEqual(beacon["budget"]["result"], "unknown")
        self.assertGreater(beacon["budget"]["usable_storage_Wh"], 0)
        self.assertIsNone(beacon["conservation"]["remaining_usable_Wh_lower"])
        self.assertNotIn("runtime_lower_bound_s", beacon["budget"])

    def test_fsm_applies_hysteresis_and_sos_sheds_only_degradable_loads(self) -> None:
        outcome = run_energy_scenario(self.load_scenario(), repository_root=REPO_ROOT)
        by_domain = {item["domain_id"]: item for item in outcome["domains"]}
        relay = by_domain["energy-relay-a"]
        cell = by_domain["energy-cell-a"]

        self.assertIn("state_path", relay)
        self.assertEqual(
            relay["state_path"],
            ["normal", "conserve", "conserve", "normal", "normal"],
        )
        sos = next(
            item
            for item in cell["timeline"]
            if item["checkpoint"]["kind"] == "sos_active"
        )
        self.assertIn("extended-observability", sos["status"]["loads_shed"])
        self.assertNotIn("sos-terminal", sos["status"]["loads_shed"])

    def test_brownout_starts_local_survival_with_new_boot_and_monotonic_state(
        self,
    ) -> None:
        outcome = run_energy_scenario(self.load_scenario(), repository_root=REPO_ROOT)
        cell = next(
            item for item in outcome["domains"] if item["domain_id"] == "energy-cell-a"
        )
        brownout = next(
            item
            for item in cell["timeline"]
            if item["checkpoint"]["kind"] == "brownout"
        )

        self.assertIn("recovery_mode", brownout["checkpoint"])
        self.assertEqual(brownout["checkpoint"]["recovery_mode"], "local_survival")
        self.assertEqual(brownout["status"]["fsm_state"], "survival")
        self.assertNotEqual(
            brownout["checkpoint"]["boot_id"],
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        self.assertGreater(
            brownout["checkpoint"]["sequence_after"],
            brownout["checkpoint"]["sequence_before"],
        )
        self.assertGreaterEqual(
            brownout["checkpoint"]["accepted_log_after"],
            brownout["checkpoint"]["accepted_log_before"],
        )

    def test_negative_reserve_fails_before_budget_projection(self) -> None:
        scenario = copy.deepcopy(self.load_scenario())
        scenario["domains"][0]["reserves"]["sos_Wh"] = -1

        with self.assertRaisesRegex(
            EnergyScenarioError, "energy-cell-a.reserves.sos_Wh must not be negative"
        ):
            run_energy_scenario(scenario, repository_root=REPO_ROOT)

    def test_missing_persistent_boot_identity_fails_closed(self) -> None:
        scenario = copy.deepcopy(self.load_scenario())
        scenario["domains"][0].pop("initial_boot_id")

        with self.assertRaisesRegex(
            EnergyScenarioError,
            "energy-cell-a.initial_boot_id must be 128-bit lowercase hex",
        ):
            run_energy_scenario(scenario, repository_root=REPO_ROOT)

    def test_fixture_freezes_the_expected_replay_hash(self) -> None:
        scenario = self.load_scenario()
        outcome = run_energy_scenario(scenario, repository_root=REPO_ROOT)

        self.assertIn("expected_result_sha256", scenario)
        self.assertEqual(outcome["result_sha256"], scenario["expected_result_sha256"])

    def test_ci_runs_energy_replay_with_a_p0_receipt(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "openbrec.verify energy-replay --scenario fixtures/p0/energy/three-domains.json",
            workflow,
        )
        self.assertIn("evidence/p0/p0-02/energy-replay/p0-02-receipt.json", workflow)

    def test_energy_receipt_assigns_the_energy_maintainer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "energy-receipt.json"
            result = self.run_verify(
                "energy-replay",
                "--scenario",
                "fixtures/p0/energy/three-domains.json",
                "--receipt",
                str(receipt),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            material = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(material["responsible_role"], "energy-maintainer")

    def test_projection_exposes_zero_prohibited_physical_claims(self) -> None:
        outcome = run_energy_scenario(self.load_scenario(), repository_root=REPO_ROOT)

        self.assertIn("prohibited_claims", outcome)
        self.assertEqual(outcome["prohibited_claims"], [])
        serialized = json.dumps(outcome, sort_keys=True).lower()
        self.assertNotIn("72 hours", serialized)
        self.assertNotIn("indefinite", serialized)
        self.assertNotIn("sustainable_under_profile", serialized)

    def test_domain_without_events_fails_with_a_governed_error(self) -> None:
        scenario = copy.deepcopy(self.load_scenario())
        scenario["domains"][0]["events"] = []

        with self.assertRaisesRegex(
            EnergyScenarioError, "energy-cell-a must declare at least one event"
        ):
            run_energy_scenario(scenario, repository_root=REPO_ROOT)

    def test_negative_initial_sequence_is_not_normalized_by_replay(self) -> None:
        scenario = copy.deepcopy(self.load_scenario())
        scenario["domains"][0]["initial_sequence"] = -1

        with self.assertRaisesRegex(
            EnergyScenarioError,
            "energy-cell-a.initial_sequence must be a non-negative integer",
        ):
            run_energy_scenario(scenario, repository_root=REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
