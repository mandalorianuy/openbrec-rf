from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schemas/p1a/capability-manifest.schema.json"
AUTHORIZATION_REQUEST = (
    REPO_ROOT / "docs/governance/p1a-01-asset-authorization-request.json"
)
PLAN = REPO_ROOT / "docs/superpowers/plans/2026-07-17-openbrec-p1a-bench-conducted-plan.md"
RESIDUALS = REPO_ROOT / "docs/governance/p1a-residuals.json"
CATEGORIES = (
    "lorawan_gateway",
    "lorawan_endpoint",
    "meshtastic_node",
    "meshcore_node",
    "rnode",
    "offline_terminal",
    "trimodal_beacon",
    "energy_storage",
    "wired_cell_gateway",
)
FIRMWARE_CATEGORIES = set(CATEGORIES) - {"energy_storage"}


class P1AAssetGateTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_complete_evidence(self, directory: Path) -> None:
        manifests = directory / "manifests"
        manifests.mkdir(parents=True)
        authorizations = []
        for index, category in enumerate(CATEGORIES, start=1):
            asset_id = f"p1a-asset-unit-{index:02d}"
            authorization_id = f"P1A-AUTH-{index:02d}"
            manifest = {
                "manifest_version": "1.0.0",
                "asset_id": asset_id,
                "candidate_id": f"P1A-HW-{index:02d}",
                "category": category,
                "manufacturer": f"Vendor {index}",
                "model": f"Model {index}",
                "sku": f"SKU-{index:02d}",
                "hardware_revision": f"rev-{index}",
                "serial_evidence_sha256": f"{index:064x}",
                "custody": {
                    "method": "existing_asset",
                    "authorization_id": authorization_id,
                    "custodian": "hardware-custody-owner",
                    "receipt_sha256": f"{index + 10:064x}",
                },
                "physical_inspection": {
                    "inspected_at": "2026-07-17T12:00:00Z",
                    "inspector": "hardware-custody-owner",
                    "condition": "serviceable",
                    "exact_match": True,
                    "evidence_sha256": f"{index + 20:064x}",
                },
                "capabilities": [f"declared-capability-{index}"],
                "support_status": "unverified",
                "limitations": ["Physical behavior remains unverified until its later P1a gate."],
            }
            if category in FIRMWARE_CATEGORIES:
                manifest["firmware_pin"] = {
                    "project": f"firmware-{index}",
                    "version": "1.0.0",
                    "commit": f"{index:040x}",
                    "artifact_sha256": f"{index + 30:064x}",
                    "advisory_reviewed_at": "2026-07-17",
                }
            (manifests / f"{category}.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            authorizations.append(
                {
                    "authorization_id": authorization_id,
                    "candidate_id": f"P1A-HW-{index:02d}",
                    "asset_id": asset_id,
                    "category": category,
                    "method": "existing_asset",
                    "state": "authorized_for_inventory_only",
                    "authorized_at": "2026-07-17T11:00:00Z",
                    "authorized_by": "asset-owner",
                    "custodian": "hardware-custody-owner",
                    "scope": ["physical_inspection", "custody_registration"],
                    "evidence_sha256": f"{index + 40:064x}",
                }
            )
        (directory / "authorization-register.json").write_text(
            json.dumps(
                {
                    "register_version": "1.0.0",
                    "task": "P1a-01",
                    "authorizations": authorizations,
                }
            ),
            encoding="utf-8",
        )

    def test_gate_is_registered_with_exact_evidence_arguments(self) -> None:
        result = self.run_verify("p1a-assets", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--evidence-dir", result.stdout)
        self.assertIn("--schema", result.stdout)

    def test_repository_evidence_fails_closed_until_assets_exist(self) -> None:
        result = self.run_verify(
            "p1a-assets", "--evidence-dir", "evidence/p1a/p1a-01"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("authorization register", result.stderr)
        self.assertIn("nine exact manifests", result.stderr)
        self.assertNotIn(str(REPO_ROOT), result.stderr)

    def test_complete_exact_authorized_inventory_passes_structural_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["accepted_assets"], 9)
        self.assertEqual(summary["category_denominator"], 9)
        self.assertEqual(summary["support_statuses"], {"unverified": 9})
        self.assertEqual(summary["authorization_mismatches"], 0)

    def test_duplicate_category_and_missing_category_fail(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            path = evidence_dir / "manifests" / "wired_cell_gateway.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["category"] = "energy_storage"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("categories must match the nine-category denominator", result.stderr)

    def test_placeholder_identity_and_unknown_condition_fail(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            path = evidence_dir / "manifests" / "rnode.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["sku"] = "TBD"
            value["physical_inspection"]["condition"] = "unknown"
            path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("placeholder identity", result.stderr)
        self.assertIn("inspection condition cannot remain unknown", result.stderr)

    def test_authorization_must_match_asset_candidate_category_and_custodian(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register = evidence_dir / "authorization-register.json"
            value = json.loads(register.read_text(encoding="utf-8"))
            value["authorizations"][0]["custodian"] = "different-custodian"
            register.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("authorization does not match manifest", result.stderr)

    def test_firmware_capable_asset_requires_immutable_pin_and_advisory_review(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            path = evidence_dir / "manifests" / "meshtastic_node.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            del value["firmware_pin"]
            path.write_text(json.dumps(value), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("immutable firmware pin", result.stderr)

    def test_authorization_request_governs_all_categories_without_fabricating_approval(self) -> None:
        self.assertTrue(AUTHORIZATION_REQUEST.is_file())
        value = json.loads(AUTHORIZATION_REQUEST.read_text(encoding="utf-8"))
        self.assertEqual(value["task"], "P1a-01")
        self.assertEqual(value["status"], "blocked_external_evidence")
        self.assertEqual(value["progress"], {"accepted_tasks": 0, "total_tasks": 8, "percent": 0.0})
        self.assertFalse(value["physical_actions_authorized"])
        self.assertFalse(value["purchase_authorized"])
        rows = value["asset_requests"]
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["category"] for row in rows}, set(CATEGORIES))
        self.assertEqual(
            {row["candidate_id"] for row in rows},
            {f"P1A-HW-{index:02d}" for index in range(1, 10)},
        )
        for row in rows:
            self.assertEqual(row["state"], "awaiting_explicit_authorization")
            self.assertNotIn("authorization_id", row)
            self.assertTrue(row["required_external_evidence"])
        self.assertEqual(value["next_task_if_accepted"], "P1a-02")
        self.assertFalse(value["next_task_started"])

    def test_ci_proves_the_repository_inventory_remains_blocked(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  p1a-assets-blocked:", workflow)
        job = workflow.split("  p1a-assets-blocked:", 1)[1]
        self.assertIn("openbrec.verify p1a-assets", job)
        self.assertIn("evidence/p1a/p1a-01", job)
        self.assertIn("test $gate_status -eq 1", job)
        self.assertIn('receipt["result"] == "failed"', job)
        self.assertIn("p1a-01-blocked-receipt", job)

    def test_plan_and_board_record_blocked_status_without_progress(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        board = (REPO_ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for source in (plan, board):
            self.assertIn("P1a-01", source)
            self.assertIn("blocked_external_evidence", source)
            self.assertIn("0 / 8", source)
            self.assertIn("P1a-02 no iniciada", source)
        self.assertIn("openbrec.verify p1a-assets", readme)
        self.assertIn("blocked_external_evidence", readme)

    def test_asset_residuals_are_blocked_with_a_durable_resolution_path(self) -> None:
        value = json.loads(RESIDUALS.read_text(encoding="utf-8"))
        by_id = {row["id"]: row for row in value["residuals"]}
        for identifier in ("P1A-R001", "P1A-R002"):
            self.assertEqual(by_id[identifier]["state"], "blocked")
            self.assertIn("P1a-01", by_id[identifier]["gate_or_task"])
            self.assertTrue(by_id[identifier]["resolution_artifact"])
            self.assertTrue(by_id[identifier]["next_action"])


if __name__ == "__main__":
    unittest.main()
