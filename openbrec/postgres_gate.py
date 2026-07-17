from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openbrec.canonical import canonicalize
from openbrec.postgres_disposition import PostgresDispositionStore
from openbrec.runtime import LAB_INCIDENT_ID, observation_to_event


OBSERVATION = {
    "schema_version": "1.0.0",
    "observation_id": "55555555-5555-4555-8555-555555555555",
    "sensor_id": "synthetic-1",
    "sensor_type": "synthetic",
    "observation_kind": "measurement",
    "window_start": "2026-07-17T12:10:00.000000Z",
    "window_end": "2026-07-17T12:10:01.000000Z",
    "measurements": [
        {
            "measurement_type": "scalar",
            "metric": "synthetic.level",
            "value": 0.25,
            "unit": "1",
            "uncertainty": 0.1,
            "quality": 0.8,
            "method": "postgres gate",
        }
    ],
    "quality": 0.8,
    "uncertainty": 0.2,
    "coverage": "synthetic window",
    "capabilities_absent": ["hardware"],
    "limitations": ["not field evidence"],
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    event = observation_to_event(OBSERVATION)
    policy = event["handling_policy"]
    store = PostgresDispositionStore.from_environment(repository_root=root)
    with store.connection.transaction():
        store.connection.execute(
            "TRUNCATE audit_events, rejection_ledger, evidence_vault, "
            "review_quarantine, accepted_event_log, ingress_units RESTART IDENTITY CASCADE"
        )
    accepted_raw = canonicalize(event)
    store.ingest(accepted_raw, policy=policy, source_offset=event["sequence"])
    store.ingest(b'{"broken":true}', policy=policy, source_offset=1)
    store.ingest(
        b"synthetic possible life safety material",
        policy={**policy, "mode": "life_safety_preservation"},
        source_offset=2,
        incident_id=LAB_INCIDENT_ID,
        life_safety_relevant=True,
    )
    synthetic_secret = b"password=synthetic-do-not-store"
    store.ingest(synthetic_secret, policy=policy, source_offset=3)
    baseline = store.reconcile()
    if baseline != {
        "ingress_units": 4,
        "destinations": {
            "accepted_event_log": 1,
            "review_quarantine": 1,
            "evidence_vault": 1,
            "rejection_ledger": 1,
        },
        "unreconciled": 0,
    }:
        raise RuntimeError(f"baseline reconciliation failed: {baseline}")

    duplicate = store.ingest(
        accepted_raw, policy=policy, source_offset=event["sequence"]
    )
    if duplicate.destination != "accepted_event_log" or store.reconcile() != baseline:
        raise RuntimeError("idempotent duplicate changed disposition state")
    rollback_unit = "f" * 64 + ":999"
    try:
        with store.connection.transaction():
            store.connection.execute(
                "INSERT INTO ingress_units VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    rollback_unit,
                    "f" * 64,
                    999,
                    1,
                    "review_quarantine",
                    policy["accepted_at"],
                ),
            )
            raise RuntimeError("synthetic failure after ingress")
    except RuntimeError:
        pass
    rolled_back = store.connection.execute(
        "SELECT COUNT(*) FROM ingress_units WHERE unit_id = %s", (rollback_unit,)
    ).fetchone()[0]
    rollback = "passed" if rolled_back == 0 else "missed"
    if rollback != "passed" or store.reconcile() != baseline:
        raise RuntimeError("faulted transaction did not roll back atomically")
    store.close()

    restarted = PostgresDispositionStore.from_environment(repository_root=root)
    if restarted.reconcile() != baseline:
        raise RuntimeError("restart changed reconciled disposition state")
    restarted.close()

    def concurrent_ingest(index: int) -> None:
        concurrent = PostgresDispositionStore.from_environment(repository_root=root)
        try:
            concurrent.ingest(
                json.dumps({"broken": index}, sort_keys=True).encode("utf-8"),
                policy=policy,
                source_offset=10 + index,
            )
        finally:
            concurrent.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(concurrent_ingest, (0, 1)))

    final_store = PostgresDispositionStore.from_environment(repository_root=root)
    final = final_store.reconcile()
    cleartext_rows = final_store.connection.execute(
        "SELECT COUNT(*) FROM rejection_ledger WHERE reason LIKE %s",
        ("%synthetic-do-not-store%",),
    ).fetchone()[0]
    final_store.close()
    if final["ingress_units"] != 6 or final["unreconciled"] != 0:
        raise RuntimeError(f"concurrent reconciliation failed: {final}")
    if cleartext_rows:
        raise RuntimeError("rejected synthetic secret persisted in cleartext")
    print(
        json.dumps(
            {
                "baseline": baseline,
                "concurrent_ingress_units": final["ingress_units"],
                "concurrent_unreconciled": final["unreconciled"],
                "migration": "passed",
                "restart": "passed",
                "rollback": rollback,
                "duplicate": "idempotent",
                "secret_cleartext_persisted": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
