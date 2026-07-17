from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable

import psycopg
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from openbrec.canonical import canonicalize
from openbrec.disposition import (
    SECRET_PATTERN,
    ZERO_INCIDENT,
    DispositionResult,
    _strict_json,
)
from openbrec.keyring import KeyRegistry, KeyUnavailable, load_secret_key
from openbrec.semantic import SemanticValidationError, validate_event


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations/postgresql/0001_m0_disposition.sql"
)


class PostgresDispositionStore:
    def __init__(
        self,
        connection: psycopg.Connection,
        *,
        repository_root: Path,
        key_registry: KeyRegistry,
        nonce_source: Callable[[int], bytes] = os.urandom,
    ) -> None:
        self.connection = connection
        self.repository_root = repository_root
        self.key_registry = key_registry
        self.nonce_source = nonce_source
        self._migrate()

    @classmethod
    def connect(
        cls,
        dsn: str,
        *,
        repository_root: Path,
        key_registry: KeyRegistry,
        nonce_source: Callable[[int], bytes] = os.urandom,
    ) -> PostgresDispositionStore:
        return cls(
            psycopg.connect(dsn),
            repository_root=repository_root,
            key_registry=key_registry,
            nonce_source=nonce_source,
        )

    @classmethod
    def from_environment(cls, *, repository_root: Path) -> PostgresDispositionStore:
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
        key_path = Path(
            os.environ.get(
                "OPENBREC_MASTER_KEY_FILE", "/run/secrets/openbrec_master_key"
            )
        )
        key_id = os.environ.get("OPENBREC_MASTER_KEY_ID", "")
        if not key_id:
            raise RuntimeError("OPENBREC_MASTER_KEY_ID is required")
        try:
            master_key = load_secret_key(key_path)
        except KeyUnavailable:
            if not allow_ephemeral_gate:
                raise RuntimeError(
                    "ephemeral gate secret fallback is not explicitly enabled"
                )
            try:
                import base64

                master_key = base64.b64decode(
                    os.environ.get("OPENBREC_MASTER_KEY_B64", ""), validate=True
                )
            except (ValueError, TypeError) as exc:
                raise RuntimeError("master key secret is unavailable") from exc
            if len(master_key) != 32:
                raise RuntimeError("master key secret is unavailable")
        registry = KeyRegistry.single(
            key_id=key_id,
            key=master_key,
            epoch=int(os.environ.get("OPENBREC_KEY_EPOCH", "1")),
        )
        dsn = (
            f"host={os.environ.get('OPENBREC_POSTGRES_HOST', 'postgres')} "
            f"port={os.environ.get('OPENBREC_POSTGRES_PORT', '5432')} "
            f"dbname={os.environ.get('OPENBREC_POSTGRES_DB', 'openbrec')} "
            f"user={os.environ.get('OPENBREC_POSTGRES_USER', 'openbrec')} "
            f"password={password} connect_timeout=10"
        )
        return cls.connect(dsn, repository_root=repository_root, key_registry=registry)

    def _migrate(self) -> None:
        with self.connection.transaction():
            self.connection.execute(MIGRATION_PATH.read_text(encoding="utf-8"))

    def _encrypt(
        self, raw: bytes, *, incident_id: str, input_sha256: str, destination: str
    ) -> tuple[str, bytes, bytes, bytes]:
        key_id = self.key_registry.active_key_id
        master_key = self.key_registry.active_key()
        nonce = self.nonce_source(12)
        if len(nonce) != 12:
            raise ValueError("AES-GCM nonce source must return 12 bytes")
        key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=uuid.UUID(incident_id).bytes,
            info=b"openbrec-evidence-store-v1",
        ).derive(master_key)
        aad = canonicalize(
            {
                "incident_id": incident_id,
                "input_sha256": input_sha256,
                "destination": destination,
                "key_id": key_id,
                "size_bytes": len(raw),
            }
        )
        return key_id, nonce, AESGCM(key).encrypt(nonce, raw, aad), aad

    def ingest(
        self,
        raw: bytes,
        *,
        policy: dict[str, Any],
        source_offset: int,
        incident_id: str | None = None,
        life_safety_relevant: bool = False,
        authorized_actor: str | None = None,
        reason: str | None = None,
    ) -> DispositionResult:
        input_sha256 = hashlib.sha256(raw).hexdigest()
        unit_id = f"{input_sha256}:{source_offset}"
        errors: list[str] = []
        event: dict[str, Any] | None = None
        try:
            event = validate_event(_strict_json(raw), self.repository_root)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            SemanticValidationError,
        ) as exc:
            errors = getattr(exc, "errors", [str(exc)])

        if event is not None:
            destination = "accepted_event_log"
            incident_id = event["incident_id"]
        elif life_safety_relevant or policy["mode"] == "life_safety_preservation":
            destination = "evidence_vault"
            incident_id = incident_id or ZERO_INCIDENT
        elif SECRET_PATTERN.search(raw):
            destination = "rejection_ledger"
            incident_id = incident_id or ZERO_INCIDENT
        else:
            destination = "review_quarantine"
            incident_id = incident_id or ZERO_INCIDENT

        if policy.get("break_glass") and (not authorized_actor or not reason):
            raise PermissionError("break-glass preservation requires actor and reason")
        trigger_type = (
            "break_glass"
            if policy.get("break_glass")
            else "authorized_actor"
            if authorized_actor
            else "policy"
        )

        with self.connection.transaction():
            inserted = self.connection.execute(
                "INSERT INTO ingress_units VALUES (%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (unit_id) DO NOTHING RETURNING unit_id",
                (
                    unit_id,
                    input_sha256,
                    source_offset,
                    len(raw),
                    destination,
                    policy["accepted_at"],
                ),
            ).fetchone()
            if inserted is None:
                existing = self.connection.execute(
                    "SELECT input_sha256, source_offset, destination "
                    "FROM ingress_units WHERE unit_id = %s",
                    (unit_id,),
                ).fetchone()
                if existing == (input_sha256, source_offset, destination):
                    return DispositionResult(input_sha256, destination, unit_id)
                raise RuntimeError("idempotency collision has incompatible disposition")
            if destination == "accepted_event_log":
                event_jcs = canonicalize(event)
                self.connection.execute(
                    "INSERT INTO accepted_event_log(unit_id,event_sha256,event_jcs,policy_ref) VALUES (%s,%s,%s,%s)",
                    (
                        unit_id,
                        hashlib.sha256(event_jcs).hexdigest(),
                        event_jcs,
                        policy["policy_id"],
                    ),
                )
            elif destination in {"review_quarantine", "evidence_vault"}:
                key_id, nonce, ciphertext, aad = self._encrypt(
                    raw,
                    incident_id=incident_id,
                    input_sha256=input_sha256,
                    destination=destination,
                )
                if destination == "review_quarantine":
                    self.connection.execute(
                        "INSERT INTO review_quarantine VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            unit_id,
                            incident_id,
                            key_id,
                            nonce,
                            ciphertext,
                            aad,
                            json.dumps(sorted(errors)),
                            policy["retention_until"],
                        ),
                    )
                else:
                    self.connection.execute(
                        "INSERT INTO evidence_vault VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            unit_id,
                            input_sha256,
                            incident_id,
                            key_id,
                            nonce,
                            ciphertext,
                            aad,
                            policy["retention_until"],
                            trigger_type,
                            authorized_actor,
                            reason or policy["purpose"],
                            None,
                        ),
                    )
                    self.connection.execute(
                        "INSERT INTO audit_events VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            str(uuid.uuid5(uuid.NAMESPACE_URL, unit_id + ":seal")),
                            input_sha256,
                            policy["accepted_at"],
                            authorized_actor or "handling-policy",
                            "seal",
                            "allowed",
                            reason or policy["purpose"],
                            None,
                        ),
                    )
            else:
                self.connection.execute(
                    "INSERT INTO rejection_ledger VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        unit_id,
                        input_sha256,
                        len(raw),
                        "unrelated_secret",
                        "cleartext persistence unnecessary",
                        "discarded_after_hash",
                    ),
                )
        return DispositionResult(input_sha256, destination, unit_id)

    def reconcile(self) -> dict[str, Any]:
        destinations = {
            "accepted_event_log": 0,
            "review_quarantine": 0,
            "evidence_vault": 0,
            "rejection_ledger": 0,
        }
        rows = self.connection.execute(
            "SELECT destination, COUNT(*) FROM ingress_units GROUP BY destination"
        ).fetchall()
        destinations.update({row[0]: row[1] for row in rows})
        physical = sum(
            self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in destinations
        )
        total = sum(destinations.values())
        return {
            "ingress_units": total,
            "destinations": destinations,
            "unreconciled": abs(total - physical),
        }

    def close(self) -> None:
        self.connection.close()
