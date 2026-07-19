CREATE TABLE IF NOT EXISTS observations (
  observation_id TEXT PRIMARY KEY,
  sensor_id TEXT NOT NULL,
  sensor_type TEXT NOT NULL,
  observation_kind TEXT NOT NULL,
  zone_id TEXT,
  quality DOUBLE PRECISION NOT NULL,
  uncertainty DOUBLE PRECISION NOT NULL,
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  payload_json BYTEA NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS observations_zone_window
  ON observations (zone_id, window_start);

CREATE TABLE IF NOT EXISTS fusion_results (
  result_id TEXT PRIMARY KEY,
  state TEXT NOT NULL CHECK(state IN ('indicator','conflicted','abstained')),
  zone_id TEXT,
  window_start TEXT NOT NULL,
  window_end TEXT NOT NULL,
  result_json BYTEA NOT NULL,
  recorded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS fusion_results_zone_window
  ON fusion_results (zone_id, window_start);
