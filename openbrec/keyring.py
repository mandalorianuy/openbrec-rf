from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from openbrec.canonical import canonicalize


RECOVERY_AAD = b"openbrec-lab-key-recovery-v1"


class KeyUnavailable(RuntimeError):
    pass


class KeyRollbackDetected(RuntimeError):
    pass


@dataclass
class _KeyEntry:
    material: bytearray
    state: str


class KeyRegistry:
    """Replaceable in-memory key lifecycle for laboratory evidence only."""

    def __init__(
        self,
        entries: dict[str, _KeyEntry],
        *,
        active_key_id: str,
        epoch: int,
        minimum_epoch: int = 0,
    ) -> None:
        if epoch < minimum_epoch:
            raise KeyRollbackDetected(
                f"key epoch {epoch} is older than required epoch {minimum_epoch}"
            )
        if active_key_id not in entries:
            raise KeyUnavailable("active key is missing")
        self._entries = entries
        self.active_key_id = active_key_id
        self.epoch = epoch

    @classmethod
    def single(cls, *, key_id: str, key: bytes, epoch: int) -> KeyRegistry:
        _validate_key(key)
        if not key_id:
            raise KeyUnavailable("key_id is required")
        return cls(
            {key_id: _KeyEntry(bytearray(key), "active")},
            active_key_id=key_id,
            epoch=epoch,
        )

    def active_key(self) -> bytes:
        entry = self._entries.get(self.active_key_id)
        if entry is None or entry.state != "active":
            raise KeyUnavailable("active key is unavailable or not active")
        return bytes(entry.material)

    def resolve(self, key_id: str) -> bytes:
        entry = self._entries.get(key_id)
        if entry is None or entry.state not in {"active", "retired"}:
            raise KeyUnavailable(f"key is unavailable: {key_id}")
        return bytes(entry.material)

    def rotate(self, *, key_id: str, key: bytes, epoch: int) -> None:
        _validate_key(key)
        if epoch <= self.epoch:
            raise KeyRollbackDetected("rotation epoch must increase monotonically")
        if key_id in self._entries:
            raise KeyUnavailable("rotation key_id already exists")
        active = self._entries.get(self.active_key_id)
        if active is None or active.state != "active":
            raise KeyUnavailable("cannot rotate without an active key")
        active.state = "retired"
        self._entries[key_id] = _KeyEntry(bytearray(key), "active")
        self.active_key_id = key_id
        self.epoch = epoch

    def revoke(self, key_id: str) -> None:
        entry = self._entries.get(key_id)
        if entry is None:
            raise KeyUnavailable(f"key is unavailable: {key_id}")
        entry.state = "revoked"

    def zeroize(self, key_id: str) -> None:
        entry = self._entries.pop(key_id, None)
        if entry is None:
            raise KeyUnavailable(f"key is unavailable: {key_id}")
        for index in range(len(entry.material)):
            entry.material[index] = 0

    def export_recovery(self, *, wrapping_key: bytes, nonce: bytes) -> bytes:
        _validate_key(wrapping_key)
        if len(nonce) != 12:
            raise KeyUnavailable("recovery nonce must be 12 bytes")
        payload = {
            "version": 1,
            "epoch": self.epoch,
            "active_key_id": self.active_key_id,
            "keys": [
                {
                    "key_id": key_id,
                    "state": entry.state,
                    "material": base64.b64encode(bytes(entry.material)).decode("ascii"),
                }
                for key_id, entry in sorted(self._entries.items())
            ],
        }
        ciphertext = AESGCM(wrapping_key).encrypt(
            nonce, canonicalize(payload), RECOVERY_AAD
        )
        return nonce + ciphertext

    @classmethod
    def recover(
        cls, blob: bytes, *, wrapping_key: bytes, minimum_epoch: int
    ) -> KeyRegistry:
        _validate_key(wrapping_key)
        if len(blob) < 13:
            raise KeyUnavailable("recovery envelope is truncated")
        try:
            raw = AESGCM(wrapping_key).decrypt(blob[:12], blob[12:], RECOVERY_AAD)
            payload = json.loads(raw)
            entries = {
                item["key_id"]: _KeyEntry(
                    bytearray(base64.b64decode(item["material"], validate=True)),
                    item["state"],
                )
                for item in payload["keys"]
            }
        except Exception as exc:
            if isinstance(exc, KeyRollbackDetected):
                raise
            raise KeyUnavailable("recovery envelope is invalid") from exc
        for entry in entries.values():
            _validate_key(bytes(entry.material))
        return cls(
            entries,
            active_key_id=payload["active_key_id"],
            epoch=int(payload["epoch"]),
            minimum_epoch=minimum_epoch,
        )


def _validate_key(key: bytes) -> None:
    if len(key) != 32:
        raise KeyUnavailable("key material must be exactly 32 bytes")


def load_secret_key(path: Path) -> bytes:
    try:
        encoded = path.read_text(encoding="utf-8").strip()
        key = base64.b64decode(encoded, validate=True)
    except (OSError, ValueError) as exc:
        raise KeyUnavailable(f"key secret is unavailable: {path}") from exc
    _validate_key(key)
    return key
