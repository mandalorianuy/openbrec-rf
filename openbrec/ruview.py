from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from openbrec.canonical import canonical_hash


CAMPAIGN_PATH = Path("fixtures/replay/ruview/model-format-campaign.json")
RVF_BINARY_MAGIC = b"RVFS"
JSONL_FALLBACK = (
    "fallback: declare model_version.format=jsonl-rvf and route through the "
    "declared sidecar loader; never return a silent null"
)
GENERIC_FALLBACK = (
    "fallback: declare the model unusable and keep the baseline-without-model "
    "path; never return a silent null"
)


class RvModelFormatError(ValueError):
    pass


def inspect_model_format(raw: bytes) -> dict[str, Any]:
    """Verify the format magic of a RuView RVF model artifact.

    This is a format verifier, not a hardware adapter: it never loads or
    executes the model. A JSONL-distributed model against a binary RVF loader
    must surface a typed, visible error with a declared fallback — the
    upstream gap is `invalid magic` followed by a silent null output.
    """
    if not raw:
        raise RvModelFormatError(f"invalid magic: empty model artifact; {GENERIC_FALLBACK}")
    if raw[: len(RVF_BINARY_MAGIC)] == RVF_BINARY_MAGIC:
        return {
            "accepted": True,
            "format": "rvf-binary",
            "model_sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "fallback": None,
        }
    if raw.lstrip()[:1] in (b"{", b"["):
        raise RvModelFormatError(
            "invalid magic: distributed model is JSONL RVF but the loader "
            f"expects RVF binary magic {RVF_BINARY_MAGIC.decode('ascii')}; "
            f"{JSONL_FALLBACK}"
        )
    raise RvModelFormatError(
        f"invalid magic: {raw[: len(RVF_BINARY_MAGIC)]!r} does not match RVF "
        f"binary magic {RVF_BINARY_MAGIC.decode('ascii')}; {GENERIC_FALLBACK}"
    )


def run_ruview_model_gate(root: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        campaign = json.loads((root / CAMPAIGN_PATH).read_text(encoding="utf-8"))
        if campaign.get("campaign_version") != "1.0.0":
            raise RvModelFormatError("campaign_version must be 1.0.0")
        if campaign.get("claim_scope") != "deterministic_simulation_only":
            raise RvModelFormatError("campaign must remain deterministic simulation only")
        results = []
        for case in sorted(campaign["cases"], key=lambda item: item["case_id"]):
            raw = (root / case["path"]).read_bytes()
            try:
                verdict = inspect_model_format(raw)
                outcome = {
                    "case_id": case["case_id"],
                    "result": "accepted",
                    "format": verdict["format"],
                    "model_sha256": verdict["model_sha256"],
                    "error_type": None,
                    "fallback_declared": None,
                }
            except RvModelFormatError as exc:
                outcome = {
                    "case_id": case["case_id"],
                    "result": "rejected",
                    "format": None,
                    "model_sha256": None,
                    "error_type": type(exc).__name__,
                    "fallback_declared": "fallback:" in str(exc)
                    and "silent null" in str(exc),
                }
            results.append(outcome)
    except (OSError, json.JSONDecodeError, RvModelFormatError) as exc:
        return [str(exc)], [], {"campaign": str(CAMPAIGN_PATH)}

    errors: list[str] = []
    expected = {case["case_id"]: case["expected"] for case in campaign["cases"]}
    for item in results:
        if item["result"] != expected[item["case_id"]]:
            errors.append(
                f"{item['case_id']} derived {item['result']} != "
                f"{expected[item['case_id']]}"
            )
        if item["result"] == "rejected":
            if item["error_type"] != "RvModelFormatError":
                errors.append(f"{item['case_id']} did not fail with a typed error")
            if not item["fallback_declared"]:
                errors.append(f"{item['case_id']} has no visible declared fallback")
    summary = {
        "campaign": str(CAMPAIGN_PATH),
        "claim_scope": campaign["claim_scope"],
        "cases": len(results),
        "accepted": sum(item["result"] == "accepted" for item in results),
        "rejected": sum(item["result"] == "rejected" for item in results),
        "silent_null_returns": 0,
        "results": results,
        "result_sha256": canonical_hash(
            {
                "campaign": canonical_hash(
                    {
                        key: value
                        for key, value in campaign.items()
                        if key != "expected_result_sha256"
                    }
                ),
                "results": results,
            }
        ),
    }
    frozen = campaign.get("expected_result_sha256")
    if frozen != "TBD" and frozen != summary["result_sha256"]:
        errors.append("ruview model format result does not match frozen expected hash")
    return errors, [], summary
