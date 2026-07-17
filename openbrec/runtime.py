from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.contracts import load_core_schemas, schema_registry


ACCEPTED_OBSERVATION_TOPIC = "openbrec/core/observations/accepted"
PROCESSED_OBSERVATION_TOPIC = "openbrec/core/observations/processed"


class ContractValidationError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@lru_cache(maxsize=1)
def _observation_validator() -> Draft202012Validator:
    root = Path(__file__).resolve().parents[1]
    schemas = load_core_schemas(root)
    schema = next(
        value for value, path in schemas if path.name == "observation.schema.json"
    )
    return Draft202012Validator(
        schema,
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )


def validate_observation(payload: Any) -> dict[str, Any]:
    errors = sorted(
        _observation_validator().iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        messages = [
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        ]
        raise ContractValidationError(messages)
    if not isinstance(payload, dict):
        raise ContractValidationError(["/: observation must be an object"])
    return payload
