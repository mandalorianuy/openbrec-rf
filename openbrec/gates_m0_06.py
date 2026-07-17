from __future__ import annotations

from pathlib import Path
from typing import Any

from openbrec.keyring import (
    KeyRegistry,
    KeyRollbackDetected,
    KeyUnavailable,
)
from openbrec.supply_chain import (
    build_sbom,
    run_license_gate,
    run_secret_scan,
    run_vulnerability_gate,
    write_sbom,
)


def run_key_lifecycle_gate(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    registry = KeyRegistry.single(key_id="lab-key-1", key=b"a" * 32, epoch=1)
    before = registry.export_recovery(wrapping_key=b"w" * 32, nonce=b"1" * 12)
    registry.rotate(key_id="lab-key-2", key=b"b" * 32, epoch=2)
    after = registry.export_recovery(wrapping_key=b"w" * 32, nonce=b"2" * 12)
    recovered = KeyRegistry.recover(after, wrapping_key=b"w" * 32, minimum_epoch=2)
    if recovered.active_key_id != "lab-key-2":
        errors.append("rotated key did not remain active after recovery")
    rollback = "missed"
    try:
        KeyRegistry.recover(before, wrapping_key=b"w" * 32, minimum_epoch=2)
    except KeyRollbackDetected:
        rollback = "detected"
    else:
        errors.append("old key recovery snapshot did not fail closed")
    recovered.revoke("lab-key-2")
    revoked = "missed"
    try:
        recovered.active_key()
    except KeyUnavailable:
        revoked = "denied"
    else:
        errors.append("revoked active key remained usable")
    recovered.zeroize("lab-key-1")
    zeroized = "missed"
    try:
        recovered.resolve("lab-key-1")
    except KeyUnavailable:
        zeroized = "unavailable"
    else:
        errors.append("zeroized key remained resolvable")
    return (
        errors,
        [],
        {
            "profile": "lab_secret_file_replaceable",
            "field_support": "unverified",
            "rotation_epoch": 2,
            "recovery": "passed",
            "rollback": rollback,
            "revoked_key": revoked,
            "zeroized_key": zeroized,
            "embedded_default": False,
        },
    )


__all__ = [
    "build_sbom",
    "run_key_lifecycle_gate",
    "run_license_gate",
    "run_secret_scan",
    "run_vulnerability_gate",
    "write_sbom",
]
