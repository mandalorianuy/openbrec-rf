from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACEABILITY = REPO_ROOT / "docs/governance/p0-traceability.json"
SUPPORT = REPO_ROOT / "docs/governance/p0-support-status.json"
SHORTLIST = REPO_ROOT / "docs/governance/p1a-hardware-shortlist.json"
RESIDUALS = REPO_ROOT / "docs/governance/p0-residual-closure.json"


class P009ExitTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_exit_and_independent_governance_gates_are_registered(self) -> None:
        for gate in (
            "p0-traceability",
            "p0-support-status",
            "p0-residuals",
            "p0-all",
        ):
            result = self.run_verify(gate, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)

        planned = self.run_verify("p0-all", "--plan-only")
        self.assertEqual(planned.returncode, 0, planned.stderr)
        value = json.loads(planned.stdout)
        self.assertEqual(value["result"], "planned")
        self.assertEqual(len(value["gates"]), len(set(value["gates"])))
        self.assertGreaterEqual(len(value["gates"]), 27)
        for gate in (
            "addon-contracts",
            "energy-replay",
            "human-message-security",
            "transport-comparison",
            "federation-scale",
            "terminal-ux",
            "beacon-replay",
            "p0-integrated",
            "secret-scan",
            "sbom",
            "licenses",
            "vulnerability-scan",
            "p0-traceability",
            "p0-support-status",
            "p0-residuals",
        ):
            self.assertIn(gate, value["gates"])

    def test_traceability_maps_every_p0_task_to_fixture_gate_and_receipt(self) -> None:
        value = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
        rows = value["requirements"]
        self.assertEqual(value["matrix_version"], "1.0.0")
        self.assertEqual(
            {row["task"] for row in rows},
            {f"P0-{index:02d}" for index in range(1, 10)},
        )
        self.assertTrue(all(row["fixtures"] for row in rows))
        self.assertTrue(all(row["gate"] for row in rows))
        self.assertTrue(all(row["receipt"] for row in rows))
        self.assertTrue(all(row["status"] == "accepted" for row in rows))

    def test_support_is_profile_scoped_and_never_globally_supported(self) -> None:
        value = json.loads(SUPPORT.read_text(encoding="utf-8"))
        rows = value["support_matrix"]
        allowed = {"experimental", "unverified", "unavailable", "deferred"}
        self.assertEqual(value["claim_scope"], "simulation_only")
        self.assertEqual(value["global_winner"], None)
        self.assertEqual(len(rows), 9)
        self.assertEqual(
            {row["profile"] for row in rows},
            {"mobile-ad-hoc", "urban-planned", "backbone-heterogeneous"},
        )
        self.assertEqual(
            {row["bearer"] for row in rows},
            {"meshtastic", "meshcore", "reticulum"},
        )
        self.assertTrue(all(row["status"] in allowed for row in rows))
        self.assertTrue(all(row["version"] and row["commit"] for row in rows))
        self.assertTrue(all(row["scenario"] for row in rows))
        self.assertNotIn("supported", {row["status"] for row in rows})

    def test_p1a_shortlist_is_one_unverified_unit_per_category_no_purchase(self) -> None:
        value = json.loads(SHORTLIST.read_text(encoding="utf-8"))
        rows = value["categories"]
        categories = [row["category"] for row in rows]
        self.assertEqual(len(categories), len(set(categories)))
        self.assertGreaterEqual(len(categories), 8)
        for row in rows:
            self.assertEqual(len(row["candidates"]), 1)
            candidate = row["candidates"][0]
            self.assertEqual(candidate["support_status"], "unverified")
            self.assertEqual(candidate["disposition"], "shortlisted_no_purchase")
            self.assertTrue(candidate["separate_authorization_required"])

    def test_every_residual_has_terminal_governance_for_p0(self) -> None:
        value = json.loads(RESIDUALS.read_text(encoding="utf-8"))
        rows = value["residuals"]
        self.assertEqual(
            {row["id"] for row in rows},
            {f"P0-R{index:03d}" for index in range(1, 16)},
        )
        self.assertTrue(
            all(row["state"] in {"resolved", "controlled", "planned"} for row in rows)
        )
        self.assertTrue(all(row["owner"] for row in rows))
        self.assertTrue(all(row["gate_or_plan"] for row in rows))
        self.assertTrue(all(row["stop_condition"] for row in rows))
        self.assertFalse(any(row.get("due_task") == "P0-09" for row in rows))

    def test_governance_gates_fail_independently_on_mutation(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            root = Path(directory)
            for gate, source, mutation in (
                (
                    "p0-traceability",
                    TRACEABILITY,
                    lambda value: value["requirements"][0].update(fixtures=[]),
                ),
                (
                    "p0-support-status",
                    SUPPORT,
                    lambda value: value["support_matrix"][0].update(status="supported"),
                ),
                (
                    "p0-residuals",
                    RESIDUALS,
                    lambda value: value["residuals"][0].update(owner=""),
                ),
            ):
                value = json.loads(source.read_text(encoding="utf-8"))
                mutation(value)
                artifact = root / source.name
                artifact.write_text(json.dumps(value), encoding="utf-8")
                result = self.run_verify(gate, "--artifact", str(artifact))
                self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_ci_has_independent_p0_exit_job_and_receipts(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        job = workflow.split("  p0-exit:", 1)[1]
        self.assertIn("needs:", job)
        for dependency in (
            "contracts",
            "replay",
            "privacy-security",
            "transport-simulation",
            "federation-simulation",
            "simulation-ui",
            "beacon-simulation",
            "integrated-simulation",
            "supply-chain",
        ):
            self.assertIn(dependency, job)
        self.assertIn("openbrec.verify p0-all", job)
        self.assertIn("p0-exit-receipts", job)
        self.assertIn("git diff --exit-code", job)


if __name__ == "__main__":
    unittest.main()
