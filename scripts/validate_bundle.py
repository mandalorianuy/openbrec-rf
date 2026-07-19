#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    required = [
        'README.md', 'docs/legacy/OPENBREC_RF_TECHNICAL_DESIGN.md',
        'docs/legacy/BOM.md',
        'AGENTS.md', 'CODEX_MASTER_PROMPT.md', 'docker-compose.yml',
        'DELIVERY_BOARD.md', 'SECURITY.md', 'LICENSE', 'NOTICE.md',
        'docs/legacy/08-ruview-evaluation.md', 'docs/legacy/09-drone-deployment.md',
        'docs/legacy/10-rf-quieting.md',
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            errors.append(f'falta {rel}')

    forbidden_extensions = {'.docx', '.xlsx', '.pptx'}
    for path in ROOT.rglob('*'):
        if path.is_file() and path.suffix.lower() in forbidden_extensions:
            errors.append(f'artefacto binario no permitido: {path.relative_to(ROOT)}')

    for path in sorted((ROOT / 'schemas').glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('$schema') != 'https://json-schema.org/draft/2020-12/schema':
                errors.append(f'{path.relative_to(ROOT)}: draft inesperado')
            if 'title' not in data or data.get('type') != 'object':
                errors.append(f'{path.relative_to(ROOT)}: falta title/type object')
        except Exception as exc:
            errors.append(f'{path.relative_to(ROOT)}: JSON inválido: {exc}')

    try:
        import yaml  # type: ignore
        for path in sorted((ROOT / 'config/profiles').glob('*.yaml')):
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('name') != path.stem:
                errors.append(f'{path.relative_to(ROOT)}: name no coincide')
    except ModuleNotFoundError:
        warnings.append('PyYAML no instalado; perfiles YAML no validados')

    design = (ROOT / 'docs/legacy/OPENBREC_RF_TECHNICAL_DESIGN.md').read_text(encoding='utf-8') if (ROOT/'docs/legacy/OPENBREC_RF_TECHNICAL_DESIGN.md').exists() else ''
    for term in ['RuView', 'Drop Pod', 'RF Quieting', 'drones']:
        if term.lower() not in design.lower():
            errors.append(f'diseño técnico no contiene sección requerida: {term}')

    bom = (ROOT / 'docs/legacy/BOM.md').read_text(encoding='utf-8') if (ROOT/'docs/legacy/BOM.md').exists() else ''
    for term in ['ESP32', 'Drone', 'RF Quieting', 'Uruguay']:
        if term.lower() not in bom.lower():
            errors.append(f'BOM no contiene categoría requerida: {term}')

    # Source-code safety scan. Documentation may name forbidden features to prohibit them.
    code_roots = ['apps', 'collectors', 'firmware', 'packages', 'scripts']
    offensive_patterns = [r'aireplay-ng', r'mdk4', r'deauth_attack', r'credential_harvest', r'evil_twin_start']
    for rel in code_roots:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if path.resolve() == Path(__file__).resolve():
                continue
            if not path.is_file() or path.suffix.lower() not in {'.py','.rs','.ts','.js','.sh','.c','.cpp','.h'}:
                continue
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
            for pattern in offensive_patterns:
                if re.search(pattern, text):
                    errors.append(f'función ofensiva prohibida en {path.relative_to(ROOT)}: {pattern}')

    if warnings:
        print('Advertencias:')
        for warning in warnings:
            print(f'- {warning}')
    if errors:
        print('Repositorio inválido:')
        for error in errors:
            print(f'- {error}')
        return 1
    print('OpenBREC RF v0.2: repositorio estructuralmente válido.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
