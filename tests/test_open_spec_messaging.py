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
PROFILES = (
    ROOT / "specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json"
)
CONTENT_SCHEMA = ROOT / "schemas/open-spec/human-message-content.schema.json"
EVENT_SCHEMA = ROOT / "schemas/open-spec/human-message-lifecycle-event.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/messaging/interoperability-examples.json"
RESIDUALS = ROOT / "docs/governance/open-spec-messaging-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-04/os-04-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-04/acceptance.json"

MESSAGE_TYPES = {"text", "status", "sos", "location"}
SOS_EVENTS = {
    "sos.created",
    "sos.queued",
    "transport.transmitted",
    "transport.relay_observed",
    "gateway.received",
    "operator.seen",
    "operator.accepted",
    "sos.cancel_requested",
    "sos.expired",
    "sos.failed",
}


class OpenSpecMessagingTests(unittest.TestCase):
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
        result = self.run_verify("open-spec-messaging", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--profiles",
            "--content-schema",
            "--event-schema",
            "--fixtures",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_os_04_remains_accepted_after_os_05_closure(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("6 / 8", source)
        self.assertIn("OS-04 — aceptada", source)
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

    def test_profiles_cover_four_types_without_transport_coupling(self) -> None:
        value = self.load_json(PROFILES)
        self.assertEqual(
            {row["message_type"] for row in value["message_profiles"]}, MESSAGE_TYPES
        )
        self.assertFalse(value["open_boundary"]["requires_specific_bearer"])
        self.assertFalse(value["open_boundary"]["requires_owned_hardware"])
        self.assertFalse(value["open_boundary"]["physical_delivery_blocks_spec"])
        for row in value["message_profiles"]:
            self.assertTrue(row["alternatives_allowed"])
            self.assertTrue(row["content_contract"])
            self.assertTrue(row["acceptance_criteria"])
            self.assertTrue(row["limitations"])

    def test_application_security_is_above_every_bearer(self) -> None:
        security = self.load_json(PROFILES)["application_security"]
        self.assertEqual(security["trust_boundary"], "untrusted_transport")
        for field in (
            "incident_scoped_identity",
            "actor_device_binding",
            "encrypt_then_sign",
            "all_routing_headers_authenticated",
            "ttl_checked",
            "boot_sequence_monotonic",
            "nonce_reuse_fails_closed",
            "revocation_and_rekey_offline",
            "stable_message_id_across_bearers",
        ):
            self.assertTrue(security[field], field)
        self.assertFalse(security["bearer_id_is_actor_identity"])
        self.assertFalse(security["transport_ack_is_delivery"])
        self.assertFalse(security["transport_ack_is_operator_acceptance"])
        self.assertTrue(security["p0_crypto_evidence_ref"])

    def test_sos_semantics_are_append_only_and_never_guarantee_rescue(self) -> None:
        distress = self.load_json(PROFILES)["distress_policy"]
        self.assertEqual(set(distress["event_types"]), SOS_EVENTS)
        self.assertTrue(distress["append_only"])
        self.assertTrue(distress["cancel_adds_event_never_erases"])
        self.assertTrue(distress["late_event_never_regresses_terminal_state"])
        self.assertTrue(
            distress[
                "operator_acceptance_requires_gateway_seen_and_authorized_signature"
            ]
        )
        self.assertFalse(distress["gateway_received_means_rescue"])
        self.assertFalse(distress["operator_accepted_means_rescue"])
        self.assertFalse(distress["transport_may_set_derived_state"])

    def test_life_safety_preservation_precedes_minimization_without_false_authentication(
        self,
    ) -> None:
        preservation = self.load_json(PROFILES)["life_safety_preservation"]
        self.assertTrue(preservation["possible_distress_is_never_silently_discarded"])
        self.assertEqual(
            set(preservation["allowed_destinations"]),
            {"EvidenceVault", "ReviewQuarantine"},
        )
        self.assertTrue(preservation["access_control_required"])
        self.assertTrue(preservation["audit_required"])
        self.assertTrue(preservation["retention_review_required"])
        self.assertFalse(preservation["unverified_distress_becomes_authenticated"])
        self.assertFalse(
            preservation["privacy_minimization_may_destroy_possible_distress"]
        )

    def test_content_and_event_schemas_are_closed_and_examples_conform(self) -> None:
        content_schema = self.load_json(CONTENT_SCHEMA)
        event_schema = self.load_json(EVENT_SCHEMA)
        Draft202012Validator.check_schema(content_schema)
        Draft202012Validator.check_schema(event_schema)
        self.assertFalse(content_schema["additionalProperties"])
        self.assertFalse(event_schema["additionalProperties"])
        fixtures = self.load_json(FIXTURES)
        content_validator = Draft202012Validator(
            content_schema, format_checker=FormatChecker()
        )
        event_validator = Draft202012Validator(
            event_schema, format_checker=FormatChecker()
        )
        contents = fixtures["contents"]
        self.assertEqual({row["message_type"] for row in contents}, MESSAGE_TYPES)
        for index, row in enumerate(contents):
            errors = sorted(
                content_validator.iter_errors(row), key=lambda error: list(error.path)
            )
            self.assertEqual(
                errors,
                [],
                f"contents[{index}]: " + "; ".join(e.message for e in errors),
            )
        for index, row in enumerate(fixtures["sos_replay"]["events"]):
            errors = sorted(
                event_validator.iter_errors(row), key=lambda error: list(error.path)
            )
            self.assertEqual(
                errors, [], f"events[{index}]: " + "; ".join(e.message for e in errors)
            )

    def test_location_requires_source_precision_time_and_staleness(self) -> None:
        location = next(
            row
            for row in self.load_json(FIXTURES)["contents"]
            if row["message_type"] == "location"
        )
        self.assertEqual(
            set(location["body"]),
            {"representation", "zone", "precision_m", "source", "captured_at", "stale"},
        )
        schema = self.load_json(CONTENT_SCHEMA)
        broken = json.loads(json.dumps(location))
        del broken["body"]["precision_m"]
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(broken)))

    def test_sos_replay_is_deterministic_and_separates_receipt_states(self) -> None:
        result = self.run_verify("open-spec-messaging")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["replay_orders"], 10)
        self.assertEqual(summary["replay_hashes"], 1)
        self.assertEqual(summary["technical_state"], "gateway_received")
        self.assertEqual(summary["human_state"], "seen")
        self.assertEqual(summary["operational_state"], "accepted")
        self.assertEqual(summary["false_operator_acceptances"], 0)
        self.assertEqual(summary["cancel_events_preserved"], 1)
        self.assertEqual(summary["silent_discards"], 0)

    def test_false_acceptance_and_unverified_distress_are_preserved_for_review(
        self,
    ) -> None:
        result = self.run_verify("open-spec-messaging")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["rejected_false_acceptances"], 1)
        self.assertEqual(summary["unverified_distress_cases"], 4)
        self.assertEqual(summary["unverified_distress_preserved"], 4)
        self.assertEqual(summary["unverified_distress_authenticated"], 0)

    def test_gate_rejects_a_delivery_guarantee(self) -> None:
        profiles = self.load_json(PROFILES)
        profiles["distress_policy"]["operator_accepted_means_rescue"] = True
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            result = self.run_verify("open-spec-messaging", "--profiles", str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot guarantee rescue", result.stderr)

    def test_residuals_are_resolved_controlled_planned_or_evidence_required(
        self,
    ) -> None:
        register = self.load_json(RESIDUALS)
        self.assertEqual(register["task"], "OS-04")
        self.assertGreaterEqual(len(register["residuals"]), 10)
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

    def test_gate_reports_os_04_acceptance_without_physical_claims(self) -> None:
        result = self.run_verify("open-spec-messaging")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 6)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["message_profiles"], 4)
        self.assertEqual(summary["conforming_contents"], 4)
        self.assertFalse(summary["physical_delivery_blocks_publication"])
        self.assertEqual(summary["next_task"], "OS-07")
        self.assertFalse(summary["next_task_started"])

    def test_board_readme_and_ci_publish_os_04_gate(self) -> None:
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec `6 / 8`", board)
        self.assertIn("[x] `OS-04`", board)
        self.assertIn("OS-06", board)
        self.assertIn("openbrec.verify open-spec-messaging", readme)
        self.assertIn("messaging-interoperability-profiles.json", readme)
        self.assertIn("  open-spec-messaging:", workflow)
        job = workflow.split("  open-spec-messaging:", 1)[1]
        self.assertIn("tests.test_open_spec_messaging", job)
        self.assertIn("openbrec.verify open-spec-messaging", job)
        self.assertIn("evidence/open-spec/os-04", job)

    def test_os_04_acceptance_is_scoped_and_does_not_start_os_05(self) -> None:
        acceptance = self.load_json(ACCEPTANCE)
        receipt = self.load_json(RECEIPT)
        self.assertEqual(acceptance["task"], "OS-04")
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
            {"accepted_tasks": 4, "total_tasks": 8, "percent": 50.0},
        )
        self.assertFalse(acceptance["physical_validation_progress"]["blocks_open_spec"])
        self.assertEqual(acceptance["next_task"], "OS-05")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
