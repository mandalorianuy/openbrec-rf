from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GUIDES = (
    "quickstart-offgrid.md",
    "deployment-planning.md",
    "energy.md",
    "transports.md",
    "messaging-sos.md",
    "beacons.md",
    "federation.md",
    "building-reuse.md",
    "validation-troubleshooting.md",
)

REFERENCE_BUILDS = (
    "personal-team-kit.md",
    "response-cell.md",
    "federated-deployment.md",
)

PRACTICAL_HEADINGS = (
    "## Objetivo",
    "## Audiencia",
    "## Prerrequisitos",
    "## Capacidades necesarias",
    "## Alternativas permitidas",
    "## Componentes e interfaces",
    "## Pasos",
    "## Resultado esperado",
    "## Validación mínima",
    "## Fallos comunes y recuperación",
    "## Safety, privacidad y preservación",
    "## Estado de evidencia",
    "## Qué no demuestra",
    "## Contratos normativos relacionados",
)


class DocumentationProgramTests(unittest.TestCase):
    def load_validator(self):
        script = ROOT / "scripts/validate_docs.py"
        spec = importlib.util.spec_from_file_location("validate_docs", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def read_required(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"missing documentation artifact: {path}")
        return path.read_text(encoding="utf-8")

    def test_program_plan_closes_doc_01_through_doc_05(self) -> None:
        plan = ROOT / (
            "docs/superpowers/plans/"
            "2026-07-18-openbrec-documentation-program-plan.md"
        )
        source = self.read_required(plan)
        for index in range(1, 6):
            self.assertIn(f"[x] **DOC-{index:02d}", source)
        self.assertIn("cinco entregables", source)
        self.assertIn("no depende de P1a", source)

    def test_information_architecture_has_six_layers_and_one_start_here(self) -> None:
        architecture = ROOT / "docs/DOCUMENTATION_ARCHITECTURE.md"
        source = self.read_required(architecture)
        for layer in (
            "A. Open Spec normativa",
            "B. Reference implementation",
            "C. Manuales y guías",
            "D. Reference builds",
            "E. Evidence packs",
            "F. Field profiles",
        ):
            self.assertIn(layer, source)
        self.assertTrue((ROOT / "docs/START_HERE.md").is_file())
        compatibility = ROOT / "docs/open-spec/reference-builds"
        self.assertTrue(compatibility.is_dir())
        for name in (
            "README.md",
            "energy-site.md",
            "machine-telemetry.md",
            "human-messaging.md",
            "beacon-node.md",
            "response-cell-gateway.md",
        ):
            source = self.read_required(compatibility / name)
            self.assertIn("Alias de compatibilidad", source)
            self.assertIn("docs/reference-builds", source)

    def test_practical_guides_have_the_shared_contract(self) -> None:
        for name in GUIDES:
            path = ROOT / "docs/guides" / name
            source = self.read_required(path)
            for heading in PRACTICAL_HEADINGS:
                self.assertIn(heading, source, f"{name}: {heading}")

    def test_three_solution_reference_builds_are_practical_and_replaceable(
        self,
    ) -> None:
        for name in REFERENCE_BUILDS:
            path = ROOT / "docs/reference-builds" / name
            source = self.read_required(path)
            for heading in PRACTICAL_HEADINGS:
                self.assertIn(heading, source, f"{name}: {heading}")
            self.assertIn("reemplaz", source.lower())
            self.assertIn("no demuestra", source.lower())

    def test_readme_is_public_entry_point_not_a_physical_gate_report(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for token in (
            "Open Spec normativa",
            "Reference implementation",
            "Start Here",
            "Quickstart off-grid",
            "Meshtastic",
            "MeshCore",
            "Reticulum",
            "LoRaWAN",
            "life-safety-first",
            "bench-validated",
            "field-validated",
            "Kit mínimo personal/equipo",
            "ResponseCell",
            "Deployment federado",
        ):
            self.assertIn(token, readme)
        self.assertIn("docs/START_HERE.md", readme)
        self.assertIn("docs/reference-builds/README.md", readme)
        self.assertLess(readme.count("P1a"), 8)

    def test_documentation_validator_accepts_current_public_tree(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_docs.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("documentation valid", result.stdout)

    def test_documentation_validator_rejects_a_broken_internal_link(self) -> None:
        module = self.load_validator()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            markdown = root / "README.md"
            markdown.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            errors = module.validate_markdown_links(root, [markdown])
        self.assertTrue(any("missing target" in error for error in errors))

    def test_documentation_validator_parses_json_and_yaml_examples(self) -> None:
        module = self.load_validator()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.md"
            valid.write_text(
                '```json\n{"status": "specified"}\n```\n'
                "```yaml\nstatus: simulated\n```\n",
                encoding="utf-8",
            )
            invalid = root / "invalid.md"
            invalid.write_text("```json\n{broken}\n```\n", encoding="utf-8")
            self.assertEqual(module.validate_fenced_examples(root, [valid]), [])
            errors = module.validate_fenced_examples(root, [invalid])
        self.assertTrue(any("invalid json example" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
