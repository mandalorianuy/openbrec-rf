# M0-04 replay and storage security review

- Date: 2026-07-17
- Scope: M0 laboratory replay and portable disposition boundary only
- Status: approved for evidence generation; field support remains `unverified`
- Review authority: `docs/security/OpenBREC-RF-threat-model.md`

## Decision

M0-04 may use the portable SQLite implementation as the normative executable
reference for disposition semantics. It is not a field database profile and it
does not prove PostgreSQL/runtime integration. The boundary is replaceable:
canonical events, destination rules, receipts and reconciliation are independent
of the database engine.

Potentially life-saving material takes precedence over routine minimization. It
is encrypted and preserved in `EvidenceVault`, including when it cannot yet be
validated as a core event. This precedence does not waive access control: every
seal, read, denied action and reviewed deletion is auditable; break-glass needs
an actor and reason; deletion needs expired retention and a distinct reviewer.

## Implemented trust boundaries

1. Adapter fixture bytes are hashed before parsing. A mismatch produces a failed
   receipt and zero normalized events.
2. Core replay revalidates JSON Schema and semantic relations before deriving
   outputs. Idempotency collisions, impossible time relations, unknown schemas
   or regressive sequences produce a failed receipt and zero partial evidence.
3. Each ingested unit is committed transactionally to exactly one primary
   destination: `AcceptedEventLog`, `ReviewQuarantine`, `EvidenceVault` or
   `RejectionLedger`.
4. Valid accepted events are stored in RFC 8785 canonical form with SHA-256.
   Invalid material is never silently corrected into an accepted event.
5. Quarantine and vault bytes are protected with AES-256-GCM. A 32-byte master
   key is injected by the caller; HKDF-SHA-256 derives an incident-specific key;
   a fresh 96-bit nonce is generated per record; canonical metadata is bound as
   additional authenticated data.
6. A clearly unrelated secret is represented only by hash, size,
   classification, reason and destruction disposition in `RejectionLedger`.
   The clear bytes are not persisted.
7. Replay material uses only fixture logical time, canonical inputs, pinned
   artifacts and configuration. Host time, network access and random values do
   not enter the result hash.

## Verification and negative evidence

The M0-04 gates cover:

- adapter corruption and receipt schema validation;
- upstream adapter-receipt binding before core replay;
- ten deterministic runs with reversed order, two time zones and two locale
  settings;
- identical duplicate deduplication, idempotency collision, regressive
  sequence, late input, unknown schema and absent source capability;
- four-input/four-destination reconciliation with zero unreconciled units;
- unauthorized break-glass, active-retention deletion denial, audited access
  and reviewed deletion receipt;
- cleartext scans for rejected secrets and preserved life-safety bytes;
- duplicate JSON keys, modified fixture data and modified AES-GCM ciphertext.

These are synthetic laboratory results. They do not prove resistance to host
compromise, physical capture, rollback of a copied database or denial of
service.

## Governed residuals

| Residual | State after M0-04 | Required resolution |
|---|---|---|
| Master-key custody, rotation, recovery and zeroization | planned for M0-06; field `unverified` | Select custody profile, add rotation/recovery vectors and fail closed when key material is absent or stale. |
| SQLite file rollback, concurrent writers and physical capture | controlled for single-process lab replay; field `unverified` | PostgreSQL/runtime integration plus rollback/concurrency tests before M0 exit. |
| PostgreSQL migrations and worker disposition integration | planned for M0-06 and blocks M0 exit | Implement the same four-destination transaction and run reconciliation through Compose. |
| Random-nonce durability across crash/restart | controlled by 96-bit OS randomness and `(incident_id, nonce)` uniqueness in the lab schema | Add fault-injection and operational key lifecycle evidence before any field profile. |
| Dependency supply chain for `cryptography` and `rfc8785` | planned under M0-R007 | SBOM, licenses, vulnerability receipt and exact-lock review in M0-06. |
| Database availability/backup | not claimed | Define backup, restore, retention and evidence-custody SOP before a field deployment. |

No residual above authorizes a field security claim. Missing M0-06 evidence
blocks the M0 exit and therefore blocks every addon P0.

## Stop conditions

- any accepted event without normative and semantic validation;
- any collision or corrupt input that leaves partial derived evidence;
- any input without one reconciled primary destination;
- any vault read without actor, purpose, active retention and audit;
- any deletion without expiry, reason, actor, distinct reviewer and receipt;
- any sensitive rejected or preserved bytes visible in clear in the store;
- any replay hash influenced by host time, network or randomness;
- any claim that this laboratory SQLite profile is a supported field vault.
