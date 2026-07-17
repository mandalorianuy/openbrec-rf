from __future__ import annotations

import copy
import importlib
import json
import math
import tempfile
import unittest
from unittest import mock
from datetime import UTC, datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_PATH = (
    REPO_ROOT
    / "fixtures/contracts/core/1.0.0/observation/valid/minimal.json"
)


def require_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"required M0-04 module is missing: {relative_path}")
    return importlib.import_module(name)


def observation() -> dict:
    return json.loads(OBSERVATION_PATH.read_text(encoding="utf-8"))


def adapter_bundle(canonical) -> dict:
    observations = [observation()]
    return {
        "bundle_version": "1.0.0",
        "input_sha256": canonical.canonical_hash(observations),
        "adapter": {
            "name": "synthetic",
            "version": "1.0.0",
            "artifact_sha256": "1" * 64,
        },
        "configuration": {
            "source_namespace": "urn:openbrec:adapter:synthetic",
            "incident_id": "11111111-1111-4111-8111-111111111111",
            "deployment_id": "22222222-2222-4222-8222-222222222222",
            "correlation_id": "11111111-1111-4111-8111-111111111111",
            "boot_id": "33333333-3333-4333-8333-333333333333",
            "session_id": "44444444-4444-4444-8444-444444444444",
            "source_node_id": "node-a1b2c3d4",
            "received_at": "2026-07-17T12:10:02.000000Z",
            "configuration_sha256": "2" * 64,
        },
        "contract_set_sha256": "1a8d147e033ecaa0f80df894dbee005c14192b28bfb966d98a4f5b391462f84d",
        "logical_time": "2026-07-17T12:30:00.000000Z",
        "handling_policy": {
            "schema_version": "1.0.0",
            "policy_id": "urn:openbrec:handling:routine:1.0.0",
            "mode": "routine_minimized",
            "retention_until": "2026-07-18T12:00:00.000000Z",
            "accepted_at": "2026-07-17T12:00:00.000000Z",
            "purpose": "synthetic M0 replay",
            "audit_required": True,
        },
        "observations": observations,
    }


