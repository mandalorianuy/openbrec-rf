from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class VerifyCliTests(unittest.TestCase):
    def run_verify(self, *args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "openbrec.verify", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_catalog(self, root: Path, *, sha256: str | None = None, path: str = "schemas/item.schema.json") -> Path:
        schema_path = root / path
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://openbrec.org/schemas/example/1.0.0",
            "title": "Example",
            "type": "object",
        }
        raw = json.dumps(schema, separators=(",", ":"), sort_keys=True).encode()
        schema_path.write_bytes(raw)
        catalog = {
            "catalog_version": "1.0.0",
            "draft": "https://json-schema.org/draft/2020-12/schema",
            "status": "legacy-unverified",
            "entries": [
                {
                    "path": path,
                    "$id": schema["$id"],
                    "declared_version": "1.0.0",
                    "sha256": sha256 or hashlib.sha256(raw).hexdigest(),
                }
            ],
        }
        catalog_path = root / "schemas/legacy/catalog.json"
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
        return catalog_path

    def test_schema_gate_accepts_matching_local_catalog_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            lockfile = root / "uv.lock"
            lockfile.write_text("version = 1\n", encoding="utf-8")
            receipt = root / "evidence/schema.json"

            result = self.run_verify(
                "schema",
                "--root",
                str(root),
                "--catalog",
                str(catalog.relative_to(root)),
                "--receipt",
                str(receipt.relative_to(root)),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(data["gate"], "schema")
            self.assertEqual(data["result"], "passed")
            self.assertEqual(data["summary"]["catalog_entries"], 1)
            self.assertEqual(
                data["lockfiles"],
                [{"path": "uv.lock", "sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest()}],
            )

    def test_schema_gate_rejects_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root, sha256="0" * 64)

            result = self.run_verify(
                "schema",
                "--root",
                str(root),
                "--catalog",
                str(catalog.relative_to(root)),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("sha256 mismatch", result.stderr)

    def test_schema_gate_rejects_uppercase_hash_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            data = json.loads(catalog.read_text(encoding="utf-8"))
            data["entries"][0]["sha256"] = data["entries"][0]["sha256"].upper()
            catalog.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_verify(
                "schema",
                "--root",
                str(root),
                "--catalog",
                str(catalog.relative_to(root)),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lowercase hexadecimal", result.stderr)

    def test_schema_gate_rejects_path_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            data = json.loads(catalog.read_text(encoding="utf-8"))
            data["entries"][0]["path"] = "../outside.schema.json"
            catalog.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_verify(
                "schema",
                "--root",
                str(root),
                "--catalog",
                str(catalog.relative_to(root)),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside repository root", result.stderr)

    def test_schema_gate_rejects_duplicate_schema_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            second_schema = root / "schemas/second.schema.json"
            second_schema.write_bytes((root / "schemas/item.schema.json").read_bytes())
            data = json.loads(catalog.read_text(encoding="utf-8"))
            duplicate = dict(data["entries"][0])
            duplicate["path"] = "schemas/second.schema.json"
            data["entries"].append(duplicate)
            catalog.write_text(json.dumps(data), encoding="utf-8")

            result = self.run_verify(
                "schema",
                "--root",
                str(root),
                "--catalog",
                str(catalog.relative_to(root)),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate schema $id", result.stderr)

    def test_bundle_structure_receipt_declares_structural_only_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "bundle-structure.json"

            result = self.run_verify(
                "bundle-structure",
                "--root",
                str(REPO_ROOT),
                "--receipt",
                str(receipt),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(data["gate"], "bundle-structure")
            self.assertEqual(data["scope"], "structural_only")
            self.assertEqual(data["result"], "passed")

    def test_bundle_structure_receipt_preserves_validator_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "validate_bundle.py").write_text(
                'print("Advertencias:")\nprint("- optional validator unavailable")\n',
                encoding="utf-8",
            )
            receipt = root / "evidence/bundle.json"

            result = self.run_verify(
                "bundle-structure",
                "--root",
                str(root),
                "--receipt",
                str(receipt.relative_to(root)),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(data["warnings"], ["optional validator unavailable"])


if __name__ == "__main__":
    unittest.main()
