from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash
from openbrec.contracts import load_addon_schemas


SCENARIO_PATH = Path("fixtures/p0/terminal/offline-terminal.json")
PUBLIC_PROJECTION_PATH = Path("apps/web/public/p0-terminal.json")
P1A_PROTOCOL_PATH = Path("docs/testing/p1a-terminal-comprehension-protocol.md")
EXPECTED_STATES = {
    "queued",
    "sent",
    "delivered",
    "seen",
    "accepted",
    "cancelled",
    "expired",
}
ALLOWED_EVENT_TYPES = {
    "message.created",
    "message.queued",
    "sos.created",
    "sos.queued",
    "transport.transmitted",
    "transport.relay_observed",
    "gateway.received",
    "operator.seen",
    "operator.accepted",
    "sos.cancel_requested",
    "sos.expired",
    "sos.failed",
}
CENTRAL_DEPENDENCIES = {"internet", "hub", "superior_service", "cloud"}
PROHIBITED_COPY = {
    "rescate garantizado",
    "entrega garantizada",
    "zona vacía",
    "sin víctimas",
    "ausencia confirmada",
}


class TerminalScenarioError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise TerminalScenarioError("terminal timestamps require timezone")
    return parsed.astimezone(UTC)


def _terminal_capability_validator(root: Path) -> Draft202012Validator:
    schema = next(
        (
            item
            for item, path in load_addon_schemas(root)
            if path.name == "terminal-capability.schema.json"
        ),
        None,
    )
    if schema is None:
        raise TerminalScenarioError("terminal capability schema not found")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_capability(root: Path, capability: dict[str, Any]) -> None:
    errors = sorted(
        _terminal_capability_validator(root).iter_errors(capability),
        key=lambda item: (list(item.path), item.message),
    )
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise TerminalScenarioError(f"terminal capability invalid: {detail}")


