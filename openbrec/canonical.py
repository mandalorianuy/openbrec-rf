from __future__ import annotations

import hashlib
import math
from decimal import Decimal
from typing import Any

import rfc8785


class CanonicalizationError(ValueError):
    pass


def _ijson(value: Any) -> Any:
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("JSON object keys must be strings")
        return {key: _ijson(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ijson(item) for item in value]
    if isinstance(value, Decimal):
        if not value.is_finite() or value.is_zero() and value.is_signed():
            raise CanonicalizationError("non-I-JSON decimal")
        if value == value.to_integral_value():
            return _ijson(int(value))
        converted = float(value)
        if not math.isfinite(converted):
            raise CanonicalizationError("decimal outside binary64 range")
        return converted
    if isinstance(value, float):
        if not math.isfinite(value) or value == 0.0 and math.copysign(1.0, value) < 0:
            raise CanonicalizationError("non-I-JSON float")
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > 9_007_199_254_740_991:
            raise CanonicalizationError("integer outside I-JSON safe range")
        return value
    if value is None or isinstance(value, (str, bool)):
        return value
    raise CanonicalizationError(f"unsupported JSON value: {type(value).__name__}")


def canonicalize(value: Any) -> bytes:
    try:
        return rfc8785.dumps(_ijson(value))
    except (rfc8785.CanonicalizationError, UnicodeError, ValueError) as exc:
        if isinstance(exc, CanonicalizationError):
            raise
        raise CanonicalizationError(str(exc)) from exc


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonicalize(value)).hexdigest()
