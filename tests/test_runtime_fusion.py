from __future__ import annotations

import asyncio
import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_OBSERVATION = (
    REPO_ROOT / "fixtures/contracts/core/1.0.0/observation/valid/minimal.json"
)
POSTGRES_IMAGE = (
    "postgres:17-alpine"
    "@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"
)
DOCKER_MISSING_REASON = "docker is required for the real PostgreSQL integration test"
DOCKER_AVAILABLE = shutil.which("docker") is not None


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_observation(**overrides: Any) -> dict[str, Any]:
    observation = json.loads(VALID_OBSERVATION.read_text(encoding="utf-8"))
    for key, value in overrides.items():
        if value is None:
            observation.pop(key, None)
        else:
            observation[key] = value
    return observation


class FusionRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fusion = load_module(
            "openbrec_fusion_test", REPO_ROOT / "openbrec/fusion.py"
        )

    def test_classify_fusion_case_matches_campaign_rules(self) -> None:
        observations = {
            "obs-1": {"sensor_id": "beacon-1"},
            "obs-2": {"sensor_id": "beacon-2"},
        }
        base = {
            "known_artifact": False,
            "coverage_status": "sufficient",
            "baseline_valid": True,
            "placement_valid": True,
            "ood": False,
            "source_observation_ids": ["obs-1", "obs-2"],
            "independence_groups": ["group-a", "group-b"],
        }
        fusion = self.fusion

        self.assertEqual(
            fusion.classify_fusion_case(base, observations),
            "corroborated_candidate",
        )
        self.assertEqual(
            fusion.classify_fusion_case(
                {**base, "independence_groups": ["group-a", "group-a"]},
                observations,
            ),
            "single_modality_candidate",
        )
        self.assertEqual(
            fusion.classify_fusion_case(
                {**base, "source_observation_ids": ["obs-1"]},
                observations,
            ),
            "single_modality_candidate",
        )
        self.assertEqual(
            fusion.classify_fusion_case(
                {**base, "known_artifact": True}, observations
            ),
            "sensor_artifact_likely",
        )
        self.assertEqual(
            fusion.classify_fusion_case(
                {**base, "coverage_status": "degraded"}, observations
            ),
            "insufficient_coverage",
        )
        for patch in (
            {"baseline_valid": False},
            {"placement_valid": False},
            {"ood": True},
        ):
            self.assertEqual(
                fusion.classify_fusion_case({**base, **patch}, observations),
                "unknown",
            )

    def test_fuse_observations_abstains_when_evidence_is_unusable(self) -> None:
        low_quality = make_observation(quality=0.3)
        no_event = make_observation(
            observation_id="55555555-5555-4555-8555-555555555556",
            observation_kind="no_event_detected",
            measurements=[],
        )
        result = self.fusion.fuse_observations([low_quality, no_event])

        self.assertEqual(result["state"], "abstained")
        self.assertTrue(result["abstained"])
        self.assertEqual(
            result["abstention_reasons"], ["insufficient independent evidence"]
        )
        self.assertEqual(result["supporting_evidence_ids"], [])
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("silence does not imply absence", result["limitations"])

    def test_fuse_observations_marks_single_source_candidate(self) -> None:
        observation = make_observation(zone_id="zone-a")
        result = self.fusion.fuse_observations([observation], zone_id="zone-a")

        self.assertEqual(result["state"], "indicator")
        self.assertFalse(result["abstained"])
        self.assertEqual(result["abstention_reasons"], [])
        self.assertEqual(result["confidence"], 0.2)
        self.assertEqual(result["coverage"], "single-source")
        self.assertEqual(
            result["supporting_evidence_ids"], [observation["observation_id"]]
        )
        self.assertEqual(result["zone_id"], "zone-a")
        self.assertIn("never confirms presence or absence", result["limitations"])

    def test_fuse_observations_corroborates_independent_sources(self) -> None:
        first = make_observation(zone_id="zone-a")
        second = make_observation(
            observation_id="55555555-5555-4555-8555-555555555557",
            sensor_id="synthetic-2",
            sensor_type="operator",
            zone_id="zone-a",
        )
        result = self.fusion.fuse_observations([first, second], zone_id="zone-a")

        self.assertEqual(result["state"], "indicator")
        self.assertEqual(result["confidence"], 0.5)
        self.assertEqual(result["coverage"], "sufficient")
        self.assertEqual(
            result["supporting_evidence_ids"],
            sorted([first["observation_id"], second["observation_id"]]),
        )

    def test_fusion_output_is_order_independent_and_idempotent(self) -> None:
        canonical = load_module(
            "openbrec_canonical_fusion_test", REPO_ROOT / "openbrec/canonical.py"
        )
        first = make_observation(zone_id="zone-a")
        second = make_observation(
            observation_id="55555555-5555-4555-8555-555555555557",
            sensor_id="synthetic-2",
            zone_id="zone-a",
        )
        forward = self.fusion.fuse_observations([first, second], zone_id="zone-a")
        reversed_result = self.fusion.fuse_observations(
            [second, first], zone_id="zone-a"
        )

        self.assertEqual(forward["result_id"], reversed_result["result_id"])
        self.assertEqual(
            canonical.canonical_hash(forward),
            canonical.canonical_hash(reversed_result),
        )

    def test_fusion_result_rejects_inconsistent_state(self) -> None:
        result = self.fusion.fuse_observations([make_observation()])
        tampered = {**result, "abstained": True}
        with self.assertRaises(self.fusion.FusionError):
            self.fusion.validate_fusion_result(tampered)
        with self.assertRaises(self.fusion.FusionError):
            self.fusion.validate_fusion_result(
                {**result, "schema_version": "0.9.0"}
            )
        with self.assertRaises(self.fusion.FusionError):
            self.fusion.fuse_observations([])


class InMemoryFusionStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        store_module = load_module(
            "openbrec_fusion_store_test", REPO_ROOT / "openbrec/fusion_store.py"
        )
        self.store_module = store_module
        self.store = store_module.InMemoryFusionStore()
        self.fusion = load_module(
            "openbrec_fusion_store_engine_test", REPO_ROOT / "openbrec/fusion.py"
        )

    def test_observation_recording_is_idempotent_and_consistent(self) -> None:
        observation = make_observation(zone_id="zone-a")
        self.store.record_observation(observation)
        self.store.record_observation(observation)
        self.assertEqual(len(self.store.list_observations()), 1)
        with self.assertRaises(self.store_module.FusionStoreError):
            self.store.record_observation({**observation, "quality": 0.4})

    def test_window_query_filters_zone_and_lookback(self) -> None:
        inside = make_observation(zone_id="zone-a")
        other_zone = make_observation(
            observation_id="55555555-5555-4555-8555-555555555557",
            sensor_id="synthetic-2",
            zone_id="zone-b",
        )
        outside = make_observation(
            observation_id="55555555-5555-4555-8555-555555555558",
            sensor_id="synthetic-3",
            zone_id="zone-a",
            window_start="2026-07-17T13:10:00.000000Z",
            window_end="2026-07-17T13:10:01.000000Z",
        )
        for observation in (inside, other_zone, outside):
            self.store.record_observation(observation)

        peers = self.store.observations_in_window(
            "zone-a", inside["window_start"], inside["window_end"]
        )
        self.assertEqual(
            [item["observation_id"] for item in peers],
            [inside["observation_id"]],
        )

    def test_fusion_result_round_trip_and_filters(self) -> None:
        result = self.fusion.fuse_observations(
            [make_observation(zone_id="zone-a")], zone_id="zone-a"
        )
        self.store.record_fusion_result(result)
        self.store.record_fusion_result(result)
        self.assertEqual(self.store.get_fusion_result(result["result_id"]), result)
        self.assertIsNone(self.store.get_fusion_result(str(uuid.uuid4())))
        self.assertEqual(
            self.store.list_fusion_results(state="indicator"), [result]
        )
        self.assertEqual(self.store.list_fusion_results(state="abstained"), [])
        self.assertEqual(self.store.list_fusion_results(zone_id="zone-b"), [])


class RecordingStore:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def ingest(self, raw: bytes, **kwargs):
        self.calls.append({"raw": raw, **kwargs})


class WorkerFusionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = load_module(
            "openbrec_runtime_fusion_test", REPO_ROOT / "openbrec/runtime.py"
        )
        self.worker = load_module(
            "openbrec_worker_fusion_test",
            REPO_ROOT / "apps/fusion-worker/openbrec_worker/worker.py",
        )
        store_module = load_module(
            "openbrec_fusion_store_worker_test",
            REPO_ROOT / "openbrec/fusion_store.py",
        )
        self.store_module = store_module

    def test_worker_persists_fusion_result_after_durable_ingest(self) -> None:
        fusion_store = self.store_module.InMemoryFusionStore()
        observation = make_observation(zone_id="zone-a")
        event = self.runtime.observation_to_event(observation)

        processed = self.worker.process_event(
            event,
            store=RecordingStore(),
            fusion_store=fusion_store,
            worker_id="worker-test",
        )

        self.assertEqual(processed["status"], "durably_processed")
        self.assertEqual(processed["fusion_state"], "indicator")
        result = fusion_store.get_fusion_result(processed["fusion_result_id"])
        self.assertIsNotNone(result)
        self.assertEqual(
            result["supporting_evidence_ids"], [observation["observation_id"]]
        )

        reprocessed = self.worker.process_event(
            event,
            store=RecordingStore(),
            fusion_store=fusion_store,
            worker_id="worker-test",
        )
        self.assertEqual(
            reprocessed["fusion_result_id"], processed["fusion_result_id"]
        )
        self.assertEqual(len(fusion_store.list_fusion_results()), 1)

    def test_worker_abstains_on_unusable_evidence(self) -> None:
        fusion_store = self.store_module.InMemoryFusionStore()
        observation = make_observation(quality=0.1)
        event = self.runtime.observation_to_event(observation)

        processed = self.worker.process_event(
            event,
            store=RecordingStore(),
            fusion_store=fusion_store,
            worker_id="worker-test",
        )

        self.assertEqual(processed["fusion_state"], "abstained")
        result = fusion_store.get_fusion_result(processed["fusion_result_id"])
        self.assertTrue(result["abstained"])
        self.assertEqual(
            result["abstention_reasons"], ["insufficient independent evidence"]
        )


class ApiReadPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = load_module(
            "openbrec_api_fusion_test", REPO_ROOT / "apps/api/openbrec_api/app.py"
        )
        self.worker = load_module(
            "openbrec_worker_api_test",
            REPO_ROOT / "apps/fusion-worker/openbrec_worker/worker.py",
        )
        store_module = load_module(
            "openbrec_fusion_store_api_test", REPO_ROOT / "openbrec/fusion_store.py"
        )
        self.fusion_store = store_module.InMemoryFusionStore()
        self.publisher = self.api.RecordingPublisher()

    def request(self, method: str, path: str, payload: dict | None = None):
        import httpx

        async def call() -> httpx.Response:
            app = self.api.create_app(
                publisher=self.publisher, reader=self.fusion_store
            )
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                if method == "post":
                    return await client.post(path, json=payload)
                return await client.get(path)

        return asyncio.run(call())

    def test_observation_flows_to_fusion_result_and_read_endpoints(self) -> None:
        observation = make_observation(zone_id="zone-a")
        response = self.request("post", "/v1/observations", observation)
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(len(self.publisher.messages), 1)

        _, event = self.publisher.messages[0]
        processed = self.worker.process_event(
            event,
            store=RecordingStore(),
            fusion_store=self.fusion_store,
            worker_id="worker-test",
        )

        listed = self.request("get", "/v1/observations")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(
            [item["observation_id"] for item in listed.json()["items"]],
            [observation["observation_id"]],
        )
        by_zone = self.request("get", "/v1/observations?zone_id=zone-a")
        self.assertEqual(len(by_zone.json()["items"]), 1)
        other_zone = self.request("get", "/v1/observations?zone_id=zone-b")
        self.assertEqual(other_zone.json()["items"], [])

        results = self.request("get", "/v1/fusion-results")
        self.assertEqual(results.status_code, 200, results.text)
        items = results.json()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["result_id"], processed["fusion_result_id"])
        self.assertEqual(items[0]["state"], "indicator")
        self.assertEqual(
            items[0]["supporting_evidence_ids"], [observation["observation_id"]]
        )

        detail = self.request(
            "get", f"/v1/fusion-results/{processed['fusion_result_id']}"
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["schema_version"], "1.0.0")
        missing = self.request("get", f"/v1/fusion-results/{uuid.uuid4()}")
        self.assertEqual(missing.status_code, 404)

    def test_read_endpoints_validate_query_parameters(self) -> None:
        invalid_type = self.request("get", "/v1/observations?sensor_type=lidar")
        self.assertEqual(invalid_type.status_code, 422)
        invalid_state = self.request("get", "/v1/fusion-results?state=confirmed")
        self.assertEqual(invalid_state.status_code, 422)
        invalid_limit = self.request("get", "/v1/fusion-results?limit=0")
        self.assertEqual(invalid_limit.status_code, 422)

    def test_read_endpoints_report_unavailable_store(self) -> None:
        store_module = load_module(
            "openbrec_fusion_store_offline_test",
            REPO_ROOT / "openbrec/fusion_store.py",
        )
        offline_store = store_module.PostgresFusionStore("host=invalid dbname=x")

        import httpx

        async def call() -> httpx.Response:
            app = self.api.create_app(
                publisher=self.publisher, reader=offline_store
            )
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                return await client.get("/v1/fusion-results")

        response = asyncio.run(call())
        self.assertEqual(response.status_code, 503)


