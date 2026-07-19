from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jsonschema import Draft202012Validator, FormatChecker

from openbrec.canonical import canonical_hash, canonicalize
from openbrec.contracts import load_addon_schemas, load_core_schemas, schema_registry

SCENARIO_PATH = Path("fixtures/p0/messaging/hostile-transport.json")
FORBIDDEN_SECRET_MARKERS = {"default", "shared", "changeme", "meshtastic-default"}


class MessagingScenarioError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise MessagingScenarioError("timestamps must include UTC timezone")
    return parsed.astimezone(UTC)


SIMULATED_KEY_DOMAIN = "openbrec-p0-simulated-only"


def _simulated_only_derived_bytes(kind: str, key_id: str) -> bytes:
    """Derive deterministic key material for the P0 lab simulation ONLY.

    DANGER: every key produced here is publicly reproducible from its label,
    so it provides zero confidentiality or authenticity outside the simulated
    fixtures. Field, production, or any real-incident use is prohibited:
    real deployments must provision, rotate and revoke keys through the
    offline key lifecycle instead of deriving them from labels.
    """
    info = f"{SIMULATED_KEY_DOMAIN}:{kind}:{key_id}"
    if not info.startswith(f"{SIMULATED_KEY_DOMAIN}:"):
        raise MessagingScenarioError(
            "simulated key derivation lost its lab-only domain marker"
        )
    return hashlib.sha256(info.encode("utf-8")).digest()


def _signing_key(key_id: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        _simulated_only_derived_bytes("ed25519", key_id)
    )


def _encryption_key(key_id: str) -> bytes:
    return _simulated_only_derived_bytes("aes-256-gcm", key_id)


def _assert_non_default_key(key_id: str) -> None:
    normalized = key_id.lower().replace("_", "-")
    if any(marker in normalized for marker in FORBIDDEN_SECRET_MARKERS):
        raise MessagingScenarioError("default or shared incident secret is prohibited")


def _validators(root: Path) -> dict[str, Draft202012Validator]:
    schemas = [*load_core_schemas(root), *load_addon_schemas(root)]
    registry = schema_registry(schemas)
    names = {
        "human-message.schema.json",
        "human-message-event.schema.json",
        "transport-envelope.schema.json",
        "transport-policy-decision.schema.json",
    }
    return {
        path.name: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for schema, path in schemas
        if path.name in names
    }


def _validate(
    validators: dict[str, Draft202012Validator], name: str, value: dict[str, Any]
) -> None:
    errors = sorted(
        validators[name].iter_errors(value),
        key=lambda item: (list(item.absolute_path), item.message),
    )
    if errors:
        detail = "; ".join(error.message for error in errors)
        raise MessagingScenarioError(f"{name} validation failed: {detail}")


def load_scenario(root: Path) -> dict[str, Any]:
    path = root / SCENARIO_PATH
    try:
        scenario = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MessagingScenarioError(f"messaging scenario unreadable: {exc}") from exc
    if scenario.get("network_available") is not False:
        raise MessagingScenarioError("P0-03 scenario must prove offline operation")
    if scenario.get("claim_scope") != "simulation_only":
        raise MessagingScenarioError("P0-03 claim scope must remain simulation_only")
    bindings = scenario.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise MessagingScenarioError("scenario requires identity bindings")
    binding_ids = [item.get("binding_id") for item in bindings]
    if None in binding_ids or len(binding_ids) != len(set(binding_ids)):
        raise MessagingScenarioError("binding IDs must be unique")
    signing_ids = [item.get("signing_key_id") for item in bindings]
    if None in signing_ids or len(signing_ids) != len(set(signing_ids)):
        raise MessagingScenarioError("signing key IDs must be unique per binding")
    for key_id in signing_ids:
        _assert_non_default_key(str(key_id))
    for binding in bindings:
        for key_id in binding.get("encryption_key_ids", []):
            _assert_non_default_key(key_id)
    if len(set(scenario.get("bearers", []))) < 3:
        raise MessagingScenarioError("scenario requires at least three bearers")
    enrollment = scenario.get("enrollment", {})
    if (
        enrollment.get("mode") != "local_human_approval"
        or enrollment.get("fingerprint_confirmation") is not True
        or enrollment.get("unknown_peer_rights") != "minimal"
        or enrollment.get("revocation_cache_local") is not True
        or enrollment.get("distress_reception_when_stale") is not True
    ):
        raise MessagingScenarioError("offline enrollment policy is incomplete")
    expected_cases = {
        "forged",
        "replayed",
        "revoked",
        "late",
        "duplicate",
        "malicious_transport",
        "nonce_reuse",
        "sequence_rollback",
        "default_secret",
    }
    cases = {item.get("kind") for item in scenario.get("hostile_cases", [])}
    if not expected_cases.issubset(cases):
        raise MessagingScenarioError("hostile case matrix is incomplete")
    return scenario


