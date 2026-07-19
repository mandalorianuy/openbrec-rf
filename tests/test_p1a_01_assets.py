from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schemas/p1a/capability-manifest.schema.json"
LEGACY_SCHEMA = REPO_ROOT / "schemas/p1a/capability-manifest-1.0.0.schema.json"
AUTHORIZATION_SCHEMA = (
    REPO_ROOT / "schemas/p1a/asset-authorization-register.schema.json"
)
AUTHORIZATION_REQUEST = (
    REPO_ROOT / "docs/governance/p1a-01-asset-authorization-request.json"
)
PLAN = REPO_ROOT / "docs/superpowers/plans/2026-07-17-openbrec-p1a-bench-conducted-plan.md"
RESIDUALS = REPO_ROOT / "docs/governance/p1a-residuals.json"
INTAKE_GUIDE = REPO_ROOT / "docs/governance/P1A_ASSET_INTAKE.md"
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
            authorization_evidence_sha256 = f"{index + 40:064x}"
            manifest = {
                "manifest_version": "2.0.0",
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
                    "receipt_sha256": authorization_evidence_sha256,
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
                    "advisory_review": {
                        "reviewed_at": "2026-07-17",
                        "reviewer": "release-reviewer",
                        "sources": [
                            {
                                "locator": f"https://example.invalid/firmware-{index}/advisories",
                                "retrieved_at": "2026-07-17T12:30:00Z",
                                "evidence_sha256": f"{index + 50:064x}",
                            }
                        ],
                        "disposition": "no_known_blocker",
                        "reason": "Synthetic fixture with no declared blocker.",
                    },
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
                    "evidence_sha256": authorization_evidence_sha256,
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

    def test_authorization_register_has_a_closed_schema_cli_contract(self) -> None:
        self.assertTrue(AUTHORIZATION_SCHEMA.is_file())
        schema = json.loads(AUTHORIZATION_SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["$defs"]["authorization"]["additionalProperties"])
        for gate in ("p1a-assets-intake", "p1a-assets"):
            result = self.run_verify(gate, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--authorization-schema", result.stdout)

    def test_capability_manifest_v2_preserves_v1_contract(self) -> None:
        self.assertTrue(LEGACY_SCHEMA.is_file())
        current = json.loads(SCHEMA.read_text(encoding="utf-8"))
        legacy = json.loads(LEGACY_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(current["properties"]["manifest_version"]["const"], "2.0.0")
        self.assertTrue(current["$id"].endswith("/2.0.0"))
        self.assertEqual(legacy["properties"]["manifest_version"]["const"], "1.0.0")
        self.assertTrue(legacy["$id"].endswith("/1.0.0"))
        review = current["properties"]["firmware_pin"]["properties"][
            "advisory_review"
        ]
        self.assertFalse(review["additionalProperties"])
        self.assertEqual(
            set(review["required"]),
            {"reviewed_at", "reviewer", "sources", "disposition", "reason"},
        )

    def test_repository_evidence_fails_closed_until_assets_exist(self) -> None:
        result = self.run_verify(
            "p1a-assets", "--evidence-dir", "evidence/p1a/p1a-01"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("authorization register", result.stderr)
        self.assertIn("nine exact manifests", result.stderr)
        self.assertNotIn(str(REPO_ROOT), result.stderr)

    def test_intake_preflight_lists_every_missing_category_without_progress(
        self,
    ) -> None:
        result = self.run_verify(
            "p1a-assets-intake", "--evidence-dir", "evidence/p1a/p1a-01"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["summary"]
        self.assertEqual(summary["task"], "P1a-01")
        self.assertEqual(summary["task_status"], "blocked_external_evidence")
        self.assertEqual(summary["category_denominator"], 9)
        self.assertEqual(summary["categories_ready_for_gate"], 0)
        self.assertEqual(summary["categories_awaiting_external_evidence"], 9)
        self.assertEqual(summary["accepted_tasks"], 0)
        self.assertFalse(summary["physical_actions_authorized"])
        self.assertFalse(summary["next_task_started"])
        rows = summary["category_checklist"]
        self.assertEqual({row["category"] for row in rows}, set(CATEGORIES))
        for row in rows:
            self.assertEqual(row["status"], "awaiting_external_evidence")
            self.assertFalse(row["authorization_present"])
            self.assertFalse(row["manifest_present"])
            self.assertTrue(row["missing_external_evidence"])

    def test_intake_preflight_rejects_candidate_category_drift(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            request_path = Path(temporary) / "authorization-request.json"
            request = json.loads(
                AUTHORIZATION_REQUEST.read_text(encoding="utf-8")
            )
            request["asset_requests"][0]["candidate_id"] = "P1A-HW-09"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                "evidence/p1a/p1a-01",
                "--request",
                str(request_path.relative_to(REPO_ROOT)),
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate_id does not match governed category", result.stderr)

    def test_intake_preflight_validates_partial_submission_before_counting_it(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["authorizations"] = register["authorizations"][:1]
            register_path.write_text(json.dumps(register), encoding="utf-8")
            manifests = evidence_dir / "manifests"
            for path in manifests.glob("*.json"):
                if path.name != "lorawan_gateway.json":
                    path.unlink()

            manifest_path = manifests / "lorawan_gateway.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["sku"] = "TBD"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            invalid = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
            )
            self.assertNotEqual(invalid.returncode, 0, invalid.stdout)
            self.assertIn("placeholder identity", invalid.stderr)

            manifest["sku"] = "SKU-01"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            valid = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
            )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        summary = json.loads(valid.stdout)["summary"]
        self.assertEqual(summary["task_status"], "blocked_external_evidence")
        self.assertEqual(summary["categories_valid_for_gate"], 1)
        self.assertEqual(summary["categories_invalid"], 0)
        self.assertEqual(summary["categories_awaiting_external_evidence"], 8)
        row = summary["category_checklist"][0]
        self.assertEqual(row["status"], "validated_for_acceptance_gate")
        self.assertEqual(row["validation_errors"], [])
        self.assertEqual(summary["accepted_tasks"], 0)

    def test_intake_rejects_unknown_authorization_fields(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["authorizations"] = register["authorizations"][:1]
            register["authorizations"][0]["implicit_approval"] = True
            register_path.write_text(json.dumps(register), encoding="utf-8")
            result = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Additional properties are not allowed", result.stderr)
        self.assertIn("implicit_approval", result.stderr)

    def test_intake_rejects_duplicate_asset_id_across_categories(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["authorizations"] = register["authorizations"][:2]
            duplicate_asset_id = register["authorizations"][0]["asset_id"]
            register["authorizations"][1]["asset_id"] = duplicate_asset_id
            register_path.write_text(json.dumps(register), encoding="utf-8")

            manifests = evidence_dir / "manifests"
            for path in manifests.glob("*.json"):
                if path.name not in {"lorawan_gateway.json", "lorawan_endpoint.json"}:
                    path.unlink()
            endpoint_path = manifests / "lorawan_endpoint.json"
            endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
            endpoint["asset_id"] = duplicate_asset_id
            endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")

            receipt_path = evidence_dir / "intake-receipt.json"

            result = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(receipt_path.relative_to(REPO_ROOT)),
            )
            summary = json.loads(receipt_path.read_text(encoding="utf-8"))["summary"]

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("asset_id is reused across categories", result.stderr)
        self.assertEqual(summary["categories_invalid"], 2)
        self.assertEqual(summary["duplicate_asset_id_groups"], 1)
        self.assertEqual(
            [row["status"] for row in summary["category_checklist"][:2]],
            ["invalid_submission", "invalid_submission"],
        )

    def test_intake_rejects_duplicate_serial_evidence_across_categories(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["authorizations"] = register["authorizations"][:2]
            register_path.write_text(json.dumps(register), encoding="utf-8")

            manifests = evidence_dir / "manifests"
            for path in manifests.glob("*.json"):
                if path.name not in {"lorawan_gateway.json", "lorawan_endpoint.json"}:
                    path.unlink()
            gateway = json.loads(
                (manifests / "lorawan_gateway.json").read_text(encoding="utf-8")
            )
            endpoint_path = manifests / "lorawan_endpoint.json"
            endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
            endpoint["serial_evidence_sha256"] = gateway["serial_evidence_sha256"]
            endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")

            receipt_path = evidence_dir / "intake-receipt.json"

            result = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(receipt_path.relative_to(REPO_ROOT)),
            )
            summary = json.loads(receipt_path.read_text(encoding="utf-8"))["summary"]

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("serial evidence is reused across categories", result.stderr)
        self.assertEqual(summary["categories_invalid"], 2)
        self.assertEqual(summary["duplicate_serial_evidence_groups"], 1)

    def test_intake_rejects_reused_authorization_id_across_categories(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            register["authorizations"] = register["authorizations"][:2]
            duplicate_authorization_id = register["authorizations"][0][
                "authorization_id"
            ]
            register["authorizations"][1][
                "authorization_id"
            ] = duplicate_authorization_id
            register_path.write_text(json.dumps(register), encoding="utf-8")

            manifests = evidence_dir / "manifests"
            for path in manifests.glob("*.json"):
                if path.name not in {"lorawan_gateway.json", "lorawan_endpoint.json"}:
                    path.unlink()
            endpoint_path = manifests / "lorawan_endpoint.json"
            endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
            endpoint["custody"]["authorization_id"] = duplicate_authorization_id
            endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")
            receipt_path = evidence_dir / "intake-receipt.json"

            result = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(receipt_path.relative_to(REPO_ROOT)),
            )
            summary = json.loads(receipt_path.read_text(encoding="utf-8"))["summary"]

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("authorization_id is reused across categories", result.stderr)
        self.assertEqual(summary["duplicate_authorization_id_groups"], 1)
        self.assertEqual(
            [row["status"] for row in summary["category_checklist"][:2]],
            ["invalid_submission", "invalid_submission"],
        )

    def test_intake_and_gate_reject_unbound_custody_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            manifest_path = evidence_dir / "manifests" / "lorawan_gateway.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["custody"]["receipt_sha256"] = f"{999:064x}"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            intake_receipt_path = evidence_dir / "intake-receipt.json"
            intake = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(intake_receipt_path.relative_to(REPO_ROOT)),
            )
            intake_summary = json.loads(
                intake_receipt_path.read_text(encoding="utf-8")
            )["summary"]
            gate_receipt_path = evidence_dir / "gate-receipt.json"
            gate = self.run_verify(
                "p1a-assets",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(gate_receipt_path.relative_to(REPO_ROOT)),
            )
            gate_summary = json.loads(gate_receipt_path.read_text(encoding="utf-8"))[
                "summary"
            ]

        self.assertNotEqual(intake.returncode, 0, intake.stdout)
        self.assertNotEqual(gate.returncode, 0, gate.stdout)
        self.assertIn(
            "custody receipt does not match authorization evidence", intake.stderr
        )
        self.assertIn(
            "custody receipt does not match authorization evidence", gate.stderr
        )
        self.assertEqual(intake_summary["custody_receipt_mismatches"], 1)
        self.assertEqual(gate_summary["custody_receipt_mismatches"], 1)

    def test_intake_and_gate_reject_reused_authorization_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            register_path = evidence_dir / "authorization-register.json"
            register = json.loads(register_path.read_text(encoding="utf-8"))
            duplicate_evidence = register["authorizations"][0]["evidence_sha256"]
            register["authorizations"][1]["evidence_sha256"] = duplicate_evidence
            register_path.write_text(json.dumps(register), encoding="utf-8")
            endpoint_path = evidence_dir / "manifests" / "lorawan_endpoint.json"
            endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
            endpoint["custody"]["receipt_sha256"] = duplicate_evidence
            endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")

            intake_receipt_path = evidence_dir / "intake-receipt.json"
            intake = self.run_verify(
                "p1a-assets-intake",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(intake_receipt_path.relative_to(REPO_ROOT)),
            )
            intake_summary = json.loads(
                intake_receipt_path.read_text(encoding="utf-8")
            )["summary"]
            gate_receipt_path = evidence_dir / "gate-receipt.json"
            gate = self.run_verify(
                "p1a-assets",
                "--evidence-dir",
                str(evidence_dir.relative_to(REPO_ROOT)),
                "--receipt",
                str(gate_receipt_path.relative_to(REPO_ROOT)),
            )
            gate_summary = json.loads(gate_receipt_path.read_text(encoding="utf-8"))[
                "summary"
            ]

        self.assertNotEqual(intake.returncode, 0, intake.stdout)
        self.assertNotEqual(gate.returncode, 0, gate.stdout)
        self.assertIn(
            "authorization evidence is reused across categories", intake.stderr
        )
        self.assertIn("authorization evidence is reused across categories", gate.stderr)
        self.assertEqual(intake_summary["duplicate_authorization_evidence_groups"], 1)
        self.assertEqual(gate_summary["duplicate_authorization_evidence_groups"], 1)

    def test_gate_rejects_duplicate_serial_evidence_across_assets(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            manifests = evidence_dir / "manifests"
            gateway = json.loads(
                (manifests / "lorawan_gateway.json").read_text(encoding="utf-8")
            )
            endpoint_path = manifests / "lorawan_endpoint.json"
            endpoint = json.loads(endpoint_path.read_text(encoding="utf-8"))
            endpoint["serial_evidence_sha256"] = gateway["serial_evidence_sha256"]
            endpoint_path.write_text(json.dumps(endpoint), encoding="utf-8")

            receipt_path = evidence_dir / "gate-receipt.json"

            result = self.run_verify(
                "p1a-assets",
                "--evidence-dir",
                str(evidence_dir),
                "--receipt",
                str(receipt_path.relative_to(REPO_ROOT)),
            )
            summary = json.loads(receipt_path.read_text(encoding="utf-8"))["summary"]

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("serial evidence must be unique per physical asset", result.stderr)
        self.assertEqual(summary["duplicate_serial_evidence_groups"], 1)

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

    def test_date_only_firmware_review_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            path = evidence_dir / "manifests" / "meshtastic_node.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["manifest_version"] = "1.0.0"
            firmware_pin = value["firmware_pin"]
            firmware_pin.pop("advisory_review", None)
            firmware_pin["advisory_reviewed_at"] = "2026-07-17"
            path.write_text(json.dumps(value), encoding="utf-8")

            result = self.run_verify(
                "p1a-assets", "--evidence-dir", str(evidence_dir)
            )

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("manifest_version", result.stderr)
        self.assertIn("advisory_review", result.stderr)

    def test_blocked_advisory_disposition_remains_visible(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temporary:
            evidence_dir = Path(temporary)
            self.write_complete_evidence(evidence_dir)
            path = evidence_dir / "manifests" / "meshtastic_node.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            firmware_pin = value["firmware_pin"]
            firmware_pin.pop("advisory_reviewed_at", None)
            firmware_pin["advisory_review"] = {
                "reviewed_at": "2026-07-17",
                "reviewer": "release-reviewer",
                "sources": [
                    {
                        "locator": "https://example.invalid/security-advisories",
                        "retrieved_at": "2026-07-17T12:30:00Z",
                        "evidence_sha256": f"{91:064x}",
                    }
                ],
                "disposition": "block_firmware_use",
                "reason": "A governed blocker remains open.",
            }
            path.write_text(json.dumps(value), encoding="utf-8")
            receipt_path = evidence_dir / "gate-receipt.json"

            result = self.run_verify(
                "p1a-assets",
                "--evidence-dir",
                str(evidence_dir),
                "--receipt",
                str(receipt_path.relative_to(REPO_ROOT)),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["summary"]["firmware_advisory_blockers"], 1)
        self.assertTrue(
            any(
                "firmware use remains blocked" in warning
                for warning in receipt["warnings"]
            )
        )

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
            self.assertIn(
                "authorization and custody receipt binding",
                row["required_external_evidence"],
            )
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

    def test_intake_preflight_is_documented_and_published_by_ci(self) -> None:
        self.assertTrue(INTAKE_GUIDE.is_file())
        guide = INTAKE_GUIDE.read_text(encoding="utf-8")
        self.assertIn("openbrec.verify p1a-assets-intake", guide)
        self.assertIn("no acepta P1a-01", guide)
        self.assertIn("0 / 8", guide)
        self.assertIn("invalid_submission", guide)
        self.assertIn("validated_for_acceptance_gate", guide)
        self.assertIn("asset-authorization-register.schema.json", guide)
        self.assertIn("additionalProperties", guide)
        self.assertIn("asset_id", guide)
        self.assertIn("serial_evidence_sha256", guide)
        self.assertIn("no pueden reutilizarse", guide)
        self.assertNotIn("sólo indica que existen ambos archivos", guide)

        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        job = workflow.split("  p1a-assets-blocked:", 1)[1]
        self.assertIn("openbrec.verify p1a-assets-intake", job)
        self.assertIn("--authorization-schema", job)
        self.assertIn("asset-authorization-register.schema.json", job)
        self.assertIn("p1a-01-intake-receipt", job)
        self.assertIn('task_status"] == "blocked_external_evidence"', job)
        self.assertIn('categories_invalid"] == 0', job)
        self.assertIn('categories_valid_for_gate"] == 0', job)
        self.assertIn('accepted_tasks"] == 0', job)
        self.assertIn('firmware_advisory_blockers"] == 0', job)
        self.assertIn('firmware_use_authorized"] is False', job)

    def test_firmware_contract_migration_is_documented(self) -> None:
        guide = INTAKE_GUIDE.read_text(encoding="utf-8")
        self.assertIn("capability-manifest-1.0.0.schema.json", guide)
        self.assertIn("manifest_version: 2.0.0", guide)
        self.assertIn("block_firmware_use", guide)
        self.assertIn("no ejecuta una revisión real", guide)

    def test_authorization_evidence_binding_is_documented_and_published(self) -> None:
        guide = INTAKE_GUIDE.read_text(encoding="utf-8")
        plan = PLAN.read_text(encoding="utf-8")
        board = (REPO_ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for source in (guide, plan, board, readme):
            self.assertIn("authorization_id", source)
            self.assertIn("receipt_sha256", source)
            self.assertIn("evidencia de", source)
            self.assertIn("autorización", source)

        residuals = json.loads(RESIDUALS.read_text(encoding="utf-8"))
        authorization = next(
            row for row in residuals["residuals"] if row["id"] == "P1A-R001"
        )
        self.assertIn("receipt_sha256", authorization["stop_condition"])
        self.assertIn("por asset", authorization["next_action"])

        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        job = workflow.split("  p1a-assets-blocked:", 1)[1]
        self.assertIn('duplicate_authorization_id_groups"] == 0', job)
        self.assertIn('duplicate_authorization_evidence_groups"] == 0', job)
        self.assertIn('duplicate_custody_receipt_groups"] == 0', job)
        self.assertIn('custody_receipt_mismatches"] == 0', job)

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
        firmware = by_id["P1A-R003"]
        self.assertEqual(firmware["state"], "controlled")
        self.assertIn("P1a-01", firmware["gate_or_task"])
        self.assertTrue(firmware["resolution_artifact"])
        self.assertTrue(firmware["next_action"])


if __name__ == "__main__":
    unittest.main()