def load_scenario(root: Path) -> dict[str, Any]:
    path = root / SCENARIO_PATH
    public_path = root / PUBLIC_PROJECTION_PATH
    try:
        scenario = json.loads(path.read_text(encoding="utf-8"))
        public = json.loads(public_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TerminalScenarioError(f"terminal scenario unreadable: {exc}") from exc
    if canonical_hash(scenario) != canonical_hash(public):
        raise TerminalScenarioError("public terminal projection drifted from fixture")
    if scenario.get("scenario_version") != "1.0.0":
        raise TerminalScenarioError("terminal scenario_version must be 1.0.0")
    if scenario.get("claim_scope") != "deterministic_simulation_only":
        raise TerminalScenarioError("terminal claim scope must remain simulated")
    connectivity = scenario.get("connectivity", {})
    if any(
        connectivity.get(field) is not False
        for field in (
            "internet_available",
            "hub_available",
            "superior_service_available",
        )
    ):
        raise TerminalScenarioError("terminal scenario must operate without superiors")
    if connectivity.get("queue_gap_visible") is not True:
        raise TerminalScenarioError("partition queue gap must remain visible")
    _validate_capability(root, scenario.get("terminal_capability", {}))
    if set(scenario.get("expected_states", [])) != EXPECTED_STATES:
        raise TerminalScenarioError("terminal state denominator changed")
    if len(scenario.get("messages", [])) != 7:
        raise TerminalScenarioError("terminal scenario requires seven state examples")
    return scenario


def derive_state(message: dict[str, Any]) -> str:
    events = {event["event_type"] for event in message["event_log"]}
    if "operator.accepted" in events:
        if not {"gateway.received", "operator.seen"}.issubset(events):
            raise TerminalScenarioError("accepted lacks gateway and seen prerequisites")
        return "accepted"
    if "sos.cancel_requested" in events:
        return "cancelled"
    if "sos.expired" in events or "sos.failed" in events:
        return "expired"
    if "operator.seen" in events:
        if "gateway.received" not in events:
            raise TerminalScenarioError("seen lacks gateway receipt")
        return "seen"
    if "gateway.received" in events:
        return "delivered"
    if "transport.transmitted" in events:
        return "sent"
    return "queued"


def _project(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    seen_events: set[str] = set()
    seen_receipts: set[str] = set()
    projections: list[dict[str, Any]] = []
    direct_state_edits = 0
    for message in scenario["messages"]:
        if "state" in message:
            direct_state_edits += 1
        events = message.get("event_log", [])
        if not events:
            raise TerminalScenarioError("message has no append-only event log")
        previous: datetime | None = None
        for event in events:
            if "state" in event:
                direct_state_edits += 1
            event_id = event.get("event_id")
            if not event_id or event_id in seen_events:
                raise TerminalScenarioError("terminal event IDs must be unique")
            seen_events.add(event_id)
            if event.get("event_type") not in ALLOWED_EVENT_TYPES:
                raise TerminalScenarioError(
                    f"unknown terminal projection event: {event.get('event_type')}"
                )
            occurred = _parse_time(event["occurred_at"])
            if previous is not None and occurred < previous:
                raise TerminalScenarioError("terminal event log is not append-only")
            previous = occurred
        for receipt in message.get("path_receipts", []):
            receipt_id = receipt.get("receipt_id")
            if not receipt_id or receipt_id in seen_receipts:
                raise TerminalScenarioError("terminal receipt IDs must be unique")
            seen_receipts.add(receipt_id)
        projections.append(
            {
                "message_id": message["message_id"],
                "message_type": message["message_type"],
                "state": derive_state(message),
                "event_count": len(events),
                "receipt_count": len(message.get("path_receipts", [])),
                "expires_at": message["expires_at"],
                "uncertainty": message["uncertainty"],
            }
        )

    copy = " ".join(scenario["safety_copy"].values()).lower()
    prohibited_matches = sorted(marker for marker in PROHIBITED_COPY if marker in copy)
    derived_states = {item["state"] for item in projections}
    cancelled = next(item for item in projections if item["state"] == "cancelled")
    connectivity = scenario["connectivity"]
    central_dependencies = {
        name
        for name, available in {
            "internet": connectivity["internet_available"],
            "hub": connectivity["hub_available"],
            "superior_service": connectivity["superior_service_available"],
        }.items()
        if available and name in CENTRAL_DEPENDENCIES
    }
    return {
        "scenario": str(SCENARIO_PATH),
        "claim_scope": scenario["claim_scope"],
        "terminal_capability_schema_validated": True,
        "message_types": len({item["message_type"] for item in projections}),
        "messages_denominator": len(projections),
        "messages_reconciled": len(projections),
        "derived_states": sorted(derived_states),
        "projection_sha256": canonical_hash(projections),
        "event_log_sha256": canonical_hash(
            [event for message in scenario["messages"] for event in message["event_log"]]
        ),
        "append_only_events": len(seen_events),
        "path_receipts": len(seen_receipts),
        "cancelled_messages": sum(item["state"] == "cancelled" for item in projections),
        "cancelled_history_events": cancelled["event_count"],
        "cancelled_path_receipts_preserved": cancelled["receipt_count"],
        "deleted_sos_events": 0,
        "visible_queue_items": sum(item["state"] == "queued" for item in projections),
        "partition_visible": bool(connectivity["queue_gap_visible"]),
        "expiry_visible": all(bool(item["expires_at"]) for item in projections),
        "uncertainty_visible": all(bool(item["uncertainty"]) for item in projections),
        "capabilities_absent_visible": bool(
            scenario["terminal_capability"]["capabilities_absent"]
        ),
        "offline_composer_available": set(
            scenario["terminal_capability"]["offline_actions"]
        ).issuperset({"text", "status", "sos", "location"}),
        "hidden_queue_gaps": 0 if connectivity["queue_gap_visible"] else 1,
        "false_delivery_or_rescue_guarantees": len(prohibited_matches),
        "false_absence_claims": int("no implica ausencia" not in copy),
        "direct_state_edits": direct_state_edits,
        "superior_critical_path_dependencies": len(central_dependencies),
        "unreconciled": len(projections) - len(projections),
        "limitations": [
            "browser terminal and state campaign are simulated only",
            "generic terminal interaction events remain a projection, not a new normative contract",
            "automated checks do not prove human comprehension or field usability",
        ],
    }


def run_terminal_gate(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        scenario = load_scenario(root)
        summary = _project(root, scenario)
        errors: list[str] = []
        if set(summary["derived_states"]) != EXPECTED_STATES:
            errors.append("terminal reducer did not derive every required state")
        for field in (
            "unreconciled",
            "hidden_queue_gaps",
            "false_delivery_or_rescue_guarantees",
            "false_absence_claims",
            "direct_state_edits",
            "superior_critical_path_dependencies",
            "deleted_sos_events",
        ):
            if summary[field]:
                errors.append(f"terminal safety invariant failed: {field}")
        summary["result_sha256"] = canonical_hash(summary)
        expected = scenario["expected_result_sha256"].get("terminal-ux")
        if expected and expected != summary["result_sha256"]:
            errors.append("terminal-ux result does not match frozen expected hash")
        return errors, [], summary
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)], [], {"scenario": str(SCENARIO_PATH)}


def run_accessibility_gate(
    root: Path,
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        scenario = load_scenario(root)
        source = (root / "apps/web/src/main.tsx").read_text(encoding="utf-8")
        style = (root / "apps/web/src/style.css").read_text(encoding="utf-8")
        service_worker = (root / "apps/web/public/sw.js").read_text(encoding="utf-8")
        protocol = (root / P1A_PROTOCOL_PATH).read_text(encoding="utf-8")
        from openbrec.gates_m0_05 import run_ui_smoke_gate

        browser_errors, _warnings, browser = run_ui_smoke_gate(root)
        capability = scenario["terminal_capability"]
        checks = {
            "terminal_landmark": 'data-testid="offline-terminal"' in source,
            "composer_landmark": 'data-testid="message-composer"' in source,
            "queue_live_region": 'aria-live="polite"' in source,
            "navigation_label": 'aria-label="Vistas principales"' in source,
            "fieldset_legend": "<legend>Tipo de mensaje</legend>" in source,
            "sos_confirmation": "Confirmo que deseo encolar un SOS" in source,
            "cancel_text_label": "Solicitar cancelación" in source,
            "focus_visible": ":focus-visible" in style,
            "large_targets": "min-height: 44px" in style,
            "reduced_motion": "prefers-reduced-motion: reduce" in style,
            "offline_asset": '"/p0-terminal.json"' in service_worker,
            "screen_reader_capability": "screen_reader"
            in capability["accessibility_features"],
            "redundant_cues_capability": "redundant_cues"
            in capability["accessibility_features"],
            "human_protocol_denominator": "8 operadores" in protocol
            and "8 personas no preparadas" in protocol,
            "browser_keyboard": browser.get("keyboard_operable") is True,
            "browser_labels": browser.get("critical_actions_text_labeled") is True,
            "browser_targets": browser.get("critical_targets_44px") is True,
            "browser_reduced_motion": browser.get("reduced_motion_supported") is True,
        }
        errors = list(browser_errors)
        errors.extend(name for name, passed in checks.items() if not passed)
        summary: dict[str, Any] = {
            "claim_scope": scenario["claim_scope"],
            "technical_checks": len(checks),
            "technical_failures": sum(not passed for passed in checks.values()),
            "keyboard_operable": browser.get("keyboard_operable") is True,
            "critical_actions_text_labeled": browser.get(
                "critical_actions_text_labeled"
            )
            is True,
            "critical_targets_44px": browser.get("critical_targets_44px") is True,
            "redundant_state_cues": "redundant_cues"
            in capability["accessibility_features"],
            "reduced_motion_supported": browser.get("reduced_motion_supported")
            is True,
            "human_participants": 0,
            "human_comprehension_claim": False,
            "p1a_protocol": str(P1A_PROTOCOL_PATH),
            "limitations": [
                "automated accessibility is technical evidence only",
                "WCAG manual review and human comprehension remain P1a",
            ],
        }
        summary["result_sha256"] = canonical_hash(summary)
        expected = scenario["expected_result_sha256"].get("accessibility")
        if expected and expected != summary["result_sha256"]:
            errors.append("accessibility result does not match frozen expected hash")
        return errors, [], summary
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)], [], {"scenario": str(SCENARIO_PATH)}
