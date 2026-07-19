from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO = REPO_ROOT / "fixtures/p0/terminal/offline-terminal.json"
PNPM_AVAILABLE = shutil.which("pnpm") is not None
PNPM_MISSING_REASON = (
    "pnpm not installed; skipping gate that builds the PWA browser evidence"
)


class P006OfflineTerminalTests(unittest.TestCase):
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

    def test_p0_06_gates_are_registered(self) -> None:
        for gate in ("terminal-ux", "accessibility"):
            result = subprocess.run(
                [sys.executable, "-m", "openbrec.verify", gate, "--help"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_scenario_declares_offline_actions_states_and_safety_copy(self) -> None:
        self.assertTrue(SCENARIO.is_file())
        scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))

        self.assertEqual(scenario["scenario_version"], "1.0.0")
        self.assertEqual(scenario["claim_scope"], "deterministic_simulation_only")
        self.assertFalse(scenario["connectivity"]["internet_available"])
        self.assertFalse(scenario["connectivity"]["hub_available"])
        self.assertFalse(scenario["connectivity"]["superior_service_available"])
        self.assertEqual(
            set(scenario["terminal_capability"]["offline_actions"]),
            {"text", "status", "sos", "location", "cancel_request", "queue_review"},
        )
        self.assertEqual(
            {message["message_type"] for message in scenario["messages"]},
            {"text", "status", "sos", "location"},
        )
        self.assertEqual(
            set(scenario["expected_states"]),
            {"queued", "sent", "delivered", "seen", "accepted", "cancelled", "expired"},
        )
        copy = " ".join(scenario["safety_copy"].values()).lower()
        self.assertIn("no garantiza arribo ni rescate", copy)
        self.assertIn("no implica ausencia", copy)

    def test_terminal_gate_derives_every_state_without_superior_dependency(self) -> None:
        summary = self.assert_gate_passed("terminal-ux")

        self.assertEqual(
            set(summary["derived_states"]),
            {"queued", "sent", "delivered", "seen", "accepted", "cancelled", "expired"},
        )
        self.assertEqual(summary["message_types"], 4)
        self.assertEqual(summary["messages_denominator"], 7)
        self.assertEqual(summary["messages_reconciled"], 7)
        self.assertEqual(summary["unreconciled"], 0)
        self.assertEqual(summary["superior_critical_path_dependencies"], 0)
        self.assertTrue(summary["offline_composer_available"])
        self.assertEqual(summary["hidden_queue_gaps"], 0)
        self.assertEqual(summary["false_delivery_or_rescue_guarantees"], 0)
        self.assertEqual(summary["false_absence_claims"], 0)
        self.assertEqual(summary["direct_state_edits"], 0)

    def test_cancellation_preserves_sos_history_and_receipts(self) -> None:
        summary = self.assert_gate_passed("terminal-ux")

        self.assertEqual(summary["cancelled_messages"], 1)
        self.assertEqual(summary["cancelled_history_events"], 3)
        self.assertEqual(summary["cancelled_path_receipts_preserved"], 1)
        self.assertEqual(summary["deleted_sos_events"], 0)
        self.assertGreaterEqual(summary["visible_queue_items"], 1)
        self.assertTrue(summary["partition_visible"])
        self.assertTrue(summary["expiry_visible"])
        self.assertTrue(summary["uncertainty_visible"])
        self.assertTrue(summary["capabilities_absent_visible"])

    def test_terminal_source_exposes_operational_controls_and_redundant_cues(self) -> None:
        source = (REPO_ROOT / "apps/web/src/main.tsx").read_text(encoding="utf-8")
        for marker in (
            'data-testid="offline-terminal"',
            'data-testid="message-composer"',
            'data-testid="message-queue"',
            'data-testid="message-history"',
            "Encolar texto",
            "Compartir estado",
            "Encolar SOS",
            "Compartir ubicación",
            "Capacidades ausentes",
            "Partición activa",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("setMessageState", source)
        lowered = source.lower()
        for prohibited in ("rescate garantizado", "zona vacía", "sin víctimas"):
            self.assertNotIn(prohibited, lowered)

    @unittest.skipUnless(PNPM_AVAILABLE, PNPM_MISSING_REASON)
    def test_accessibility_gate_is_technical_and_defers_human_claims(self) -> None:
        summary = self.assert_gate_passed("accessibility")

        self.assertGreaterEqual(summary["technical_checks"], 10)
        self.assertEqual(summary["technical_failures"], 0)
        self.assertTrue(summary["keyboard_operable"])
        self.assertTrue(summary["critical_actions_text_labeled"])
        self.assertTrue(summary["redundant_state_cues"])
        self.assertTrue(summary["reduced_motion_supported"])
        self.assertEqual(summary["human_participants"], 0)
        self.assertFalse(summary["human_comprehension_claim"])
        protocol = REPO_ROOT / str(summary["p1a_protocol"])
        self.assertTrue(protocol.is_file())
        text = protocol.read_text(encoding="utf-8")
        self.assertIn("8 operadores", text)
        self.assertIn("8 personas no preparadas", text)
        self.assertIn("90%", text)
        self.assertIn("cero SOS o cancelaciones accidentales", text)

    def test_browser_smoke_exercises_terminal_before_and_after_network_loss(self) -> None:
        smoke = (REPO_ROOT / "apps/web/scripts/ui-smoke.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn('getByTestId("offline-terminal")', smoke)
        self.assertIn('getByTestId("message-composer")', smoke)
        self.assertIn('getByTestId("message-queue")', smoke)
        self.assertIn("context.setOffline(true)", smoke)
        self.assertIn("queued_after_offline_action", smoke)

    @unittest.skipUnless(PNPM_AVAILABLE, PNPM_MISSING_REASON)
    def test_fixture_freezes_gate_hashes_and_ci_writes_independent_receipts(self) -> None:
        scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
        for gate in ("terminal-ux", "accessibility"):
            summary = self.assert_gate_passed(gate)
            self.assertEqual(
                summary["result_sha256"],
                scenario["expected_result_sha256"][gate],
            )

        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        for gate in ("terminal-ux", "ui-smoke", "accessibility"):
            self.assertIn(f"openbrec.verify {gate}", workflow)
            self.assertIn(f"evidence/p0/p0-06/{gate}/p0-06-receipt.json", workflow)


if __name__ == "__main__":
    unittest.main()
