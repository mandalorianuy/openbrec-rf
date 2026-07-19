from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg

from openbrec.canonical import canonicalize
from openbrec.fusion import EVIDENCE_LOOKBACK_S
from openbrec.semantic import parse_timestamp


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations/postgresql/0002_fusion_results.sql"
)


class FusionStoreError(RuntimeError):
    pass


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def dsn_from_environment() -> str:
    allow_ephemeral_gate = (
        os.environ.get("OPENBREC_ALLOW_EPHEMERAL_GATE_SECRETS") == "1"
    )
    password_path = Path(
        os.environ.get(
            "OPENBREC_POSTGRES_PASSWORD_FILE", "/run/secrets/postgres_password"
        )
    )
    try:
        password = password_path.read_text(encoding="utf-8").strip()
    except OSError:
        if not allow_ephemeral_gate:
            raise RuntimeError(
                "ephemeral gate secret fallback is not explicitly enabled"
            )
        password = os.environ.get("OPENBREC_POSTGRES_PASSWORD", "")
    if not password:
        raise RuntimeError("PostgreSQL password secret is unavailable")
    return (
        f"host={os.environ.get('OPENBREC_POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('OPENBREC_POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('OPENBREC_POSTGRES_DB', 'openbrec')} "
        f"user={os.environ.get('OPENBREC_POSTGRES_USER', 'openbrec')} "
        f"password={password} connect_timeout=10"
    )


def _window_bounds(
    window_start: str, window_end: str, lookback_s: int
) -> tuple[str, str]:
    start = parse_timestamp(window_start) - timedelta(seconds=lookback_s)
    end = parse_timestamp(window_end) + timedelta(seconds=lookback_s)
    return _timestamp(start), _timestamp(end)


def _observation_columns(
    observation: dict[str, Any], recorded_at: str
) -> dict[str, Any]:
    return {
        "observation_id": observation["observation_id"],
        "sensor_id": observation["sensor_id"],
        "sensor_type": observation["sensor_type"],
        "observation_kind": observation["observation_kind"],
        "zone_id": observation.get("zone_id"),
        "quality": observation["quality"],
        "uncertainty": observation["uncertainty"],
        "window_start": observation["window_start"],
        "window_end": observation["window_end"],
        "payload": observation,
        "recorded_at": recorded_at,
    }


