from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md"
POLICY = ROOT / "config/open-spec/governance.json"
PROFILES = ROOT / "specs/openbrec/1.0.0-draft.1/reference-build-profiles.json"
BUILD_SCHEMA = ROOT / "schemas/open-spec/reference-build-manifest.schema.json"
ADAPTER_SCHEMA = ROOT / "schemas/open-spec/reuse-adapter-manifest.schema.json"
FIXTURES = ROOT / "fixtures/open-spec/builds/conformance-examples.json"
GUIDE_INDEX = ROOT / "docs/open-spec/reference-builds/README.md"
RESIDUALS = ROOT / "docs/governance/open-spec-build-residuals.json"
RECEIPT = ROOT / "evidence/open-spec/os-07/os-07-receipt.json"
ACCEPTANCE = ROOT / "evidence/open-spec/os-07/acceptance.json"

ADDONS = {
    "energy",
    "machine_telemetry",
    "human_messaging",
    "beacon_sensing",
    "recursive_federation",
}
ROUTES = {"open_build", "reuse_existing", "hybrid"}


class OpenSpecBuildTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def load_json(self, path: Path) -> dict[str, object]:
        self.assertTrue(path.is_file(), f"missing normative artifact: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_gate_is_registered_with_normative_inputs(self) -> None:
        result = self.run_verify("open-spec-builds", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in (
            "--profiles",
            "--build-schema",
            "--adapter-schema",
            "--fixtures",
            "--guide-index",
            "--residuals",
        ):
            self.assertIn(option, result.stdout)

    def test_os_07_remains_accepted_after_os_08_closure(self) -> None:
        source = PLAN.read_text(encoding="utf-8")
        self.assertIn("8 / 8", source)
        self.assertIn("OS-07 — aceptada", source)
        self.assertIn("OS-08 — aceptada", source)
        policy = self.load_json(POLICY)
        self.assertEqual(
            policy["progress"],
            {"accepted_tasks": 8, "total_tasks": 8, "percent": 100.0},
        )
        tasks = policy["tasks"]
        self.assertEqual([task["status"] for task in tasks], ["accepted"] * 8)

    def test_profiles_cover_every_addon_and_all_three_delivery_routes(self) -> None:
        profiles = self.load_json(PROFILES)
        builds = profiles["reference_builds"]
        self.assertEqual({row["addon"] for row in builds}, ADDONS)
        for row in builds:
            self.assertEqual(set(row["delivery_routes"]), ROUTES)
            self.assertFalse(row["required_for_spec"])
            self.assertTrue(row["substitution_allowed"])

    def test_open_boundary_keeps_hardware_vendor_and_physical_evidence_optional(
        self,
    ) -> None:
        boundary = self.load_json(PROFILES)["open_boundary"]
        for field in (
            "owned_hardware_required",
            "named_vendor_required",
            "named_sku_required",
            "physical_evidence_blocks_spec",
            "reference_build_is_field_ready",
            "reference_build_is_certified",
        ):
            self.assertFalse(boundary[field])
        self.assertTrue(boundary["capability_equivalent_substitution_allowed"])
        self.assertTrue(boundary["existing_components_reusable"])

    def test_build_schema_is_closed_and_all_build_examples_conform(self) -> None:
        schema = self.load_json(BUILD_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        builds = self.load_json(FIXTURES)["build_manifests"]
        self.assertEqual(len(builds), len(ADDONS))
        for index, row in enumerate(builds):
            self.assertEqual(list(validator.iter_errors(row)), [], f"build {index}")
            self.assertEqual(row["evidence_level"], "specified")
            self.assertFalse(row["physical_performance_claimed"])
            self.assertFalse(row["field_readiness_claimed"])

    def test_adapter_schema_is_closed_and_reuse_examples_conform(self) -> None:
        schema = self.load_json(ADAPTER_SCHEMA)
        Draft202012Validator.check_schema(schema)
        self.assertFalse(schema["additionalProperties"])
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        adapters = self.load_json(FIXTURES)["adapter_manifests"]
        self.assertGreaterEqual(len(adapters), 8)
        for index, row in enumerate(adapters):
            self.assertEqual(list(validator.iter_errors(row)), [], f"adapter {index}")
            self.assertIn(
                row["support_status"], {"experimental", "unverified", "unavailable"}
            )
            self.assertFalse(row["writes_facts_directly"])
            self.assertTrue(row["limitations"])

    def test_boms_use_capability_roles_and_never_single_source_parts(self) -> None:
        builds = self.load_json(FIXTURES)["build_manifests"]
        encoded = json.dumps(builds, sort_keys=True).lower()
        self.assertNotIn('"vendor"', encoded)
        self.assertNotIn('"sku"', encoded)
        self.assertNotIn('"product_url"', encoded)
        for build in builds:
            self.assertGreaterEqual(len(build["bom"]), 3)
            for item in build["bom"]:
                self.assertTrue(item["capability_role"])
                self.assertTrue(item["selection_criteria"])
                self.assertGreaterEqual(len(item["substitution_classes"]), 2)
                self.assertFalse(item["single_source_required"])

    def test_plans_include_interfaces_safe_steps_verification_and_rollback(
        self,
    ) -> None:
        builds = self.load_json(FIXTURES)["build_manifests"]
        for build in builds:
            self.assertTrue(build["interfaces"])
            self.assertGreaterEqual(len(build["assembly_steps"]), 3)
            self.assertGreaterEqual(len(build["verification_steps"]), 3)
            self.assertTrue(build["safety_stop_conditions"])
            self.assertTrue(build["rollback_and_disassembly"])
            self.assertTrue(build["capabilities_absent"])

    def test_guides_exist_for_every_build_and_support_discovery_first_reuse(
        self,
    ) -> None:
        profiles = self.load_json(PROFILES)
        index = GUIDE_INDEX.read_text(encoding="utf-8")
        self.assertIn("inventario de capacidades", index.lower())
        self.assertIn("reutilizar", index.lower())
        self.assertIn("no acredita", index.lower())
        for row in profiles["reference_builds"]:
            guide = ROOT / row["guide_ref"]
            self.assertTrue(guide.is_file(), row["guide_ref"])
            source = guide.read_text(encoding="utf-8")
            for heading in (
                "## Alcance",
                "## Plano funcional",
                "## BOM por capacidades",
                "## Reutilización",
                "## Verificación",
                "## Límites",
            ):
                self.assertIn(heading, source)

    def test_adapter_compatibility_is_bounded_versioned_and_reversible(self) -> None:
        adapters = self.load_json(FIXTURES)["adapter_manifests"]
        for row in adapters:
            self.assertTrue(row["interface_contract_ref"])
            self.assertTrue(row["version_constraint"])
            self.assertTrue(row["capability_mapping"])
            self.assertTrue(row["fallback"])
            self.assertTrue(row["disable_procedure"])
            self.assertTrue(row["evidence_required_to_promote"])

    def test_no_adapter_is_supported_without_exact_evidence(self) -> None:
        adapters = self.load_json(FIXTURES)["adapter_manifests"]
        self.assertFalse(any(row["support_status"] == "supported" for row in adapters))
        self.assertTrue(
            any(row["support_status"] == "experimental" for row in adapters)
        )
        self.assertTrue(any(row["support_status"] == "unverified" for row in adapters))

    def test_machine_and_human_planes_remain_separate_in_reference_builds(self) -> None:
        profiles = self.load_json(PROFILES)
        separation = profiles["plane_separation"]
        self.assertFalse(separation["human_plane_writes_observations"])
        self.assertFalse(separation["human_plane_writes_facts"])
        self.assertFalse(separation["machine_plane_accepts_sos"])
        self.assertTrue(separation["shared_enclosure_requires_coexistence_evidence"])
        self.assertTrue(separation["keys_queues_priorities_and_audit_separate"])

    def test_mutation_rejects_a_named_sku_requirement(self) -> None:
        from openbrec.open_spec_builds import run_open_spec_build_gate

        profiles = copy.deepcopy(self.load_json(PROFILES))
        profiles["open_boundary"]["named_sku_required"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            path.write_text(json.dumps(profiles), encoding="utf-8")
            errors, _, _, _ = run_open_spec_build_gate(
                ROOT,
                profiles_path=path,
                build_schema_path=BUILD_SCHEMA,
                adapter_schema_path=ADAPTER_SCHEMA,
                fixtures_path=FIXTURES,
                guide_index_path=GUIDE_INDEX,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("SKU" in error for error in errors))

    def test_mutation_rejects_supported_without_evidence(self) -> None:
        from openbrec.open_spec_builds import run_open_spec_build_gate

        fixtures = copy.deepcopy(self.load_json(FIXTURES))
        fixtures["adapter_manifests"][0]["support_status"] = "supported"
        fixtures["adapter_manifests"][0]["support_evidence_refs"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixtures.json"
            path.write_text(json.dumps(fixtures), encoding="utf-8")
            errors, _, _, _ = run_open_spec_build_gate(
                ROOT,
                profiles_path=PROFILES,
                build_schema_path=BUILD_SCHEMA,
                adapter_schema_path=ADAPTER_SCHEMA,
                fixtures_path=path,
                guide_index_path=GUIDE_INDEX,
                residuals_path=RESIDUALS,
            )
        self.assertTrue(any("supported" in error for error in errors))

    def test_residuals_are_governed_without_blocking_open_publication(self) -> None:
        value = self.load_json(RESIDUALS)
        self.assertEqual(value["task"], "OS-07")
        self.assertGreaterEqual(len(value["residuals"]), 10)
        for row in value["residuals"]:
            self.assertIn(
                row["state"],
                {"resolved", "controlled", "planned", "evidence_required"},
            )
            self.assertFalse(row["blocks_open_spec"])
            for field in (
                "owner",
                "risk",
                "disposition",
                "gate_or_task",
                "stop_condition",
            ):
                self.assertTrue(row[field])

    def test_summary_points_only_to_optional_p1a_01(self) -> None:
        result = self.run_verify("open-spec-builds")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)["summary"]
        self.assertEqual(summary["spec_tasks_accepted"], 8)
        self.assertEqual(summary["spec_tasks_total"], 8)
        self.assertEqual(summary["addons_covered"], 5)
        self.assertEqual(summary["delivery_routes"], 3)
        self.assertEqual(summary["next_task"], "P1a-01")
        self.assertFalse(summary["next_task_started"])
        self.assertFalse(summary["physical_build_blocks_publication"])

    def test_readme_board_and_ci_publish_os_07_gate(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        board = (ROOT / "DELIVERY_BOARD.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("Open Spec está `8 / 8`", readme)
        self.assertIn("Open Spec `8 / 8`", board)
        self.assertIn("open-spec-builds:", workflow)
        self.assertIn("tests.test_open_spec_builds", workflow)

    def test_acceptance_references_a_clean_passing_receipt(self) -> None:
        receipt = self.load_json(RECEIPT)
        acceptance = self.load_json(ACCEPTANCE)
        self.assertEqual(receipt["result"], "passed")
        self.assertFalse(receipt["dirty"])
        self.assertEqual(acceptance["task"], "OS-07")
        self.assertEqual(acceptance["status"], "accepted")
        self.assertEqual(
            acceptance["receipt"]["sha256"],
            hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
        )
        self.assertEqual(acceptance["next_task"], "OS-08")
        self.assertFalse(acceptance["next_task_started"])


if __name__ == "__main__":
    unittest.main()
