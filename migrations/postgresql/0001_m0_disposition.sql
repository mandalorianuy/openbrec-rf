CREATE TABLE IF NOT EXISTS ingress_units (
  unit_id TEXT PRIMARY KEY,
  input_sha256 TEXT NOT NULL,
  source_offset BIGINT NOT NULL,
  size_bytes BIGINT NOT NULL,
  destination TEXT NOT NULL CHECK(destination IN (
    'accepted_event_log','review_quarantine','evidence_vault','rejection_ledger'
  )),
  recorded_at TEXT NOT NULL,
  UNIQUE(input_sha256, source_offset)
);

CREATE TABLE IF NOT EXISTS accepted_event_log (
  logical_offset BIGSERIAL PRIMARY KEY,
  unit_id TEXT NOT NULL UNIQUE REFERENCES ingress_units(unit_id),
  event_sha256 TEXT NOT NULL,
  event_jcs BYTEA NOT NULL,
  policy_ref TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_quarantine (
  unit_id TEXT PRIMARY KEY REFERENCES ingress_units(unit_id),
  incident_id TEXT NOT NULL,
  key_id TEXT NOT NULL,
  nonce BYTEA NOT NULL,
  ciphertext BYTEA NOT NULL,
  aad BYTEA NOT NULL,
  errors_json TEXT NOT NULL,
  retention_until TEXT NOT NULL,
  UNIQUE(incident_id, key_id, nonce)
);

CREATE TABLE IF NOT EXISTS evidence_vault (
  unit_id TEXT PRIMARY KEY REFERENCES ingress_units(unit_id),
  input_sha256 TEXT NOT NULL UNIQUE,
  incident_id TEXT NOT NULL,
  key_id TEXT NOT NULL,
  nonce BYTEA NOT NULL,
  ciphertext BYTEA,
  aad BYTEA NOT NULL,
  retention_until TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  trigger_ref TEXT,
  reason TEXT NOT NULL,
  deletion_receipt_sha256 TEXT,
  UNIQUE(incident_id, key_id, nonce)
);

CREATE TABLE IF NOT EXISTS rejection_ledger (
  unit_id TEXT PRIMARY KEY REFERENCES ingress_units(unit_id),
  input_sha256 TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  classification TEXT NOT NULL,
  reason TEXT NOT NULL,
  destruction TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  audit_id TEXT PRIMARY KEY,
  input_sha256 TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  result TEXT NOT NULL,
  reason TEXT NOT NULL,
  receipt_sha256 TEXT
);
