from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.open_spec_federation import run_open_spec_federation_gate

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md"
POLICY = ROOT / "config/open-spec/governance.json"
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json"
PEER_SCHEMA = ROOT / "schemas/open-spec/federation-peer-agreement.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/federation/conformance-examples.json"
RESIDUALS = ROOT / "docs/governance/open-spec-federation-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-06/os-06-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-06/acceptance.json"

LEVELS = ["IncidentFederation", "OperationalArea", "ResponseCell", "Deployment", "Site"]


class OpenSpecFederationTests(unittest.TestCase):
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
        result = self.run_verify("open-spec-federation", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ("--profiles", "--peer-schema", "--fixtures", "--residuals"):
            self.assertIn(option, result.stdout)

    def test_os_06_remains_accepted_after_os_07_closure(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("7 / 8", source)
        self.assertIn("OS-06 — aceptada", source)
        self.assertIn("OS-07 — aceptada", source)
        self.assertIn("OS-08 — no iniciada", source)
        policy = self.load_json(POLICY)
        self.assertEqual(
            policy["progress"],
            {"accepted_tasks": 7, "total_tasks": 8, "percent": 87.5},
        )
        tasks = policy["tasks"]
        self.assertEqual([task["status"] for task in tasks[:7]], ["accepted"] * 7)
        self.assertTrue(all(task["status"] == "not_started" for task in tasks[7:]))

    def test_hierarchy_is_recursive_and_every_level_operates_isolated(self) -> None:
        profiles = self.load_json(PROFILES)
        hierarchy = profiles["hierarchy"]
        self.assertEqual([row["level"] for row in hierarchy], LEVELS)
        for row in hierarchy:
            self.assertTrue(row["can_operate_without_parent"])
            self.assertTrue(row["local_event_log"])
            self.assertTrue(row["local_trust_cache"])
            self.assertTrue(row["local_policy_cache"])
            self.assertTrue(row["distress_preservation"])
        self.assertEqual(profiles["minimum_federable_unit"], "ResponseCell")

    def test_open_boundary_rejects_central_or_mega_mesh_critical_paths(self) -> None:
        boundary = self.load_json(PROFILES)["open_boundary"]
        self.assertFalse(boundary["central_service_in_critical_path"])
        self.assertFalse(boundary["cloud_in_critical_path"])
        self.assertFalse(boundary["single_incident_wide_lora_mesh"])
        self.assertFalse(boundary["owned_hardware_required"])
        self.assertFalse(boundary["physical_scale_blocks_spec"])
        self.assertTrue(boundary["local_networks_per_response_cell"])

    def test_multiple_teams_and_networks_are_isolated_until_explicit_peering(
        self,
    ) -> None:
        isolation = self.load_json(PROFILES)["team_network_isolation"]
        for field in ("identity_namespace", "keys", "event_log", "local_broker"):
            self.assertEqual(isolation[field], "separate_per_response_cell")
        self.assertEqual(
            isolation["cross_cell_exchange"], "explicit_peer_agreement_only"
        )
        self.assertFalse(isolation["shared_incident_key_allowed"])
        self.assertFalse(isolation["shared_incident_mqtt_root_allowed"])

    def test_peer_agreement_is_closed_minimal_and_non_authoritative(self) -> None:
        schema = self.load_json(PEER_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        agreements = self.load_json(FIXTURES)["peer_agreements"]
        self.assertGreaterEqual(len(agreements), 2)
        for index, agreement in enumerate(agreements):
            self.assertEqual(
                list(validator.iter_errors(agreement)), [], f"agreement {index}"
            )
            self.assertTrue(agreement["outbound_only"])
            self.assertTrue(agreement["minimal_disclosure"])
            self.assertFalse(agreement["authority_escalation"])
            self.assertFalse(agreement["raw_payload_allowed"])
            self.assertTrue(agreement["each_party_retains_source_log"])

    def test_hubs_are_optional_redundant_and_non_authoritative(self) -> None:
        hubs = self.load_json(PROFILES)["coordination_hubs"]
        self.assertFalse(hubs["required"])
        self.assertEqual(hubs["minimum_redundancy_when_deployed"], 2)
        self.assertTrue(hubs["backhaul_separate_from_local_lora"])
        for field in (
            "holds_cell_keys",
            "decrypts_local_content",
            "creates_operator_acceptance",
            "orders_radio_tx",
            "overwrites_source_logs",
        ):
            self.assertFalse(hubs[field])

    def test_partition_fixtures_cover_all_levels_without_blocking_local_ops(
        self,
    ) -> None:
        cases = self.load_json(FIXTURES)["partition_cases"]
        self.assertEqual([row["isolated_level"] for row in cases], LEVELS)
        for row in cases:
            self.assertFalse(row["parent_available"])
            self.assertEqual(
                row["local_operations_attempted"], row["local_operations_executed"]
            )
            self.assertEqual(row["local_operations_blocked_by_superior"], 0)
            self.assertTrue(row["distress_preserved"])

    def test_stale_trust_preserves_life_safety_and_restricts_sensitive_actions(
        self,
    ) -> None:
        trust = self.load_json(PROFILES)["stale_trust_policy"]
        self.assertTrue(trust["local_operation_continues"])
        self.assertTrue(trust["distress_preserved"])
        self.assertTrue(trust["existing_local_log_remains_authoritative"])
        self.assertEqual(
            set(trust["restricted_actions"]),
            {"new_sensitive_federation", "new_enrollment", "remote_policy_change"},
        )

    def test_reconciliation_is_deterministic_visible_and_append_only(self) -> None:
        result = self.run_verify("open-spec-federation")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["replay_orders"], 10)
        self.assertEqual(summary["replay_hashes"], 1)
        self.assertEqual(summary["silent_losses"], 0)
        self.assertEqual(summary["source_log_overwrites"], 0)
        self.assertEqual(summary["last_write_wins_resolutions"], 0)
        self.assertGreaterEqual(summary["visible_conflicts"], 3)
        self.assertGreaterEqual(summary["duplicates_deduplicated"], 1)

    def test_hostile_hub_cannot_gain_cell_authority(self) -> None:
        result = self.run_verify("open-spec-federation")
        summary = json.loads(result.stdout)["summary"]
        self.assertGreaterEqual(summary["hostile_hub_cases"], 5)
        self.assertEqual(summary["false_operator_acceptances"], 0)
        self.assertEqual(summary["hub_decryptions"], 0)
        self.assertEqual(summary["hub_tx_orders"], 0)
        self.assertEqual(summary["forged_cell_events_accepted"], 0)
        self.assertGreaterEqual(summary["unverified_distress_preserved"], 1)

    def test_50k_reference_is_simulation_correctness_not_capacity_claim(self) -> None:
        scale = self.load_json(PROFILES)["scale_reference"]
        self.assertEqual(scale["sites"], 50000)
        self.assertEqual(scale["response_cells"], 60)
        self.assertEqual(scale["operational_areas"], 5)
        self.assertEqual(scale["coordination_hubs"], 2)
        self.assertEqual(
            scale["evidence_scope"], "deterministic_simulation_correctness_only"
        )
        self.assertFalse(scale["capacity_claim"])
        self.assertFalse(scale["field_readiness_claim"])

    def test_mutation_rejects_central_critical_dependency(self) -> None:
        profiles = copy.deepcopy(self.load_json(PROFILES))
        profiles["open_boundary"]["central_service_in_critical_path"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            errors, _, _, _ = run_open_spec_federation_gate(
                ROOT,
                profiles_path=path,
                peer_schema_path=PEER_SCHEMA,
                fixtures_path=FIXTURES,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("critical path" in error for error in errors))

    def test_mutation_rejects_hub_authority(self) -> None:
        profiles = copy.deepcopy(self.load_json(PROFILES))
        profiles["coordination_hubs"]["creates_operator_acceptance"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            errors, _, _, _ = run_open_spec_federation_gate(
                ROOT,
                profiles_path=path,
                peer_schema_path=PEER_SCHEMA,
                fixtures_path=FIXTURES,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("hub" in error.lower() for error in errors))

    def test_residuals_are_governed_without_silently_blocking_publication(self) -> None:
        value = self.load_json(RESIDUALS)
        self.assertEqual(value["task"], "OS-06")
        self.assertGreaterEqual(len(value["residuals"]), 10)
        for row in value["residuals"]:
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

    def test_summary_advances_only_to_os_08(self) -> None:
        result = self.run_verify("open-spec-federation")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 7)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["next_task"], "OS-08")
        self.assertFalse(summary["next_task_started"])
        self.assertFalse(summary["physical_scale_blocks_publication"])

    def test_acceptance_references_a_clean_passing_receipt(self) -> None:
        receipt = self.load_json(RECEIPT)
        acceptance = self.load_json(ACCEPTANCE)
        self.assertEqual(receipt["result"], "passed")
        self.assertFalse(receipt["dirty"])
        self.assertEqual(acceptance["task"], "OS-06")
        self.assertEqual(acceptance["status"], "accepted")
        self.assertEqual(
            acceptance["receipt"]["sha256"],
            __import__("hashlib").sha256(RECEIPT.read_bytes()).hexdigest(),
        )
        self.assertEqual(acceptance["next_task"], "OS-07")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