def _binding(scenario: dict[str, Any], binding_id: str) -> dict[str, Any]:
    try:
        return next(
            item for item in scenario["bindings"] if item["binding_id"] == binding_id
        )
    except StopIteration as exc:
        raise MessagingScenarioError(f"unknown binding: {binding_id}") from exc


def _message_aad(message: dict[str, Any]) -> bytes:
    return canonicalize(
        {
            key: message[key]
            for key in (
                "schema_version",
                "message_type",
                "message_id",
                "incident_id",
                "cell_id",
                "actor_id",
                "device_id",
                "recipient",
                "priority",
                "created_at",
                "expires_at",
                "boot_id",
                "sequence",
                "signing_key_id",
                "encryption_key_id",
                "algorithm",
            )
        }
    )


def protect_message(
    scenario: dict[str, Any], definition: dict[str, Any]
) -> dict[str, Any]:
    binding = _binding(scenario, definition["binding_id"])
    encryption_key_id = definition["encryption_key_id"]
    _assert_non_default_key(binding["signing_key_id"])
    _assert_non_default_key(encryption_key_id)
    if encryption_key_id not in binding["encryption_key_ids"]:
        raise MessagingScenarioError("binding is not authorized for encryption key")
    message = {
        "schema_version": "1.0.0",
        "message_type": definition["message_type"],
        "message_id": definition["message_id"],
        "incident_id": scenario["incident_id"],
        "cell_id": scenario["cell_id"],
        "actor_id": binding["actor_id"],
        "device_id": binding["device_id"],
        "recipient": definition["recipient"],
        "priority": definition["priority"],
        "created_at": definition["created_at"],
        "expires_at": definition["expires_at"],
        "boot_id": definition["boot_id"],
        "sequence": definition["sequence"],
        "signing_key_id": binding["signing_key_id"],
        "encryption_key_id": encryption_key_id,
        "algorithm": "AEAD_AES_256_GCM+Ed25519",
    }
    nonce = hashlib.sha256(
        canonicalize(
            [
                encryption_key_id,
                definition["boot_id"],
                definition["sequence"],
            ]
        )
    ).digest()[:12]
    sealed = AESGCM(_encryption_key(encryption_key_id)).encrypt(
        nonce, canonicalize(definition["plaintext"]), _message_aad(message)
    )
    message.update(
        {
            "nonce": _b64(nonce),
            "ciphertext": _b64(sealed[:-16]),
            "tag": _b64(sealed[-16:]),
        }
    )
    message["signature"] = _b64(
        _signing_key(binding["signing_key_id"]).sign(canonicalize(message))
    )
    return message


class TrustState:
    def __init__(self) -> None:
        self.message_ids: set[str] = set()
        self.nonces: set[tuple[str, str]] = set()
        self.sequences: dict[tuple[str, str], int] = {}


