from __future__ import annotations

import copy
import json
import os
import sqlite3
import tempfile
import time
from unittest import mock
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.contracts import load_core_schemas, schema_registry
from openbrec.disposition import AccessDenied, DispositionStore, RetentionActive
from openbrec.replay import AdapterReplayRunner, CoreReplayRunner, event_uuid
from openbrec.semantic import adapter_idempotency


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fixture(root: Path, relative: str) -> dict[str, Any]:
    return _load(root / "fixtures/replay" / relative)


def _validate_receipt(root: Path, name: str, receipt: dict[str, Any]) -> list[str]:
    schemas = load_core_schemas(root)
    schema = next(item for item, path in schemas if path.name == name)
    validator = Draft202012Validator(
        schema, registry=schema_registry(schemas), format_checker=FormatChecker()
    )
    return [error.message for error in validator.iter_errors(receipt)]


def _routine_policy() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "policy_id": "urn:openbrec:handling:routine:1.0.0",
        "mode": "routine_minimized",
        "retention_until": "2026-07-18T12:00:00.000000Z",
        "accepted_at": "2026-07-17T12:00:00.000000Z",
        "purpose": "synthetic M0 replay",
        "audit_required": True,
    }


def _life_policy(*, break_glass: bool = False) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "policy_id": "urn:openbrec:handling:life-safety:1.0.0",
        "mode": "life_safety_preservation",
        "retention_until": "2026-07-24T12:00:00.000000Z",
        "accepted_at": "2026-07-17T12:00:00.000000Z",
        "purpose": "preserve potentially life-saving evidence",
        "audit_required": True,
        "break_glass": break_glass,
    }


