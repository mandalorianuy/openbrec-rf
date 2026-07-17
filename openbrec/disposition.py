from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.semantic import SemanticValidationError, parse_timestamp, validate_event


ZERO_INCIDENT = "00000000-0000-4000-8000-000000000000"
MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations/0001_m0_disposition.sql"
SECRET_PATTERN = re.compile(
    rb"(?:password\s*=|api[_-]?key\s*=|token\s*=|BEGIN (?:RSA |EC )?PRIVATE KEY)",
    re.IGNORECASE,
)


class AccessDenied(PermissionError):
    pass


class RetentionActive(RuntimeError):
    pass


@dataclass(frozen=True)
class DispositionResult:
    input_sha256: str
    destination: str
    unit_id: str


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(UTC)
    return current.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _strict_json(raw: bytes) -> Any:
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"duplicate JSON property: {key}")
            result[key] = value
        return result

    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)


class DispositionStore:
    def __init__(
        self,
        path: Path,
        *,
        repository_root: Path,
        master_key: bytes,
        nonce_source: Callable[[int], bytes] = os.urandom,
    ) -> None:
        if len(master_key) != 32:
            raise ValueError("master_key must be 32 bytes")
        self.path = path
        self.repository_root = repository_root
        self.master_key = master_key
        self.nonce_source = nonce_source
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(MIGRATION_PATH.read_text(encoding="utf-8"))
        self.connection.commit()

    def _key(self, incident_id: str) -> bytes:
        salt = uuid.UUID(incident_id).bytes
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"openbrec-evidence-store-v1",
        ).derive(self.master_key)

    def _encrypt(
        self, raw: bytes, *, incident_id: str, input_sha256: str, destination: str
    ) -> tuple[bytes, bytes, bytes]:
        nonce = self.nonce_source(12)
        if len(nonce) != 12:
            raise ValueError("AES-GCM nonce source must return 12 bytes")
        aad = canonicalize(
            {
                "incident_id": incident_id,
                "input_sha256": input_sha256,
                "destination": destination,
                "size_bytes": len(raw),
            }
        )
        return nonce, AESGCM(self._key(incident_id)).encrypt(nonce, raw, aad), aad

    def _audit(
        self,
        input_sha256: str,
        *,
        actor: str,
        action: str,
        result: str,
        reason: str,
        occurred_at: datetime | None = None,
        receipt_sha256: str | None = None,
    ) -> None:
        material = {
            "input_sha256": input_sha256,
            "actor": actor,
            "action": action,
            "result": result,
            "reason": reason,
            "occurred_at": _timestamp(occurred_at),
            "receipt_sha256": receipt_sha256,
        }
        audit_id = str(uuid.uuid5(uuid.NAMESPACE_URL, canonical_hash(material)))
        self.connection.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                audit_id,
                input_sha256,
                material["occurred_at"],
                actor or "unknown",
                action,
                result,
                reason,
                receipt_sha256,
            ),
        )

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
            candidate = _strict_json(raw)
            event = validate_event(candidate, self.repository_root)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, SemanticValidationError) as exc:
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

        if policy.get("break_glass"):
            if not authorized_actor or not reason:
                raise AccessDenied("break-glass preservation requires actor and reason")
            trigger_type = "break_glass"
        elif authorized_actor:
            trigger_type = "authorized_actor"
        else:
            trigger_type = "policy"

        recorded_at = policy["accepted_at"]
        with self.connection:
            self.connection.execute(
                "INSERT INTO ingress_units VALUES (?, ?, ?, ?, ?, ?)",
                (
                    unit_id,
                    input_sha256,
                    source_offset,
                    len(raw),
                    destination,
                    recorded_at,
                ),
            )
            if destination == "accepted_event_log":
                event_jcs = canonicalize(event)
                self.connection.execute(
                    "INSERT INTO accepted_event_log(unit_id,event_sha256,event_jcs,policy_ref) VALUES (?,?,?,?)",
                    (unit_id, hashlib.sha256(event_jcs).hexdigest(), event_jcs, policy["policy_id"]),
                )
            elif destination == "review_quarantine":
                nonce, ciphertext, aad = self._encrypt(
                    raw,
                    incident_id=incident_id,
                    input_sha256=input_sha256,
                    destination=destination,
                )
                self.connection.execute(
                    "INSERT INTO review_quarantine VALUES (?,?,?,?,?,?,?)",
                    (
                        unit_id,
                        incident_id,
                        nonce,
                        ciphertext,
                        aad,
                        json.dumps(sorted(errors)),
                        policy["retention_until"],
                    ),
                )
            elif destination == "evidence_vault":
                nonce, ciphertext, aad = self._encrypt(
                    raw,
                    incident_id=incident_id,
                    input_sha256=input_sha256,
                    destination=destination,
                )
                self.connection.execute(
                    "INSERT INTO evidence_vault VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        unit_id,
                        input_sha256,
                        incident_id,
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
                self._audit(
                    input_sha256,
                    actor=authorized_actor or "handling-policy",
                    action="seal",
                    result="allowed",
                    reason=reason or policy["purpose"],
                    occurred_at=parse_timestamp(policy["accepted_at"]),
                )
            else:
                self.connection.execute(
                    "INSERT INTO rejection_ledger VALUES (?,?,?,?,?,?)",
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
        ingress = self.connection.execute(
            "SELECT destination, COUNT(*) AS count FROM ingress_units GROUP BY destination"
        ).fetchall()
        destinations = {
            "accepted_event_log": 0,
            "review_quarantine": 0,
            "evidence_vault": 0,
            "rejection_ledger": 0,
        }
        destinations.update({row["destination"]: row["count"] for row in ingress})
        total = sum(destinations.values())
        physical = sum(
            self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in destinations
        )
        return {
            "ingress_units": total,
            "destinations": destinations,
            "unreconciled": abs(total - physical),
        }

    def access_vault(
        self,
        input_sha256: str,
        *,
        actor: str,
        purpose: str,
        accessed_at: datetime | None = None,
    ) -> bytes:
        row = self.connection.execute(
            "SELECT * FROM evidence_vault WHERE input_sha256 = ?", (input_sha256,)
        ).fetchone()
        if row is None or row["ciphertext"] is None:
            raise KeyError(input_sha256)
        when = accessed_at or datetime.now(UTC)
        if not actor or not purpose or when > parse_timestamp(row["retention_until"]):
            with self.connection:
                self._audit(
                    input_sha256,
                    actor=actor or "unknown",
                    action="read",
                    result="denied",
                    reason=purpose or "missing actor or purpose",
                    occurred_at=when,
                )
            raise AccessDenied("vault access requires actor, purpose and active TTL")
        plaintext = AESGCM(self._key(row["incident_id"])).decrypt(
            row["nonce"], row["ciphertext"], row["aad"]
        )
        with self.connection:
            self._audit(
                input_sha256,
                actor=actor,
                action="read",
                result="allowed",
                reason=purpose,
                occurred_at=when,
            )
        return plaintext

    def delete_vault(
        self,
        input_sha256: str,
        *,
        actor: str,
        reviewer: str,
        reason: str,
        deleted_at: datetime,
    ) -> dict[str, str]:
        row = self.connection.execute(
            "SELECT * FROM evidence_vault WHERE input_sha256 = ?", (input_sha256,)
        ).fetchone()
        if row is None or row["ciphertext"] is None:
            raise KeyError(input_sha256)
        if deleted_at <= parse_timestamp(row["retention_until"]):
            with self.connection:
                self._audit(
                    input_sha256,
                    actor=actor,
                    action="delete",
                    result="denied",
                    reason="retention active",
                    occurred_at=deleted_at,
                )
            raise RetentionActive("retention is still active")
        if not actor or not reviewer or actor == reviewer or not reason:
            raise AccessDenied("deletion requires distinct actor/reviewer and reason")
        receipt = {
            "input_sha256": input_sha256,
            "ciphertext_sha256": hashlib.sha256(row["ciphertext"]).hexdigest(),
            "deleted_at": _timestamp(deleted_at),
            "actor": actor,
            "reviewer": reviewer,
            "reason": reason,
        }
        receipt_sha256 = canonical_hash(receipt)
        with self.connection:
            self.connection.execute(
                "UPDATE evidence_vault SET ciphertext = NULL, deletion_receipt_sha256 = ? WHERE input_sha256 = ?",
                (receipt_sha256, input_sha256),
            )
            self._audit(
                input_sha256,
                actor=actor,
                action="delete",
                result="allowed",
                reason=reason,
                occurred_at=deleted_at,
                receipt_sha256=receipt_sha256,
            )
        return {**receipt, "deletion_receipt_sha256": receipt_sha256}

    def audit_count(self, input_sha256: str) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE input_sha256 = ?",
                (input_sha256,),
            ).fetchone()[0]
        )
