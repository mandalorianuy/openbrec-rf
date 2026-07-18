from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN = REPO_ROOT / "docs/superpowers/plans/2026-07-17-openbrec-p1a-bench-conducted-plan.md"
POLICY = REPO_ROOT / "config/p1a/authorization-policy.json"
SCHEMA = REPO_ROOT / "schemas/p1a/capability-manifest.schema.json"
RESIDUALS = REPO_ROOT / "docs/governance/p1a-residuals.json"


class P1AReadinessTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_readiness_gate_is_registered(self) -> None:
        result = self.run_verify("p1a-readiness", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--policy", result.stdout)
        self.assertIn("--schema", result.stdout)
        self.assertIn("--residuals", result.stdout)

    def test_plan_preserves_eight_optional_tasks_without_starting_p1a_01(self) -> None:
        self.assertTrue(PLAN.is_file())
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("Estado: preservado como validación física opcional", source)
        self.assertIn("no bloquea Open Spec", source)
        self.assertIn("0 / 8", source)
        for index in range(1, 9):
            self.assertIn(f"P1a-{index:02d}", source)
        self.assertIn("P1a-01 no iniciada", source)
        self.assertIn("compra/préstamo no autorizado", source)
        self.assertIn("TX radiado prohibido", source)
        result = self.run_verify("p1a-readiness")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_policy_denies_external_and_physical_actions_by_default(self) -> None:
        self.assertTrue(POLICY.is_file())
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(value["policy_version"], "1.0.0")
        self.assertEqual(value["phase"], "P1a")
        self.assertEqual(value["progress"], {"accepted_tasks": 0, "total_tasks": 8, "percent": 0.0})
        self.assertEqual(
            {task["id"] for task in value["tasks"]},
            {f"P1a-{index:02d}" for index in range(1, 9)},
        )
        self.assertTrue(all(task["status"] == "not_started" for task in value["tasks"]))
        actions = value["actions"]
        for action in ("purchase", "loan", "hardware_use", "conducted_test", "human_study", "real_capture"):
            self.assertEqual(actions[action]["state"], "not_authorized")
            self.assertTrue(actions[action]["authorization_required"])
        self.assertEqual(actions["radiated_tx"]["state"], "prohibited_in_p1a")
        self.assertFalse(value["automatic_purchase"])

    def test_capability_manifest_schema_requires_exact_custody_evidence(self) -> None:
        self.assertTrue(SCHEMA.is_file())
        value = json.loads(SCHEMA.read_text(encoding="utf-8"))
        required = set(value["required"])
        self.assertTrue(
            {
                "asset_id",
                "category",
                "manufacturer",
                "model",
                "sku",
                "hardware_revision",
                "custody",
                "physical_inspection",
                "support_status",
            }.issubset(required)
        )
        self.assertEqual(
            value["properties"]["support_status"]["enum"], ["unverified"]
        )
        self.assertFalse(value["additionalProperties"])

    def test_all_readiness_residuals_have_owner_gate_and_stop(self) -> None:
        self.assertTrue(RESIDUALS.is_file())
        value = json.loads(RESIDUALS.read_text(encoding="utf-8"))
        rows = value["residuals"]
        self.assertGreaterEqual(len(rows), 8)
        self.assertEqual(len(rows), len({row["id"] for row in rows}))
        for row in rows:
            self.assertIn(row["state"], {"controlled", "planned", "blocked"})
            self.assertTrue(row["owner"])
            self.assertTrue(row["gate_or_task"])
            self.assertTrue(row["stop_condition"])

    def test_gate_fails_closed_when_purchase_is_preauthorized(self) -> None:
        self.assertTrue(POLICY.is_file())
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        value["actions"]["purchase"]["state"] = "authorized"
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            mutated = Path(directory) / "authorization-policy.json"
            mutated.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify("p1a-readiness", "--policy", str(mutated))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("purchase must remain not_authorized", result.stderr)

    def test_ci_runs_readiness_as_an_independent_non_physical_gate(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  p1a-readiness:", workflow)
        job = workflow.split("  p1a-readiness:", 1)[1]
        self.assertIn("openbrec.verify p1a-readiness", job)
        self.assertIn("evidence/p1a/readiness", job)
        self.assertNotIn("docker", job)
        self.assertNotIn("hardware", job)


if __name__ == "__main__":
    unittest.main()
