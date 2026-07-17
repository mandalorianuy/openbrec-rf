from __future__ import annotations

import importlib.util
import asyncio
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_OBSERVATION = (
    REPO_ROOT / "fixtures/contracts/core/1.0.0/observation/valid/minimal.json"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RuntimeContractTests(unittest.TestCase):
    def test_runtime_validates_observation_against_normative_schema(self) -> None:
        runtime_path = REPO_ROOT / "openbrec/runtime.py"
        self.assertTrue(runtime_path.is_file(), "runtime contract boundary is missing")
        runtime = load_module("openbrec_runtime_test", runtime_path)
        valid = json.loads(VALID_OBSERVATION.read_text(encoding="utf-8"))

        self.assertEqual(runtime.validate_observation(valid), valid)
        invalid = {**valid, "unexpected": True}
        with self.assertRaises(runtime.ContractValidationError):
            runtime.validate_observation(invalid)

    def test_api_rejects_invalid_input_before_publish(self) -> None:
        api_path = REPO_ROOT / "apps/api/openbrec_api/app.py"
        self.assertTrue(api_path.is_file(), "FastAPI service is missing")
        api = load_module("openbrec_api_test", api_path)
        import httpx

        publisher = api.RecordingPublisher()
        valid = json.loads(VALID_OBSERVATION.read_text(encoding="utf-8"))

        async def post(payload: dict) -> httpx.Response:
            transport = httpx.ASGITransport(app=api.create_app(publisher=publisher))
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                return await client.post("/v1/observations", json=payload)

        response = asyncio.run(post(valid))
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["observation_id"], valid["observation_id"])
        self.assertEqual(len(publisher.messages), 1)

        invalid = {**valid, "observation_kind": "human_detected"}
        response = asyncio.run(post(invalid))
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(len(publisher.messages), 1)

    def test_worker_revalidates_before_producing_processed_state(self) -> None:
        worker_path = REPO_ROOT / "apps/fusion-worker/openbrec_worker/worker.py"
        self.assertTrue(worker_path.is_file(), "async worker is missing")
        worker = load_module("openbrec_worker_test", worker_path)
        valid = json.loads(VALID_OBSERVATION.read_text(encoding="utf-8"))

        processed = worker.process_observation(valid, worker_id="worker-test")
        self.assertEqual(processed["status"], "processed")
        self.assertEqual(processed["observation_id"], valid["observation_id"])
        with self.assertRaises(worker.ContractValidationError):
            worker.process_observation({**valid, "quality": 2})

    def test_worker_acknowledges_domain_event_only_after_durable_ingest(self) -> None:
        runtime = load_module(
            "openbrec_runtime_event_test", REPO_ROOT / "openbrec/runtime.py"
        )
        worker = load_module(
            "openbrec_worker_durable_test",
            REPO_ROOT / "apps/fusion-worker/openbrec_worker/worker.py",
        )
        observation = json.loads(VALID_OBSERVATION.read_text(encoding="utf-8"))
        event = runtime.observation_to_event(observation)

        class RecordingStore:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def ingest(self, raw: bytes, **kwargs):
                self.calls.append({"raw": raw, **kwargs})

        store = RecordingStore()
        processed = worker.process_event(event, store=store, worker_id="worker-test")

        self.assertEqual(len(store.calls), 1)
        self.assertEqual(processed["status"], "durably_processed")
        self.assertEqual(processed["observation_id"], observation["observation_id"])


class RuntimePackagingTests(unittest.TestCase):
    def test_compose_declares_contained_healthy_lab_sim(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("change-me", compose)
        self.assertIn("internal: true", compose)
        self.assertIn("mosquitto_pub", compose)
        self.assertIn("-q", compose)
        for service in ("mqtt", "postgres", "api", "fusion-worker", "web"):
            self.assertIn(f"  {service}:\n", compose)
        self.assertGreaterEqual(compose.count("healthcheck:"), 5)
        mqtt_block = compose.split("  mqtt:\n", 1)[1].split("  postgres:\n", 1)[0]
        postgres_block = compose.split("  postgres:\n", 1)[1].split("  api:\n", 1)[0]
        self.assertNotIn("ports:", mqtt_block)
        self.assertNotIn("ports:", postgres_block)

    def test_web_is_an_installable_offline_shell(self) -> None:
        web = REPO_ROOT / "apps/web"
        required = (
            "package.json",
            "index.html",
            "public/manifest.webmanifest",
            "public/sw.js",
            "src/main.tsx",
        )
        for relative in required:
            self.assertTrue(
                (web / relative).is_file(), f"missing PWA asset: {relative}"
            )
        service_worker = (web / "public/sw.js").read_text(encoding="utf-8")
        self.assertIn("caches.open", service_worker)
        self.assertIn("offline", service_worker.lower())
        nginx = (web / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("pid /tmp/nginx.pid", nginx)
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("tmpfs: [/tmp, /var/cache/nginx, /var/run]", compose)

    def test_runtime_smoke_requires_postgres_durability_before_success(self) -> None:
        smoke = (REPO_ROOT / "apps/api/openbrec_api/smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"postgres_durable": "passed"', smoke)
        self.assertIn("accepted_event_log", smoke)
        self.assertIn("unreconciled", smoke)


if __name__ == "__main__":
    unittest.main()
