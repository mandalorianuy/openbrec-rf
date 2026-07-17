from __future__ import annotations

import copy
import importlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = REPO_ROOT / "fixtures/replay/core/m0-six-node.json"


def require_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"required M0-05 module is missing: {relative_path}")
    return importlib.import_module(name)


def scenario() -> dict:
    if not SCENARIO_PATH.is_file():
        raise AssertionError(f"required M0-05 scenario is missing: {SCENARIO_PATH}")
    return json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


class SixNodeScenarioTests(unittest.TestCase):
    def test_scenario_declares_six_nodes_two_tracks_three_zones_and_all_faults(
        self,
    ) -> None:
        data = scenario()

        self.assertEqual(len(data["nodes"]), 6)
        self.assertEqual(len(data["tracks"]), 2)
        self.assertEqual(len(data["zones"]), 3)
        self.assertEqual(
            {fault["kind"] for fault in data["faults"]},
            {
                "loss",
                "duplicate",
                "partition",
                "brownout",
                "restart",
                "malicious_peer",
            },
        )
        for node in data["nodes"]:
            manifest = node["capability_manifest"]
            self.assertTrue(manifest["capabilities"])
            self.assertTrue(manifest["capabilities_absent"])

    def test_simulation_is_order_independent_and_matches_expected_projection_hash(
        self,
    ) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        simulator = require_module("openbrec.simulator", "openbrec/simulator.py")
        data = scenario()

        first = simulator.run_scenario(data, repository_root=REPO_ROOT)
        reordered = copy.deepcopy(data)
        reordered["nodes"].reverse()
        reordered["tracks"].reverse()
        reordered["faults"].reverse()
        second = simulator.run_scenario(reordered, repository_root=REPO_ROOT)

        self.assertEqual(first["result_sha256"], second["result_sha256"])
        self.assertEqual(
            canonical.canonical_hash(first["projection"]),
            data["expected"]["projection_sha256"],
        )
        self.assertEqual(first["disposition"]["unreconciled"], 0)

    def test_faults_degrade_coverage_without_creating_presence_or_absence_claims(
        self,
    ) -> None:
        simulator = require_module("openbrec.simulator", "openbrec/simulator.py")
        data = scenario()

        baseline = simulator.run_scenario(
            data, repository_root=REPO_ROOT, active_faults=[]
        )
        degraded = simulator.run_scenario(data, repository_root=REPO_ROOT)

        self.assertLess(
            degraded["zone_summary"]["zone-bravo"]["confidence"],
            baseline["zone_summary"]["zone-bravo"]["confidence"],
        )
        self.assertNotEqual(
            degraded["zone_summary"]["zone-bravo"]["coverage"],
            baseline["zone_summary"]["zone-bravo"]["coverage"],
        )
        for zone in degraded["zone_summary"].values():
            self.assertEqual(zone["state"], "abstained")
            self.assertNotIn("person_present", zone)
            self.assertNotIn("person_absent", zone)
        self.assertEqual(
            degraded["fault_outcomes"],
            {
                "brownout": "confidence_degraded",
                "duplicate": "deduplicated",
                "loss": "coverage_degraded",
                "malicious_peer": "quarantined",
                "partition": "capability_absent",
                "restart": "new_boot_session_preserved",
            },
        )

    def test_projection_exposes_semantic_layers_and_required_explanation_fields(
        self,
    ) -> None:
        simulator = require_module("openbrec.simulator", "openbrec/simulator.py")
        result = simulator.run_scenario(scenario(), repository_root=REPO_ROOT)
        projection = result["projection"]

        self.assertEqual(projection["semantic_layers"], [
            "observation",
            "evidence",
            "fusion_result",
        ])
        self.assertEqual(len(projection["nodes"]), 6)
        self.assertEqual(len(projection["tracks"]), 2)
        self.assertEqual(len(projection["zones"]), 3)
        for item in projection["results"]:
            for field in (
                "timestamp",
                "zone_id",
                "precision",
                "confidence",
                "sources",
                "capabilities_absent",
                "explanation",
                "state",
            ):
                self.assertIn(field, item)
            self.assertEqual(item["state"], "abstained")
            self.assertTrue(item["capabilities_absent"])

    def test_simulator_gate_exercises_ten_order_variations(self) -> None:
        gates = require_module("openbrec.gates_m0_05", "openbrec/gates_m0_05.py")

        errors, _warnings, summary = gates.run_simulator_gate(
            REPO_ROOT, SCENARIO_PATH
        )

        self.assertEqual(errors, [])
        self.assertEqual(summary["runs"], 10)
        self.assertEqual(len(summary["unique_result_hashes"]), 1)


class ExplainablePwaSourceTests(unittest.TestCase):
    def test_pwa_contains_map_capability_timeline_and_semantic_inspector(self) -> None:
        source = (REPO_ROOT / "apps/web/src/main.tsx").read_text(encoding="utf-8")

        for marker in (
            'data-testid="operations-map"',
            'data-testid="capability-matrix"',
            'data-testid="event-timeline"',
            'data-testid="semantic-inspector"',
            "Observación",
            "Evidencia",
            "Inferencia",
            "Capacidades ausentes",
            "Abstención",
        ):
            self.assertIn(marker, source)
        lowered = source.lower()
        for prohibited in ("persona detectada", "zona vacía", "sin víctimas"):
            self.assertNotIn(prohibited, lowered)

    def test_pwa_has_loopback_only_ingress_and_runtime_offline_cache(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        service_worker = (REPO_ROOT / "apps/web/public/sw.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '127.0.0.1:${OPENBREC_WEB_PORT:-8080}:8080',
            compose,
        )
        self.assertIn('/m0-projection.json', service_worker)
        self.assertIn("cache.put", service_worker)

    def test_ui_smoke_drives_chromium_and_reloads_after_network_loss(self) -> None:
        smoke_path = REPO_ROOT / "apps/web/scripts/ui-smoke.mjs"

        self.assertTrue(smoke_path.is_file())
        smoke = smoke_path.read_text(encoding="utf-8")
        self.assertIn('from "playwright"', smoke)
        self.assertIn("context.setOffline(true)", smoke)
        self.assertIn('getByTestId("semantic-inspector")', smoke)
        self.assertIn('getByTestId("event-timeline")', smoke)

    def test_pwa_declares_a_local_favicon_without_browser_404s(self) -> None:
        index = (REPO_ROOT / "apps/web/index.html").read_text(encoding="utf-8")

        self.assertIn('href="/favicon.svg"', index)
        self.assertTrue((REPO_ROOT / "apps/web/public/favicon.svg").is_file())

    def test_map_node_overlays_do_not_block_zone_selection(self) -> None:
        stylesheet = (REPO_ROOT / "apps/web/src/style.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(".map-node { pointer-events: none; }", stylesheet)
        self.assertIn(".track-line { pointer-events: none; }", stylesheet)


if __name__ == "__main__":
    unittest.main()