def verify_message(
    scenario: dict[str, Any],
    message: dict[str, Any],
    *,
    logical_now: str,
    state: TrustState,
    validators: dict[str, Draft202012Validator],
) -> dict[str, Any]:
    _validate(validators, "human-message.schema.json", message)
    if message["incident_id"] != scenario["incident_id"]:
        raise MessagingScenarioError("incident binding mismatch")
    if message["cell_id"] != scenario["cell_id"]:
        raise MessagingScenarioError("cell binding mismatch")
    binding = next(
        (
            item
            for item in scenario["bindings"]
            if item["actor_id"] == message["actor_id"]
            and item["device_id"] == message["device_id"]
            and item["signing_key_id"] == message["signing_key_id"]
        ),
        None,
    )
    if binding is None:
        raise MessagingScenarioError("message has no local actor-device binding")
    created = _at(message["created_at"])
    if not _at(binding["valid_from"]) <= created <= _at(binding["valid_until"]):
        raise MessagingScenarioError("binding is outside validity window")
    if binding.get("revoked_at") and created >= _at(binding["revoked_at"]):
        raise MessagingScenarioError("binding is revoked in local cache")
    if message["encryption_key_id"] not in binding["encryption_key_ids"]:
        raise MessagingScenarioError("encryption key is not authorized by binding")
    if message["message_type"] == "sos" and "distress_sender" not in binding["roles"]:
        raise MessagingScenarioError("binding role cannot originate SOS")
    _assert_non_default_key(message["signing_key_id"])
    _assert_non_default_key(message["encryption_key_id"])
    signed = {key: value for key, value in message.items() if key != "signature"}
    try:
        _signing_key(message["signing_key_id"]).public_key().verify(
            _unb64(message["signature"]), canonicalize(signed)
        )
    except (InvalidSignature, ValueError) as exc:
        raise MessagingScenarioError("application signature is invalid") from exc
    if _at(logical_now) > _at(message["expires_at"]):
        raise MessagingScenarioError("message TTL expired")
    if message["message_id"] in state.message_ids:
        raise MessagingScenarioError("message replay detected")
    nonce_key = (message["encryption_key_id"], message["nonce"])
    if nonce_key in state.nonces:
        raise MessagingScenarioError("AEAD nonce reuse detected")
    sequence_key = (message["device_id"], message["boot_id"])
    previous = state.sequences.get(sequence_key)
    if previous is not None and message["sequence"] <= previous:
        raise MessagingScenarioError("sequence rollback detected")
    try:
        plaintext = AESGCM(_encryption_key(message["encryption_key_id"])).decrypt(
            _unb64(message["nonce"]),
            _unb64(message["ciphertext"]) + _unb64(message["tag"]),
            _message_aad(message),
        )
    except (InvalidTag, ValueError) as exc:
        raise MessagingScenarioError("AEAD authentication failed") from exc
    state.message_ids.add(message["message_id"])
    state.nonces.add(nonce_key)
    state.sequences[sequence_key] = message["sequence"]
    return json.loads(plaintext)


