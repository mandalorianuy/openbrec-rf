from __future__ import annotations

import base64
import importlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]


def require_module(name: str, relative_path: str):
    path = REPO_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"required M0-06 module is missing: {relative_path}")
    return importlib.import_module(name)


class SupplyChainGateTests(unittest.TestCase):
    def test_secret_scanner_detects_dummy_and_repo_has_no_unapproved_secret(
        self,
    ) -> None:
        supply_chain = require_module(
            "openbrec.supply_chain", "openbrec/supply_chain.py"
        )
        dummy = b"ghp_" + b"A1b2C3d4" * 5

        self.assertTrue(supply_chain.scan_bytes(dummy, path="synthetic-negative.txt"))
        errors, _warnings, summary = supply_chain.run_secret_scan(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(summary["negative_secret_dummy"], "detected")
        self.assertEqual(summary["findings"], 0)

    def test_sbom_is_deterministic_cyclonedx_and_license_complete(self) -> None:
        canonical = require_module("openbrec.canonical", "openbrec/canonical.py")
        supply_chain = require_module(
            "openbrec.supply_chain", "openbrec/supply_chain.py"
        )

        first = supply_chain.build_sbom(REPO_ROOT)
        second = supply_chain.build_sbom(REPO_ROOT)
        self.assertEqual(first["bomFormat"], "CycloneDX")
        self.assertEqual(first["specVersion"], "1.7")
        self.assertEqual(
            canonical.canonical_hash(first), canonical.canonical_hash(second)
        )
        self.assertGreater(len(first["components"]), 20)
        self.assertTrue(
            any(item["name"] == "openbrec-rf" for item in first["components"])
        )
        containers = [
            item for item in first["components"] if item.get("type") == "container"
        ]
        self.assertEqual(len(containers), 5)
        self.assertTrue(
            all(
                item.get("hashes", [{}])[0].get("alg") == "SHA-256"
                for item in containers
            )
        )

        errors, _warnings, summary = supply_chain.run_license_gate(REPO_ROOT, first)
        self.assertEqual(errors, [])
        self.assertEqual(summary["missing_license"], 0)
        self.assertEqual(summary["denied_license"], 0)

    def test_vulnerability_parser_detects_synthetic_findings(self) -> None:
        supply_chain = require_module(
            "openbrec.supply_chain", "openbrec/supply_chain.py"
        )
        python_report = {
            "dependencies": [
                {
                    "name": "synthetic-package",
                    "version": "0.0.1",
                    "vulns": [{"id": "PYSEC-SYNTHETIC-1"}],
                }
            ]
        }
        node_report = {
            "metadata": {
                "vulnerabilities": {
                    "info": 0,
                    "low": 0,
                    "moderate": 0,
                    "high": 1,
                    "critical": 0,
                }
            }
        }
        errors, summary = supply_chain.summarize_vulnerability_reports(
            python_report, [node_report]
        )
        self.assertEqual(summary["known_vulnerabilities"], 2)
        self.assertTrue(errors)

    def test_container_inputs_are_pinned_by_digest(self) -> None:
        dockerfiles = [
            (REPO_ROOT / "apps/api/Dockerfile").read_text(encoding="utf-8"),
            (REPO_ROOT / "apps/web/Dockerfile").read_text(encoding="utf-8"),
        ]
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        for source in dockerfiles:
            for line in source.splitlines():
                if line.startswith("FROM "):
                    self.assertIn("@sha256:", line)
        for line in compose.splitlines():
            if line.strip().startswith("image:") and "openbrec/" not in line:
                self.assertIn("@sha256:", line)


class KeyLifecycleTests(unittest.TestCase):
    def test_rotation_recovery_revocation_zeroization_and_rollback_fail_closed(
        self,
    ) -> None:
        keyring = require_module("openbrec.keyring", "openbrec/keyring.py")
        registry = keyring.KeyRegistry.single(
            key_id="lab-key-1", key=b"a" * 32, epoch=1
        )
        registry.rotate(key_id="lab-key-2", key=b"b" * 32, epoch=2)
        self.assertEqual(registry.active_key_id, "lab-key-2")
        self.assertEqual(registry.resolve("lab-key-1"), b"a" * 32)

        recovery = registry.export_recovery(wrapping_key=b"w" * 32, nonce=b"n" * 12)
        restored = keyring.KeyRegistry.recover(
            recovery, wrapping_key=b"w" * 32, minimum_epoch=2
        )
        self.assertEqual(restored.resolve("lab-key-2"), b"b" * 32)
        with self.assertRaises(keyring.KeyRollbackDetected):
            keyring.KeyRegistry.recover(
                recovery, wrapping_key=b"w" * 32, minimum_epoch=3
            )

        restored.revoke("lab-key-2")
        with self.assertRaises(keyring.KeyUnavailable):
            restored.active_key()
        restored.zeroize("lab-key-1")
        with self.assertRaises(keyring.KeyUnavailable):
            restored.resolve("lab-key-1")

    def test_secret_file_loader_rejects_missing_default_and_invalid_material(
        self,
    ) -> None:
        keyring = require_module("openbrec.keyring", "openbrec/keyring.py")
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(keyring.KeyUnavailable):
                keyring.load_secret_key(missing)
            invalid = Path(directory) / "invalid"
            invalid.write_text(base64.b64encode(b"short").decode(), encoding="utf-8")
            with self.assertRaises(keyring.KeyUnavailable):
                keyring.load_secret_key(invalid)


class RuntimeDurabilityTests(unittest.TestCase):
    def test_offline_gate_requires_postgres_durability_and_reconciliation(self) -> None:
        source = (REPO_ROOT / "openbrec/verify/cli.py").read_text(encoding="utf-8")
        self.assertIn('smoke_result.get("postgres_durable") != "passed"', source)
        self.assertIn('smoke_result.get("unreconciled") != 0', source)

    def test_runtime_wraps_observation_as_deterministic_domain_event(self) -> None:
        runtime = require_module("openbrec.runtime", "openbrec/runtime.py")
        semantic = require_module("openbrec.semantic", "openbrec/semantic.py")
        observation = json.loads(
            (
                REPO_ROOT
                / "fixtures/contracts/core/1.0.0/observation/valid/minimal.json"
            ).read_text(encoding="utf-8")
        )

        first = runtime.observation_to_event(observation)
        second = runtime.observation_to_event(observation)
        self.assertEqual(first, second)
        self.assertEqual(first["event_type"], "observation")
        semantic.validate_event(first, REPO_ROOT)

    def test_postgres_boundary_and_compose_secrets_are_declared(self) -> None:
        require_module(
            "openbrec.postgres_disposition", "openbrec/postgres_disposition.py"
        )
        migration = REPO_ROOT / "migrations/postgresql/0001_m0_disposition.sql"
        self.assertTrue(migration.is_file())
        sql = migration.read_text(encoding="utf-8")
        for table in (
            "ingress_units",
            "accepted_event_log",
            "review_quarantine",
            "evidence_vault",
            "rejection_ledger",
            "audit_events",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", sql)
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("OPENBREC_POSTGRES_PASSWORD_FILE", compose)
        self.assertIn("OPENBREC_MASTER_KEY_FILE", compose)
        self.assertIn("openbrec_master_key", compose)

    def test_environment_secret_fallback_is_restricted_to_explicit_gate(self) -> None:
        postgres = require_module(
            "openbrec.postgres_disposition", "openbrec/postgres_disposition.py"
        )
        environment = {
            "OPENBREC_POSTGRES_PASSWORD_FILE": "/missing/postgres",
            "OPENBREC_MASTER_KEY_FILE": "/missing/key",
            "OPENBREC_POSTGRES_PASSWORD": "synthetic-password",
            "OPENBREC_MASTER_KEY_B64": base64.b64encode(b"k" * 32).decode(),
            "OPENBREC_MASTER_KEY_ID": "lab-key-1",
        }
        with (
            patch.dict("os.environ", environment, clear=True),
            patch.object(postgres.PostgresDispositionStore, "connect"),
        ):
            with self.assertRaisesRegex(RuntimeError, "ephemeral gate"):
                postgres.PostgresDispositionStore.from_environment(
                    repository_root=REPO_ROOT
                )


class ExitOrchestrationTests(unittest.TestCase):
    def run_verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python", "-m", "openbrec.verify", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_new_gates_and_all_plan_are_registered(self) -> None:
        for gate in (
            "secret-scan",
            "sbom",
            "licenses",
            "key-lifecycle",
            "postgres-disposition",
            "vulnerability-scan",
        ):
            result = self.run_verify(gate, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)

        planned = self.run_verify("all", "--plan-only")
        self.assertEqual(planned.returncode, 0, planned.stderr)
        value = json.loads(planned.stdout)
        self.assertEqual(value["result"], "planned")
        for gate in ("bundle-structure", "ui-smoke", "secret-scan", "sbom", "licenses"):
            self.assertIn(gate, value["gates"])

    def test_ci_has_independent_jobs_and_no_single_bundle_substitute(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/validate.yml").read_text(
            encoding="utf-8"
        )
        for job in (
            "contracts",
            "runtime",
            "replay",
            "privacy-security",
            "simulation-ui",
            "supply-chain",
            "m0-exit",
        ):
            self.assertIn(f"  {job}:\n", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)

    def test_receipt_integrity_detects_altered_output_hash(self) -> None:
        cli = require_module("openbrec.verify.cli", "openbrec/verify/cli.py")
        receipt = {
            "git_sha": "a" * 40,
            "dirty": False,
            "result": "passed",
            "summary": {"count": 1},
            "errors": [],
            "warnings": [],
            "runtime": {"python": "3.12.0"},
            "lockfiles": [{"path": "uv.lock", "sha256": "b" * 64}],
            "inputs": [{"path": "input", "sha256": "c" * 64}],
            "output_sha256": "0" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            errors = cli.validate_receipt(
                path, expected_git_sha="a" * 40, require_clean=True
            )
        self.assertTrue(any("output_sha256" in error for error in errors))

    def test_runtime_receipt_tolerates_optional_tool_absence(self) -> None:
        cli = require_module("openbrec.verify.cli", "openbrec/verify/cli.py")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            versions = cli._runtime_versions()
        self.assertIsNotNone(versions["python"])
        self.assertIsNone(versions["node"])
        self.assertIsNone(versions["pnpm"])
        self.assertIsNone(versions["docker"])


if __name__ == "__main__":
    unittest.main()