@unittest.skipUnless(DOCKER_AVAILABLE, DOCKER_MISSING_REASON)
class PostgresFusionStoreTests(unittest.TestCase):
    def test_postgres_fusion_store_round_trip(self) -> None:
        name = f"openbrec-fusion-test-{uuid.uuid4().hex[:12]}"
        password = "test-only-fusion-store-password"
        try:
            pull = subprocess.run(
                ["docker", "pull", POSTGRES_IMAGE],
                text=True,
                capture_output=True,
                check=False,
            )
            if pull.returncode != 0:
                self.skipTest(f"cannot pull pinned PostgreSQL image: {pull.stderr}")
            started = subprocess.run(
                [
                    "docker",
                    "run",
                    "--detach",
                    "--name",
                    name,
                    "--env",
                    f"POSTGRES_PASSWORD={password}",
                    "--env",
                    "POSTGRES_DB=openbrec",
                    "--publish",
                    "127.0.0.1::5432",
                    POSTGRES_IMAGE,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            for _ in range(60):
                ready = subprocess.run(
                    ["docker", "exec", name, "pg_isready", "-U", "postgres"],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if ready.returncode == 0:
                    break
                import time

                time.sleep(1)
            else:
                self.fail("PostgreSQL test container did not become ready")
            mapping = subprocess.run(
                ["docker", "port", name, "5432"],
                text=True,
                capture_output=True,
                check=False,
            )
            port = mapping.stdout.strip().rsplit(":", 1)[-1]
            store_module = load_module(
                "openbrec_fusion_store_pg_test",
                REPO_ROOT / "openbrec/fusion_store.py",
            )
            fusion = load_module(
                "openbrec_fusion_pg_test", REPO_ROOT / "openbrec/fusion.py"
            )
            store = store_module.PostgresFusionStore(
                f"host=127.0.0.1 port={port} dbname=openbrec "
                f"user=postgres password={password} connect_timeout=10"
            )
            store.connect()
            try:
                observation = make_observation(zone_id="zone-a")
                store.record_observation(observation)
                store.record_observation(observation)
                self.assertEqual(len(store.list_observations()), 1)
                peers = store.observations_in_window(
                    "zone-a",
                    observation["window_start"],
                    observation["window_end"],
                )
                self.assertEqual(
                    [item["observation_id"] for item in peers],
                    [observation["observation_id"]],
                )
                result = fusion.fuse_observations(peers, zone_id="zone-a")
                store.record_fusion_result(result)
                store.record_fusion_result(result)
                self.assertEqual(
                    store.get_fusion_result(result["result_id"]), result
                )
                self.assertEqual(
                    store.list_fusion_results(state="indicator"), [result]
                )
                import psycopg

                dsn = (
                    f"host=127.0.0.1 port={port} dbname=openbrec "
                    f"user=postgres password={password} connect_timeout=10"
                )
                with psycopg.connect(dsn) as second:
                    persisted = second.execute(
                        "SELECT result_id, state FROM fusion_results"
                    ).fetchall()
                self.assertEqual(persisted, [(result["result_id"], "indicator")])
            finally:
                store.close()
        finally:
            subprocess.run(
                ["docker", "rm", "--force", name],
                text=True,
                capture_output=True,
                check=False,
            )


if __name__ == "__main__":
    unittest.main()