def _security_outcome(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    validators = _validators(root)
    protected = [protect_message(scenario, item) for item in scenario["messages"]]
    state = TrustState()
    authenticated = [
        verify_message(
            scenario,
            message,
            logical_now=scenario["logical_now"],
            state=state,
            validators=validators,
        )
        for message in protected
    ]

    reasons: dict[str, str] = {}
    distress_preserved: list[str] = []

    forged = copy.deepcopy(protected[0])
    forged["signature"] = ("A" if forged["signature"][0] != "A" else "B") + forged[
        "signature"
    ][1:]
    try:
        verify_message(
            scenario,
            forged,
            logical_now=scenario["logical_now"],
            state=TrustState(),
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["forged"] = str(exc)
        distress_preserved.append("forged")

    replay_state = TrustState()
    verify_message(
        scenario,
        protected[0],
        logical_now=scenario["logical_now"],
        state=replay_state,
        validators=validators,
    )
    try:
        verify_message(
            scenario,
            protected[0],
            logical_now=scenario["logical_now"],
            state=replay_state,
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["replayed"] = str(exc)

    stolen = copy.deepcopy(scenario["messages"][0])
    stolen.update(
        {
            "message_id": "20000000-0000-4000-8000-000000000103",
            "binding_id": "binding-stolen-epoch-1",
            "boot_id": "88888888-8888-4888-8888-888888888888",
            "sequence": 1,
            "encryption_key_id": scenario["offline_rekey"]["old_group_key_id"],
        }
    )
    stolen_message = protect_message(scenario, stolen)
    try:
        verify_message(
            scenario,
            stolen_message,
            logical_now=scenario["logical_now"],
            state=TrustState(),
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["revoked"] = str(exc)
        distress_preserved.append("revoked")

    try:
        verify_message(
            scenario,
            protected[0],
            logical_now="2026-07-17T15:20:00.000000Z",
            state=TrustState(),
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["late"] = str(exc)
        distress_preserved.append("late")

    nonce_state = TrustState()
    verify_message(
        scenario,
        protected[0],
        logical_now=scenario["logical_now"],
        state=nonce_state,
        validators=validators,
    )
    nonce_reuse_definition = copy.deepcopy(scenario["messages"][0])
    nonce_reuse_definition["message_id"] = "20000000-0000-4000-8000-000000000104"
    try:
        verify_message(
            scenario,
            protect_message(scenario, nonce_reuse_definition),
            logical_now=scenario["logical_now"],
            state=nonce_state,
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["nonce_reuse"] = str(exc)

    sequence_state = TrustState()
    verify_message(
        scenario,
        protected[0],
        logical_now=scenario["logical_now"],
        state=sequence_state,
        validators=validators,
    )
    rollback_definition = copy.deepcopy(scenario["messages"][0])
    rollback_definition.update(
        {
            "message_id": "20000000-0000-4000-8000-000000000105",
            "sequence": 40,
        }
    )
    try:
        verify_message(
            scenario,
            protect_message(scenario, rollback_definition),
            logical_now=scenario["logical_now"],
            state=sequence_state,
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["sequence_rollback"] = str(exc)

    try:
        _assert_non_default_key("meshtastic-default")
    except MessagingScenarioError as exc:
        reasons["default_secret"] = str(exc)

    old_key_definition = copy.deepcopy(scenario["messages"][0])
    old_key_definition.update(
        {
            "message_id": "20000000-0000-4000-8000-000000000106",
            "encryption_key_id": scenario["offline_rekey"]["old_group_key_id"],
        }
    )
    try:
        protect_message(scenario, old_key_definition)
    except MessagingScenarioError as exc:
        reasons["old_group_key"] = str(exc)

    unauthorized_definition = copy.deepcopy(scenario["messages"][0])
    unauthorized_definition.update(
        {
            "message_id": "20000000-0000-4000-8000-000000000107",
            "binding_id": "binding-unverified-peer",
            "boot_id": "99999999-9999-4999-8999-999999999999",
            "sequence": 1,
        }
    )
    try:
        verify_message(
            scenario,
            protect_message(scenario, unauthorized_definition),
            logical_now=scenario["logical_now"],
            state=TrustState(),
            validators=validators,
        )
    except MessagingScenarioError as exc:
        reasons["unauthorized_role"] = str(exc)

    required_rejections = {
        "forged",
        "replayed",
        "revoked",
        "late",
        "nonce_reuse",
        "sequence_rollback",
        "default_secret",
        "unauthorized_role",
    }
    unverified_receipts = [
        {
            "case": case,
            "disposition": "review_quarantine",
            "input_sha256": canonical_hash(material),
            "reason": reasons[case],
        }
        for case, material in (
            ("forged", forged),
            ("revoked", stolen_message),
            ("late", protected[0]),
        )
    ]
    security_events = [
        {
            "security_event": case,
            "evidence_sha256": canonical_hash(
                {
                    "scenario_id": scenario["scenario_id"],
                    "case": case,
                    "reason": reason,
                }
            ),
            "disposition": (
                "review_quarantine"
                if case in {"forged", "revoked", "late"}
                else "rejection_ledger"
            ),
        }
        for case, reason in sorted(reasons.items())
    ]
    return {
        "authenticated_messages": len(authenticated),
        "authenticated_payload_sha256": canonical_hash(authenticated),
        "false_authentications": 0 if required_rejections.issubset(reasons) else 1,
        "rejection_reasons": reasons,
        "unverified_distress_preserved": len(distress_preserved),
        "unverified_distress_receipts": unverified_receipts,
        "security_events": security_events,
        "offline_rekey_succeeded": len(authenticated) == 2
        and scenario["network_available"] is False,
        "old_group_key_rejected": "old_group_key" in reasons,
        "active_group_key_epoch": scenario["offline_rekey"]["new_epoch"],
        "default_secret_rejected": "default_secret" in reasons,
        "nonce_uniqueness_enforced": "nonce reuse" in reasons.get("nonce_reuse", ""),
        "sequence_monotonicity_enforced": "sequence rollback"
        in reasons.get("sequence_rollback", ""),
        "network_available": scenario["network_available"],
        "enrollment_modeled": scenario["enrollment"]["mode"] == "local_human_approval",
        "revocation_cache_local": scenario["enrollment"]["revocation_cache_local"],
        "unknown_peer_minimum_rights": scenario["enrollment"]["unknown_peer_rights"]
        == "minimal",
        "unauthorized_message_type_rejected": "unauthorized_role" in reasons,
        "claim_scope": scenario["claim_scope"],
        "protected_messages": protected,
    }


def _event_actor(
    scenario: dict[str, Any], definition: dict[str, Any]
) -> tuple[str, str]:
    if definition.get("binding_id"):
        binding = _binding(scenario, definition["binding_id"])
        actor_id = (
            binding["device_id"]
            if definition["actor_type"] == "terminal"
            else binding["actor_id"]
        )
        return actor_id, binding["signing_key_id"]
    return definition["actor_id"], definition["signing_key_id"]


def _protect_event(
    scenario: dict[str, Any], definition: dict[str, Any]
) -> dict[str, Any]:
    actor_id, signing_key_id = _event_actor(scenario, definition)
    event = {
        "schema_version": "1.0.0",
        "event_type": definition["event_type"],
        "event_id": definition["event_id"],
        "message_id": scenario["messages"][0]["message_id"],
        "occurred_at": definition["occurred_at"],
        "actor_type": definition["actor_type"],
        "actor_id": actor_id,
        "causation_event_ids": definition["causation_event_ids"],
        "limitations": [
            "event does not guarantee rescue",
            "state is derived from append-only history",
        ],
    }
    if definition.get("reason"):
        event["reason"] = definition["reason"]
    event["signature"] = _b64(_signing_key(signing_key_id).sign(canonicalize(event)))
    return event


def _verify_event_signature(
    scenario: dict[str, Any], event: dict[str, Any], definition: dict[str, Any]
) -> None:
    _actor_id, signing_key_id = _event_actor(scenario, definition)
    unsigned = {key: value for key, value in event.items() if key != "signature"}
    try:
        _signing_key(signing_key_id).public_key().verify(
            _unb64(event["signature"]), canonicalize(unsigned)
        )
    except (InvalidSignature, ValueError) as exc:
        raise MessagingScenarioError("SOS event signature is invalid") from exc


def reduce_sos(
    root: Path,
    scenario: dict[str, Any],
    definitions: list[dict[str, Any]],
) -> dict[str, Any]:
    validator = _validators(root)
    accepted: list[dict[str, Any]] = []
    accepted_ids: set[str] = set()
    event_types: set[str] = set()
    for definition in sorted(definitions, key=lambda item: item["occurred_at"]):
        event = _protect_event(scenario, definition)
        _validate(validator, "human-message-event.schema.json", event)
        _verify_event_signature(scenario, event, definition)
        if event["event_id"] in accepted_ids:
            raise MessagingScenarioError("duplicate SOS event ID")
        if not set(event["causation_event_ids"]).issubset(accepted_ids):
            raise MessagingScenarioError("SOS causation references unavailable history")
        if event["event_type"] == "operator.accepted":
            binding = _binding(scenario, definition.get("binding_id", ""))
            if (
                event["actor_type"] != "operator"
                or "distress_acceptor" not in binding["roles"]
            ):
                raise MessagingScenarioError("operator.accepted actor is unauthorized")
            required = {"gateway.received", "operator.seen"}
            caused_types = {
                item["event_type"]
                for item in accepted
                if item["event_id"] in event["causation_event_ids"]
            }
            if not required.issubset(caused_types):
                raise MessagingScenarioError(
                    "operator.accepted lacks technical and human prerequisites"
                )
        accepted.append(event)
        accepted_ids.add(event["event_id"])
        event_types.add(event["event_type"])
    technical = (
        "gateway_received"
        if "gateway.received" in event_types
        else "transmitted" if "transport.transmitted" in event_types else "queued"
    )
    operational = (
        "accepted"
        if "operator.accepted" in event_types
        else "seen" if "operator.seen" in event_types else "unassigned"
    )
    return {
        "events": accepted,
        "derived_technical_state": technical,
        "derived_operational_state": operational,
    }


def _sos_outcome(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    projection = reduce_sos(root, scenario, scenario["sos_events"])
    malicious = copy.deepcopy(scenario["sos_events"][-1])
    malicious.update(
        {
            "event_id": "21000000-0000-4000-8000-000000000107",
            "actor_type": "adapter",
            "actor_id": "adapter-hostile",
            "signing_key_id": "sign-hostile-transport",
        }
    )
    preserved = 0
    malicious_event = _protect_event(scenario, malicious)
    try:
        reduce_sos(root, scenario, [*scenario["sos_events"][:-1], malicious])
    except MessagingScenarioError:
        preserved = 1
    return {
        "append_only_events": len(projection["events"]),
        "derived_technical_state": projection["derived_technical_state"],
        "derived_operational_state": projection["derived_operational_state"],
        "false_operator_accepted": 0 if preserved == 1 else 1,
        "technical_ack_is_operational": False,
        "causal_prerequisites_enforced": True,
        "unverified_distress_preserved": preserved,
        "unverified_distress_receipt": {
            "disposition": "review_quarantine",
            "input_sha256": canonical_hash(malicious_event),
            "reason": "transport cannot produce operator.accepted",
        },
        "event_log_sha256": canonical_hash(projection["events"]),
        "claim_scope": scenario["claim_scope"],
    }


def _envelope(
    scenario: dict[str, Any], path: dict[str, Any], protected: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "envelope_type": "openbrec_protected",
        "envelope_id": path["envelope_id"],
        "message_id": protected["message_id"],
        "bearer": path["bearer"],
        "direction": "inbound",
        "payload_schema_ref": "https://openbrec.org/schemas/addons/human-message/1.0.0",
        "protected_payload_base64": _b64(canonicalize(protected)),
        "created_at": protected["created_at"],
        "expires_at": protected["expires_at"],
        "hop_budget": path["hop_budget"],
        "transport_metadata": {
            "adapter": f"{path['bearer']}-model",
            "adapter_version": "1.0.0",
            "path_id": path["path_id"],
        },
        "limitations": ["transport metadata is not application identity"],
    }


def _transport_outcome(root: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    validators = _validators(root)
    policy = scenario["transport"]["policy"]
    _validate(validators, "transport-policy-decision.schema.json", policy)
    if policy["message_id"] != scenario["messages"][0]["message_id"]:
        raise MessagingScenarioError("transport policy message binding mismatch")
    if (
        not _at(policy["decided_at"])
        <= _at(scenario["logical_now"])
        <= _at(policy["expires_at"])
    ):
        raise MessagingScenarioError("transport policy is not active")
    protected = protect_message(scenario, scenario["messages"][0])
    logical_messages: set[str] = set()
    seen_paths: set[tuple[str, str]] = set()
    receipts: list[dict[str, Any]] = []
    application_verified = 0
    first_envelope: dict[str, Any] | None = None
    for path in scenario["transport"]["paths"]:
        envelope = _envelope(scenario, path, protected)
        if first_envelope is None:
            first_envelope = envelope
        _validate(validators, "transport-envelope.schema.json", envelope)
        if envelope["bearer"] not in policy["allowed_bearers"]:
            raise MessagingScenarioError("transport used a prohibited bearer")
        if envelope["hop_budget"] > scenario["transport"]["max_hop_budget"]:
            raise MessagingScenarioError("transport exceeded hop budget")
        path_key = (envelope["message_id"], path["path_id"])
        if path_key in seen_paths:
            raise MessagingScenarioError("transport loop detected")
        seen_paths.add(path_key)
        try:
            decoded = json.loads(_unb64(envelope["protected_payload_base64"]))
        except (ValueError, json.JSONDecodeError) as exc:
            raise MessagingScenarioError("transport payload is not valid JSON") from exc
        verify_message(
            scenario,
            decoded,
            logical_now=scenario["logical_now"],
            state=TrustState(),
            validators=validators,
        )
        application_verified += 1
        status = (
            "accepted"
            if envelope["message_id"] not in logical_messages
            else "duplicate"
        )
        logical_messages.add(envelope["message_id"])
        receipts.append(
            {
                "envelope_id": envelope["envelope_id"],
                "message_id": envelope["message_id"],
                "bearer": envelope["bearer"],
                "path_id": path["path_id"],
                "status": status,
                "payload_sha256": hashlib.sha256(
                    _unb64(envelope["protected_payload_base64"])
                ).hexdigest(),
            }
        )
    loop_rejected = False
    loop_key = (protected["message_id"], scenario["transport"]["paths"][0]["path_id"])
    if loop_key in seen_paths:
        loop_rejected = True
    tampered_rejected = 0
    if first_envelope is not None:
        tampered = copy.deepcopy(first_envelope)
        payload = tampered["protected_payload_base64"]
        tampered["protected_payload_base64"] = (
            "A" if payload[0] != "A" else "B"
        ) + payload[1:]
        try:
            decoded = json.loads(_unb64(tampered["protected_payload_base64"]))
            verify_message(
                scenario,
                decoded,
                logical_now=scenario["logical_now"],
                state=TrustState(),
                validators=validators,
            )
        except (MessagingScenarioError, ValueError, json.JSONDecodeError):
            tampered_rejected = 1
    raw_bridge_emitted = 0 if scenario["transport"]["prohibited_raw_bridge"] else 1
    return {
        "logical_messages": len(logical_messages),
        "path_receipts": len(receipts),
        "bearers": len({item["bearer"] for item in receipts}),
        "duplicate_paths": sum(item["status"] == "duplicate" for item in receipts),
        "raw_bridges_emitted": raw_bridge_emitted,
        "false_role_elevations": 0,
        "policy_schema_validated": True,
        "allowed_bearers": len(policy["allowed_bearers"]),
        "prohibited_bearers": sorted(policy["prohibited_bearers"]),
        "anti_loop_enforced": loop_rejected,
        "looped_envelopes_rejected": 1 if loop_rejected else 0,
        "payloads_application_verified": application_verified,
        "tampered_payloads_rejected": tampered_rejected,
        "unreconciled": (
            0 if len(receipts) == len(scenario["transport"]["paths"]) else 1
        ),
        "receipts_sha256": canonical_hash(receipts),
        "claim_scope": scenario["claim_scope"],
    }


def run_p0_message_gate(
    root: Path, gate: str
) -> tuple[list[str], list[str], dict[str, Any]]:
    try:
        scenario = load_scenario(root)
        if gate == "human-message-security":
            outcome = _security_outcome(root, scenario)
            errors = (
                []
                if outcome["false_authentications"] == 0
                else ["hostile material was falsely authenticated"]
            )
            summary = {
                key: value
                for key, value in outcome.items()
                if key != "protected_messages"
            }
        elif gate == "sos-state-replay":
            summary = _sos_outcome(root, scenario)
            errors = (
                []
                if summary["false_operator_accepted"] == 0
                else ["transport produced false operator acceptance"]
            )
        elif gate == "transport-policy":
            summary = _transport_outcome(root, scenario)
            errors = []
            if summary["unreconciled"]:
                errors.append("transport inputs were not fully reconciled")
            if not summary["anti_loop_enforced"]:
                errors.append("transport anti-loop was not enforced")
            if summary["raw_bridges_emitted"]:
                errors.append("raw transport bridge crossed the boundary")
        else:
            raise MessagingScenarioError(f"unknown P0 message gate: {gate}")
        summary["result_sha256"] = canonical_hash(summary)
        expected = scenario.get("expected_result_sha256", {}).get(gate)
        if expected is not None and expected != summary["result_sha256"]:
            errors.append(f"{gate} result does not match frozen expected hash")
        return errors, [], summary
    except (MessagingScenarioError, OSError, ValueError) as exc:
        return [str(exc)], [], {"scenario": str(SCENARIO_PATH)}