class CanonicalizationTests(unittest.TestCase):
    def test_jcs_hash_is_order_independent_and_rejects_non_ijson_numbers(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        self.assertEqual(canonical.canonicalize({"b": 1, "a": 2}), b'{"a":2,"b":1}')
        self.assertEqual(
            canonical.canonical_hash({"b": 1, "a": 2}),
            canonical.canonical_hash({"a": 2, "b": 1}),
        )
        for invalid in (math.nan, math.inf, -math.inf, -0.0):
            with self.assertRaises(canonical.CanonicalizationError):
                canonical.canonicalize({"value": invalid})


class ReplayTests(unittest.TestCase):
    def test_replay_does_not_consult_network_host_clock_or_randomness(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")

        with (
            mock.patch("socket.socket", side_effect=AssertionError("network consulted")),
            mock.patch("time.time", side_effect=AssertionError("clock consulted")),
            mock.patch("os.urandom", side_effect=AssertionError("randomness consulted")),
        ):
            adapter = replay.AdapterReplayRunner(REPO_ROOT).run(
                adapter_bundle(canonical)
            )
            core = replay.CoreReplayRunner(REPO_ROOT).run(
                adapter.events,
                upstream_receipt_sha256=canonical.canonical_hash(adapter.receipt),
            )

        self.assertEqual(adapter.receipt["result"], "passed")
        self.assertEqual(core.receipt["result"], "passed")

    def test_core_fixture_requires_a_matching_adapter_receipt(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        gates = require_module("openbrec.gates_m0_04", "openbrec/gates_m0_04.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        adapter = replay.AdapterReplayRunner(REPO_ROOT).run(adapter_bundle(canonical))

        self.assertEqual(
            gates.verify_upstream_binding(
                REPO_ROOT,
                adapter.events,
                canonical.canonical_hash(adapter.receipt),
            ),
            [],
        )
        self.assertIn(
            "upstream adapter receipt hash mismatch",
            gates.verify_upstream_binding(REPO_ROOT, adapter.events, "0" * 64),
        )

    def test_adapter_builds_semantically_valid_domain_event(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        semantic = require_module("openbrec.semantic", "openbrec/semantic.py")

        outcome = replay.AdapterReplayRunner(REPO_ROOT).run(
            adapter_bundle(canonical)
        )

        self.assertEqual(outcome.receipt["result"], "passed")
        self.assertEqual(len(outcome.events), 1)
        semantic.validate_event(outcome.events[0], REPO_ROOT)
        self.assertEqual(outcome.events[0]["event_type"], "observation")

    def test_adapter_rejects_tampered_fixture_without_outputs(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        bundle = adapter_bundle(canonical)
        bundle["observations"][0]["quality"] = 0.1

        outcome = replay.AdapterReplayRunner(REPO_ROOT).run(bundle)

        self.assertEqual(outcome.receipt["result"], "failed")
        self.assertEqual(outcome.events, [])
        self.assertIn("input hash mismatch", " ".join(outcome.receipt["errors"]))

    def test_core_replay_is_order_independent_and_deduplicates_identical_events(
        self,
    ) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        adapter = replay.AdapterReplayRunner(REPO_ROOT).run(adapter_bundle(canonical))
        event = adapter.events[0]
        runner = replay.CoreReplayRunner(REPO_ROOT)

        once = runner.run([event], upstream_receipt_sha256="3" * 64)
        duplicated = runner.run(
            [copy.deepcopy(event), event], upstream_receipt_sha256="3" * 64
        )

        self.assertEqual(once.receipt["result"], "passed")
        self.assertEqual(once.receipt["result_sha256"], duplicated.receipt["result_sha256"])
        self.assertTrue(any(item["event_type"] == "fusion_result" for item in once.events))
        self.assertEqual(
            next(item for item in once.events if item["event_type"] == "fusion_result")[
                "payload"
            ]["state"],
            "abstained",
        )

    def test_collision_or_regressive_sequence_aborts_all_derived_outputs(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        adapter = replay.AdapterReplayRunner(REPO_ROOT).run(adapter_bundle(canonical))
        event = adapter.events[0]
        collision = copy.deepcopy(event)
        collision["payload"]["quality"] = 0.1

        collided = replay.CoreReplayRunner(REPO_ROOT).run(
            [event, collision], upstream_receipt_sha256="3" * 64
        )

        self.assertEqual(collided.receipt["result"], "failed")
        self.assertEqual(collided.events, [])
        self.assertIn("idempotency collision", " ".join(collided.receipt["errors"]))

        second = copy.deepcopy(event)
        second["idempotency_id"] = "urn:sha256:" + "9" * 64
        second["event_id"] = replay.event_uuid(second["idempotency_id"])
        second["sequence"] = event["sequence"] - 1
        regressive = replay.CoreReplayRunner(REPO_ROOT).run(
            [event, second], upstream_receipt_sha256="3" * 64
        )
        self.assertEqual(regressive.receipt["result"], "failed")
        self.assertEqual(regressive.events, [])


class DispositionTests(unittest.TestCase):
    def test_disposition_schema_is_loaded_from_versioned_migration(self) -> None:
        disposition = require_module("openbrec.disposition", "openbrec/disposition.py")
        migration = REPO_ROOT / "migrations/0001_m0_disposition.sql"

        self.assertTrue(migration.is_file())
        self.assertEqual(disposition.MIGRATION_PATH, migration)

        with tempfile.TemporaryDirectory() as directory:
            store = disposition.DispositionStore(
                Path(directory) / "disposition.db",
                repository_root=REPO_ROOT,
                master_key=b"k" * 32,
            )
            tables = {
                row[0]
                for row in store.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(
                {
                    "ingress_units",
                    "accepted_event_log",
                    "review_quarantine",
                    "evidence_vault",
                    "rejection_ledger",
                    "audit_events",
                }.issubset(tables)
            )

    def test_every_input_reconciles_to_exactly_one_primary_destination(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        replay = require_module("openbrec.replay", "openbrec/replay.py")
        disposition = require_module("openbrec.disposition", "openbrec/disposition.py")
        event = replay.AdapterReplayRunner(REPO_ROOT).run(
            adapter_bundle(canonical)
        ).events[0]
        policy = adapter_bundle(canonical)["handling_policy"]
        incident_id = event["incident_id"]

        with tempfile.TemporaryDirectory() as directory:
            store = disposition.DispositionStore(
                Path(directory) / "disposition.db",
                repository_root=REPO_ROOT,
                master_key=b"k" * 32,
                nonce_source=lambda size: b"n" * size,
            )
            store.ingest(canonical.canonicalize(event), policy=policy, source_offset=0)
            store.ingest(b'{"broken":true}', policy=policy, source_offset=1)
            store.ingest(
                b"possible life safety material",
                policy={**policy, "mode": "life_safety_preservation"},
                source_offset=2,
                incident_id=incident_id,
                life_safety_relevant=True,
            )
            secret = b"password=synthetic-do-not-store"
            store.ingest(secret, policy=policy, source_offset=3)

            report = store.reconcile()
            self.assertEqual(report["ingress_units"], 4)
            self.assertEqual(
                report["destinations"],
                {
                    "accepted_event_log": 1,
                    "review_quarantine": 1,
                    "evidence_vault": 1,
                    "rejection_ledger": 1,
                },
            )
            self.assertEqual(report["unreconciled"], 0)
            self.assertNotIn(secret, (Path(directory) / "disposition.db").read_bytes())

    def test_vault_requires_audited_access_ttl_and_reviewed_deletion(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        disposition = require_module("openbrec.disposition", "openbrec/disposition.py")
        incident_id = "11111111-1111-4111-8111-111111111111"
        accepted = datetime(2026, 7, 17, 12, tzinfo=UTC)
        retention = accepted + timedelta(days=7)
        policy = {
            "schema_version": "1.0.0",
            "policy_id": "urn:openbrec:handling:life-safety:1.0.0",
            "mode": "life_safety_preservation",
            "retention_until": retention.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
            "accepted_at": accepted.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
            "purpose": "preserve possible life safety evidence",
            "audit_required": True,
        }
        material = b"synthetic possibly vital bytes"

        with tempfile.TemporaryDirectory() as directory:
            store = disposition.DispositionStore(
                Path(directory) / "vault.db",
                repository_root=REPO_ROOT,
                master_key=b"k" * 32,
                nonce_source=lambda size: b"q" * size,
            )
            result = store.ingest(
                material,
                policy=policy,
                source_offset=0,
                incident_id=incident_id,
                life_safety_relevant=True,
            )
            self.assertEqual(result.destination, "evidence_vault")
            self.assertNotIn(material, (Path(directory) / "vault.db").read_bytes())

            with self.assertRaises(disposition.AccessDenied):
                store.access_vault(result.input_sha256, actor="", purpose="review")
            self.assertEqual(
                store.access_vault(
                    result.input_sha256, actor="reviewer-1", purpose="life safety review"
                ),
                material,
            )
            with self.assertRaises(disposition.RetentionActive):
                store.delete_vault(
                    result.input_sha256,
                    actor="reviewer-1",
                    reviewer="reviewer-2",
                    reason="expired",
                    deleted_at=retention - timedelta(seconds=1),
                )
            deletion = store.delete_vault(
                result.input_sha256,
                actor="reviewer-1",
                reviewer="reviewer-2",
                reason="retention expired and reviewed",
                deleted_at=retention + timedelta(seconds=1),
            )
            self.assertEqual(len(deletion["deletion_receipt_sha256"]), 64)
            self.assertGreaterEqual(store.audit_count(result.input_sha256), 3)


if __name__ == "__main__":
    unittest.main()