def run_adapter_replay(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    bundle = _fixture(root, "adapter/synthetic-observation.bundle.json")
    runner = AdapterReplayRunner(root)
    valid = runner.run(bundle)
    corrupt = copy.deepcopy(bundle)
    corrupt["input_sha256"] = "0" * 64
    failed = runner.run(corrupt)
    errors = _validate_receipt(
        root, "adapter-replay-receipt.schema.json", valid.receipt
    )
    errors.extend(
        f"failed receipt: {error}"
        for error in _validate_receipt(
            root, "adapter-replay-receipt.schema.json", failed.receipt
        )
    )
    if valid.receipt["result"] != "passed" or len(valid.events) != 1:
        errors.append("valid adapter bundle did not produce exactly one event")
    if failed.receipt["result"] != "failed" or failed.events:
        errors.append("corrupt adapter bundle did not fail closed")
    return errors, [], {
        "fixture": "fixtures/replay/adapter/synthetic-observation.bundle.json",
        "events_produced": len(valid.events),
        "negative_cases": {"corrupt_fixture_hash": failed.receipt["result"]},
        "adapter_receipt": valid.receipt,
        "failed_adapter_receipt": failed.receipt,
    }


def _core_fixture(root: Path) -> tuple[list[dict[str, Any]], str]:
    bundle = _fixture(root, "core/synthetic-observation.events.json")
    return bundle["events"], bundle["upstream_receipt_sha256"]


def verify_upstream_binding(
    root: Path, events: list[dict[str, Any]], upstream_receipt_sha256: str
) -> list[str]:
    adapter_bundle = _fixture(root, "adapter/synthetic-observation.bundle.json")
    adapter = AdapterReplayRunner(root).run(adapter_bundle)
    errors: list[str] = []
    if adapter.receipt["result"] != "passed":
        errors.append("upstream adapter replay failed")
    if canonical_hash(adapter.receipt) != upstream_receipt_sha256:
        errors.append("upstream adapter receipt hash mismatch")
    if adapter.receipt["normalized_events_sha256"] != canonical_hash(events):
        errors.append("upstream normalized events hash mismatch")
    return errors


def _failure_matrix(root: Path) -> dict[str, str]:
    events, upstream = _core_fixture(root)
    runner = CoreReplayRunner(root)
    event = events[0]
    baseline = runner.run(events, upstream_receipt_sha256=upstream)
    duplicate = runner.run([event, copy.deepcopy(event)], upstream_receipt_sha256=upstream)

    collision = copy.deepcopy(event)
    collision["payload"]["quality"] = 0.1
    collided = runner.run([event, collision], upstream_receipt_sha256=upstream)

    repeated = copy.deepcopy(event)
    repeated["source_event_id"] = "fixture:observation:1"
    repeated["idempotency_id"] = adapter_idempotency(repeated)
    repeated["event_id"] = event_uuid(repeated["idempotency_id"])
    sequence = runner.run([event, repeated], upstream_receipt_sha256=upstream)

    late = copy.deepcopy(event)
    late["received_at"] = "2026-07-19T12:00:00.000000Z"
    late_result = runner.run([late], upstream_receipt_sha256=upstream)

    unknown = copy.deepcopy(event)
    unknown["schema_ref"] = "https://openbrec.org/schemas/core/unknown/1.0.0"
    unknown_result = runner.run([unknown], upstream_receipt_sha256=upstream)
    fusion = next(item for item in baseline.events if item["event_type"] == "fusion_result")
    return {
        "duplicate_identical": (
            "deduplicated"
            if duplicate.receipt["result_sha256"] == baseline.receipt["result_sha256"]
            else "failed"
        ),
        "idempotency_collision": (
            "failed_no_outputs" if collided.receipt["result"] == "failed" and not collided.events else "failed"
        ),
        "sequence_regressive": (
            "failed_no_outputs" if sequence.receipt["result"] == "failed" and not sequence.events else "failed"
        ),
        "late_after_retention": (
            "failed_no_outputs" if late_result.receipt["result"] == "failed" and not late_result.events else "failed"
        ),
        "unknown_schema": (
            "failed_no_outputs" if unknown_result.receipt["result"] == "failed" and not unknown_result.events else "failed"
        ),
        "source_absent": (
            "abstained_with_capability_absent"
            if fusion["payload"]["state"] == "abstained"
            and fusion["payload"]["capabilities_absent"]
            else "failed"
        ),
    }


def run_core_replay(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    events, upstream = _core_fixture(root)
    outcome = CoreReplayRunner(root).run(events, upstream_receipt_sha256=upstream)
    errors = verify_upstream_binding(root, events, upstream)
    errors.extend(
        _validate_receipt(root, "core-replay-receipt.schema.json", outcome.receipt)
    )
    if outcome.receipt["result"] != "passed" or len(outcome.events) != 2:
        errors.append("core replay did not produce evidence and fusion result")
    matrix = _failure_matrix(root)
    expected = {
        item["name"]: item["expected"]
        for item in _fixture(root, "failure-cases.json")["cases"]
        if item["name"] != "corrupt_fixture_hash"
    }
    for name, expectation in expected.items():
        if matrix.get(name) != expectation:
            errors.append(f"failure case {name} did not meet {expectation}")
    return errors, [], {
        "fixture": "fixtures/replay/core/synthetic-observation.events.json",
        "outputs": len(outcome.events),
        "failure_matrix": matrix,
        "core_receipt": outcome.receipt,
    }


def run_determinism(
    root: Path, runs: int
) -> tuple[list[str], list[str], dict[str, Any]]:
    bundle = _fixture(root, "adapter/synthetic-observation.bundle.json")
    second = copy.deepcopy(bundle["observations"][0])
    second["observation_id"] = "55555555-5555-4555-8555-555555555556"
    second["sensor_id"] = "synthetic-2"
    second["window_start"] = "2026-07-17T12:09:00.000000Z"
    second["window_end"] = "2026-07-17T12:09:01.000000Z"
    bundle["observations"].append(second)
    bundle["input_sha256"] = canonical_hash(bundle["observations"])
    adapter = AdapterReplayRunner(root).run(bundle)
    upstream = canonical_hash(adapter.receipt)
    hashes: list[str] = []
    scenarios: list[dict[str, str]] = []
    old_tz, old_locale = os.environ.get("TZ"), os.environ.get("LC_ALL")
    try:
        for index in range(runs):
            tz = "UTC" if index % 2 == 0 else "Pacific/Auckland"
            locale = "C" if index % 2 == 0 else "C.UTF-8"
            os.environ["TZ"] = tz
            os.environ["LC_ALL"] = locale
            if hasattr(time, "tzset"):
                time.tzset()
            ordered = adapter.events if index % 2 == 0 else list(reversed(adapter.events))
            outcome = CoreReplayRunner(root).run(
                copy.deepcopy(ordered), upstream_receipt_sha256=upstream
            )
            hashes.append(outcome.receipt["result_sha256"])
            scenarios.append({"timezone": tz, "locale": locale, "order": "forward" if index % 2 == 0 else "reverse"})
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        if old_locale is None:
            os.environ.pop("LC_ALL", None)
        else:
            os.environ["LC_ALL"] = old_locale
        if hasattr(time, "tzset"):
            time.tzset()
    unique = sorted(set(hashes))
    errors = [] if runs >= 10 and len(unique) == 1 else ["determinism matrix diverged or used fewer than 10 runs"]
    return errors, [], {
        "runs": runs,
        "unique_result_hashes": unique,
        "result_sha256": unique[0] if len(unique) == 1 else None,
        "scenarios": scenarios,
    }


def _store(root: Path, directory: str) -> DispositionStore:
    return DispositionStore(
        Path(directory) / "m0-disposition.db",
        repository_root=root,
        master_key=b"M" * 32,
        nonce_source=os.urandom,
    )


def run_review_quarantine(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    events, _ = _core_fixture(root)
    with tempfile.TemporaryDirectory() as directory:
        store = _store(root, directory)
        store.ingest(canonicalize(events[0]), policy=_routine_policy(), source_offset=0)
        store.ingest(b'{"broken":true}', policy=_routine_policy(), source_offset=1)
        store.ingest(
            b"synthetic possible distress",
            policy=_life_policy(),
            source_offset=2,
            incident_id=events[0]["incident_id"],
            life_safety_relevant=True,
        )
        store.ingest(b"password=synthetic-secret", policy=_routine_policy(), source_offset=3)
        report = store.reconcile()
        errors = [] if report["ingress_units"] == 4 and report["unreconciled"] == 0 and all(report["destinations"].values()) else ["disposition reconciliation failed"]
        return errors, [], report


def run_life_safety_preservation(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    material = b"synthetic potentially life-saving material"
    with tempfile.TemporaryDirectory() as directory:
        store = _store(root, directory)
        try:
            store.ingest(material, policy=_life_policy(break_glass=True), source_offset=0, life_safety_relevant=True)
            errors.append("unauthorized break-glass was accepted")
        except AccessDenied:
            pass
        result = store.ingest(
            material,
            policy=_life_policy(break_glass=True),
            source_offset=1,
            incident_id="11111111-1111-4111-8111-111111111111",
            life_safety_relevant=True,
            authorized_actor="incident-commander",
            reason="possible distress requires preservation",
        )
        accessed = store.access_vault(
            result.input_sha256,
            actor="reviewer-1",
            purpose="life safety review",
            accessed_at=datetime(2026, 7, 18, tzinfo=UTC),
        )
        if accessed != material:
            errors.append("authorized vault access did not recover material")
        try:
            store.delete_vault(
                result.input_sha256,
                actor="reviewer-1",
                reviewer="reviewer-2",
                reason="test",
                deleted_at=datetime(2026, 7, 23, tzinfo=UTC),
            )
            errors.append("active retention was bypassed")
        except RetentionActive:
            pass
        deletion = store.delete_vault(
            result.input_sha256,
            actor="reviewer-1",
            reviewer="reviewer-2",
            reason="retention expired and reviewed",
            deleted_at=datetime(2026, 7, 25, tzinfo=UTC),
        )
        audit_events = store.audit_count(result.input_sha256)
        if audit_events < 4:
            errors.append("vault lifecycle was not fully audited")
        return errors, [], {
            "break_glass_without_actor": "denied",
            "authorized_access": "passed",
            "active_ttl_delete": "denied",
            "reviewed_deletion": "passed",
            "deletion_receipt_sha256": deletion["deletion_receipt_sha256"],
            "audit_events": audit_events,
            "field_support": "unverified",
        }


def run_privacy(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    secret = b"password=synthetic-secret-never-clear"
    vital = b"synthetic vital bytes never clear"
    with tempfile.TemporaryDirectory() as directory:
        store = _store(root, directory)
        ledger = store.ingest(secret, policy=_routine_policy(), source_offset=0)
        vault = store.ingest(
            vital,
            policy=_life_policy(),
            source_offset=1,
            incident_id="11111111-1111-4111-8111-111111111111",
            life_safety_relevant=True,
        )
        database = (Path(directory) / "m0-disposition.db").read_bytes()
        clear_secret = secret in database
        clear_vital = vital in database
        errors = [] if ledger.destination == "rejection_ledger" and vault.destination == "evidence_vault" and not clear_secret and not clear_vital else ["privacy boundary retained clear sensitive bytes"]
        return errors, [], {
            "secret_destination": ledger.destination,
            "life_safety_destination": vault.destination,
            "clear_secret_matches": int(clear_secret),
            "clear_vital_matches": int(clear_vital),
        }


def run_security(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    bundle = _fixture(root, "adapter/synthetic-observation.bundle.json")
    tampered = copy.deepcopy(bundle)
    tampered["observations"][0]["quality"] = 0.01
    adapter = AdapterReplayRunner(root).run(tampered)
    if adapter.receipt["result"] != "failed" or adapter.events:
        errors.append("tampered adapter fixture did not fail closed")
    matrix = _failure_matrix(root)
    if matrix["idempotency_collision"] != "failed_no_outputs":
        errors.append("idempotency collision did not fail closed")

    dependency_probe = "passed"
    try:
        with (
            mock.patch("socket.socket", side_effect=AssertionError("network consulted")),
            mock.patch("time.time", side_effect=AssertionError("clock consulted")),
            mock.patch("os.urandom", side_effect=AssertionError("randomness consulted")),
        ):
            probe_adapter = AdapterReplayRunner(root).run(bundle)
            probe_core = CoreReplayRunner(root).run(
                probe_adapter.events,
                upstream_receipt_sha256=canonical_hash(probe_adapter.receipt),
            )
            if probe_adapter.receipt["result"] != "passed" or probe_core.receipt["result"] != "passed":
                raise AssertionError("replay dependency probe did not pass")
    except AssertionError as exc:
        errors.append(str(exc))
        dependency_probe = "failed"

    duplicate_keys = b'{"schema_version":"1.0.0","schema_version":"1.0.0"}'
    material = b"synthetic encrypted material"
    with tempfile.TemporaryDirectory() as directory:
        store = _store(root, directory)
        duplicate = store.ingest(duplicate_keys, policy=_routine_policy(), source_offset=0)
        vault = store.ingest(
            material,
            policy=_life_policy(),
            source_offset=1,
            incident_id="11111111-1111-4111-8111-111111111111",
            life_safety_relevant=True,
        )
        row = store.connection.execute(
            "SELECT ciphertext FROM evidence_vault WHERE input_sha256 = ?",
            (vault.input_sha256,),
        ).fetchone()
        changed = bytes([row[0][0] ^ 1]) + row[0][1:]
        with store.connection:
            store.connection.execute(
                "UPDATE evidence_vault SET ciphertext = ? WHERE input_sha256 = ?",
                (sqlite3.Binary(changed), vault.input_sha256),
            )
        try:
            store.access_vault(
                vault.input_sha256,
                actor="reviewer-1",
                purpose="tamper test",
                accessed_at=datetime(2026, 7, 18, tzinfo=UTC),
            )
            errors.append("tampered vault ciphertext decrypted")
            tamper = "accepted"
        except InvalidTag:
            tamper = "rejected"
        if duplicate.destination != "review_quarantine":
            errors.append("duplicate JSON keys were not quarantined")
    return errors, [], {
        "tampered_fixture": adapter.receipt["result"],
        "idempotency_collision": matrix["idempotency_collision"],
        "duplicate_json_keys": duplicate.destination,
        "tampered_ciphertext": tamper,
        "network_host_clock_randomness_probe": dependency_probe,
    }