def _result_columns(result: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    return {
        "result_id": result["result_id"],
        "state": result["state"],
        "zone_id": result.get("zone_id"),
        "window_start": result["window_start"],
        "window_end": result["window_end"],
        "payload": result,
        "recorded_at": recorded_at,
    }


class InMemoryFusionStore:
    """Ephemeral read model for tests and offline replay."""

    def __init__(self) -> None:
        self._observations: dict[str, dict[str, Any]] = {}
        self._results: dict[str, dict[str, Any]] = {}

    @property
    def ready(self) -> bool:
        return True

    def connect(self) -> None:
        return None

    def close(self) -> None:
        return None

    def record_observation(self, observation: dict[str, Any]) -> None:
        row = _observation_columns(observation, _timestamp())
        existing = self._observations.get(row["observation_id"])
        if existing is not None:
            if existing["payload"] != row["payload"]:
                raise FusionStoreError(
                    "observation idempotency collision has incompatible payload"
                )
            return
        self._observations[row["observation_id"]] = row

    def observations_in_window(
        self,
        zone_id: str | None,
        window_start: str,
        window_end: str,
        *,
        lookback_s: int = EVIDENCE_LOOKBACK_S,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        start, end = _window_bounds(window_start, window_end, lookback_s)
        rows = [
            row
            for row in self._observations.values()
            if row["zone_id"] == zone_id
            and row["window_end"] >= start
            and row["window_start"] <= end
        ]
        rows.sort(key=lambda row: (row["window_start"], row["observation_id"]))
        return [row["payload"] for row in rows[:limit]]

    def record_fusion_result(self, result: dict[str, Any]) -> None:
        row = _result_columns(result, _timestamp())
        existing = self._results.get(row["result_id"])
        if existing is not None:
            if existing["payload"] != row["payload"]:
                raise FusionStoreError(
                    "fusion result idempotency collision has incompatible payload"
                )
            return
        self._results[row["result_id"]] = row

    def list_observations(
        self,
        *,
        zone_id: str | None = None,
        sensor_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        rows = list(self._observations.values())
        if zone_id is not None:
            rows = [row for row in rows if row["zone_id"] == zone_id]
        if sensor_type is not None:
            rows = [row for row in rows if row["sensor_type"] == sensor_type]
        rows.sort(
            key=lambda row: (row["window_start"], row["observation_id"]),
            reverse=True,
        )
        return [row["payload"] for row in rows[:limit]]

    def list_fusion_results(
        self,
        *,
        zone_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        rows = list(self._results.values())
        if zone_id is not None:
            rows = [row for row in rows if row["zone_id"] == zone_id]
        if state is not None:
            rows = [row for row in rows if row["state"] == state]
        rows.sort(
            key=lambda row: (row["window_start"], row["result_id"]), reverse=True
        )
        return [row["payload"] for row in rows[:limit]]

    def get_fusion_result(self, result_id: str) -> dict[str, Any] | None:
        row = self._results.get(result_id)
        return None if row is None else row["payload"]


class PostgresFusionStore:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn
        self.connection: psycopg.Connection | None = None

    @classmethod
    def from_environment(cls) -> PostgresFusionStore:
        return cls()

    @property
    def ready(self) -> bool:
        return self.connection is not None and not self.connection.closed

    def _require_connection(self) -> psycopg.Connection:
        if not self.ready:
            raise FusionStoreError("fusion store is not connected")
        assert self.connection is not None
        return self.connection

    def connect(self) -> None:
        # autocommit keeps read-only SELECTs from leaking an idle transaction
        # that would silently nest later writes into savepoints.
        self.connection = psycopg.connect(
            self.dsn or dsn_from_environment(), autocommit=True
        )
        with self.connection.transaction():
            self.connection.execute(MIGRATION_PATH.read_text(encoding="utf-8"))

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def record_observation(self, observation: dict[str, Any]) -> None:
        row = _observation_columns(observation, _timestamp())
        connection = self._require_connection()
        with connection.transaction():
            inserted = connection.execute(
                "INSERT INTO observations VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (observation_id) DO NOTHING RETURNING observation_id",
                (
                    row["observation_id"],
                    row["sensor_id"],
                    row["sensor_type"],
                    row["observation_kind"],
                    row["zone_id"],
                    row["quality"],
                    row["uncertainty"],
                    row["window_start"],
                    row["window_end"],
                    canonicalize(row["payload"]),
                    row["recorded_at"],
                ),
            ).fetchone()
            if inserted is None:
                existing = connection.execute(
                    "SELECT payload_json FROM observations WHERE observation_id = %s",
                    (row["observation_id"],),
                ).fetchone()
                if existing is None or json.loads(
                    bytes(existing[0])
                ) != row["payload"]:
                    raise FusionStoreError(
                        "observation idempotency collision has incompatible payload"
                    )

    def observations_in_window(
        self,
        zone_id: str | None,
        window_start: str,
        window_end: str,
        *,
        lookback_s: int = EVIDENCE_LOOKBACK_S,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        start, end = _window_bounds(window_start, window_end, lookback_s)
        connection = self._require_connection()
        rows = connection.execute(
            "SELECT payload_json FROM observations "
            "WHERE zone_id IS NOT DISTINCT FROM %s "
            "AND window_end >= %s AND window_start <= %s "
            "ORDER BY window_start, observation_id LIMIT %s",
            (zone_id, start, end, limit),
        ).fetchall()
        return [json.loads(bytes(row[0])) for row in rows]

    def record_fusion_result(self, result: dict[str, Any]) -> None:
        row = _result_columns(result, _timestamp())
        connection = self._require_connection()
        with connection.transaction():
            inserted = connection.execute(
                "INSERT INTO fusion_results VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (result_id) DO NOTHING RETURNING result_id",
                (
                    row["result_id"],
                    row["state"],
                    row["zone_id"],
                    row["window_start"],
                    row["window_end"],
                    canonicalize(row["payload"]),
                    row["recorded_at"],
                ),
            ).fetchone()
            if inserted is None:
                existing = connection.execute(
                    "SELECT result_json FROM fusion_results WHERE result_id = %s",
                    (row["result_id"],),
                ).fetchone()
                if existing is None or json.loads(
                    bytes(existing[0])
                ) != row["payload"]:
                    raise FusionStoreError(
                        "fusion result idempotency collision has incompatible payload"
                    )

    def list_observations(
        self,
        *,
        zone_id: str | None = None,
        sensor_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if zone_id is not None:
            clauses.append("zone_id = %s")
            params.append(zone_id)
        if sensor_type is not None:
            clauses.append("sensor_type = %s")
            params.append(sensor_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        connection = self._require_connection()
        rows = connection.execute(
            f"SELECT payload_json FROM observations {where} "
            "ORDER BY window_start DESC, observation_id DESC LIMIT %s",
            params,
        ).fetchall()
        return [json.loads(bytes(row[0])) for row in rows]

    def list_fusion_results(
        self,
        *,
        zone_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if zone_id is not None:
            clauses.append("zone_id = %s")
            params.append(zone_id)
        if state is not None:
            clauses.append("state = %s")
            params.append(state)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        connection = self._require_connection()
        rows = connection.execute(
            f"SELECT result_json FROM fusion_results {where} "
            "ORDER BY window_start DESC, result_id DESC LIMIT %s",
            params,
        ).fetchall()
        return [json.loads(bytes(row[0])) for row in rows]

    def get_fusion_result(self, result_id: str) -> dict[str, Any] | None:
        connection = self._require_connection()
        row = connection.execute(
            "SELECT result_json FROM fusion_results WHERE result_id = %s",
            (result_id,),
        ).fetchone()
        return None if row is None else json.loads(bytes(row[0]))
