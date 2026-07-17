from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class P003MessagingTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
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

    def test_p0_03_gates_are_registered(self) -> None:
        for gate in (
            "human-message-security",
            "sos-state-replay",
            "transport-policy",
        ):
            result = self.run_verify(gate, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_hostile_fixture_declares_every_required_attack_and_offline_rekey(
        self,
    ) -> None:
        path = REPO_ROOT / "fixtures/p0/messaging/hostile-transport.json"
        self.assertTrue(path.is_file())
        fixture = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(fixture["network_available"])
        self.assertEqual(fixture["claim_scope"], "simulation_only")
        self.assertEqual(
            {case["kind"] for case in fixture["hostile_cases"]},
            {
                "forged",
                "replayed",
                "revoked",
                "late",
                "duplicate",
                "malicious_transport",
                "nonce_reuse",
                "sequence_rollback",
                "default_secret",
            },
        )
        self.assertGreaterEqual(len(fixture["bearers"]), 3)
        self.assertTrue(fixture["offline_rekey"]["required"])
        active_key = fixture["offline_rekey"]["new_group_key_id"]
        old_key = fixture["offline_rekey"]["old_group_key_id"]
        self.assertEqual(fixture["messages"][0]["encryption_key_id"], active_key)
        self.assertNotEqual(active_key, old_key)
        self.assertEqual(fixture["enrollment"]["mode"], "local_human_approval")
        self.assertEqual(fixture["enrollment"]["unknown_peer_rights"], "minimal")
        self.assertTrue(fixture["enrollment"]["revocation_cache_local"])

    def test_human_message_security_authenticates_only_valid_offline_vectors(
        self,
    ) -> None:
        summary = self.assert_gate_passed("human-message-security")

        self.assertEqual(summary["authenticated_messages"], 2)
        self.assertEqual(summary["false_authentications"], 0)
        self.assertEqual(summary["unverified_distress_preserved"], 3)
        self.assertEqual(len(summary["unverified_distress_receipts"]), 3)
        self.assertTrue(
            all(
                receipt["disposition"] == "review_quarantine"
                for receipt in summary["unverified_distress_receipts"]
            )
        )
        self.assertTrue(summary["offline_rekey_succeeded"])
        self.assertTrue(summary["old_group_key_rejected"])
        self.assertEqual(summary["active_group_key_epoch"], 2)
        self.assertTrue(summary["default_secret_rejected"])
        self.assertTrue(summary["nonce_uniqueness_enforced"])
        self.assertTrue(summary["sequence_monotonicity_enforced"])
        self.assertFalse(summary["network_available"])
        self.assertTrue(summary["enrollment_modeled"])
        self.assertTrue(summary["revocation_cache_local"])
        self.assertTrue(summary["unknown_peer_minimum_rights"])
        self.assertTrue(summary["unauthorized_message_type_rejected"])
        self.assertTrue(
            {
                "forged",
                "replayed",
                "revoked",
                "late",
                "nonce_reuse",
                "sequence_rollback",
                "default_secret",
                "old_group_key",
                "unauthorized_role",
            }.issubset(
                {event["security_event"] for event in summary["security_events"]}
            )
        )
        self.assertTrue(
            all(
                len(event["evidence_sha256"]) == 64
                for event in summary["security_events"]
            )
        )

    def test_sos_reducer_separates_technical_and_operational_state(self) -> None:
        summary = self.assert_gate_passed("sos-state-replay")

        self.assertEqual(summary["append_only_events"], 6)
        self.assertEqual(summary["derived_technical_state"], "gateway_received")
        self.assertEqual(summary["derived_operational_state"], "accepted")
        self.assertEqual(summary["false_operator_accepted"], 0)
        self.assertFalse(summary["technical_ack_is_operational"])
        self.assertTrue(summary["causal_prerequisites_enforced"])
        self.assertEqual(summary["unverified_distress_preserved"], 1)
        self.assertEqual(
            summary["unverified_distress_receipt"]["disposition"],
            "review_quarantine",
        )

    def test_transport_policy_deduplicates_without_losing_path_receipts(self) -> None:
        summary = self.assert_gate_passed("transport-policy")

        self.assertEqual(summary["logical_messages"], 1)
        self.assertEqual(summary["path_receipts"], 3)
        self.assertEqual(summary["bearers"], 3)
        self.assertEqual(summary["raw_bridges_emitted"], 0)
        self.assertEqual(summary["false_role_elevations"], 0)
        self.assertTrue(summary["policy_schema_validated"])
        self.assertEqual(summary["allowed_bearers"], 3)
        self.assertEqual(summary["prohibited_bearers"], ["lorawan"])
        self.assertTrue(summary["anti_loop_enforced"])
        self.assertEqual(summary["looped_envelopes_rejected"], 1)
        self.assertEqual(summary["payloads_application_verified"], 3)
        self.assertEqual(summary["tampered_payloads_rejected"], 1)
        self.assertEqual(summary["unreconciled"], 0)

    def test_fixture_freezes_all_three_gate_hashes(self) -> None:
        fixture = json.loads(
            (REPO_ROOT / "fixtures/p0/messaging/hostile-transport.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            set(fixture["expected_result_sha256"]),
            {
                "human-message-security",
                "sos-state-replay",
                "transport-policy",
            },
        )
        for gate, expected in fixture["expected_result_sha256"].items():
            summary = self.assert_gate_passed(gate)
            self.assertEqual(summary["result_sha256"], expected)

    def test_ci_runs_all_p0_03_gates_with_independent_receipts(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )

        for gate in (
            "human-message-security",
            "sos-state-replay",
            "transport-policy",
        ):
            self.assertIn(f"openbrec.verify {gate}", workflow)
            self.assertIn(f"evidence/p0/p0-03/{gate}/p0-03-receipt.json", workflow)


if __name__ == "__main__":
    unittest.main()
