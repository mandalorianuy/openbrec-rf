# Preflight de evidencia física P1a-01

Este preflight convierte el bloqueo de P1a-01 en un checklist accionable por
categoría. Es informativo: **no acepta P1a-01**, no autoriza compras, préstamos,
inspecciones ni uso de hardware, y mantiene el avance físico en `0 / 8`.

## Consultar el estado

```bash
uv run --offline python -m openbrec.verify p1a-assets-intake \
  --evidence-dir evidence/p1a/p1a-01
```

La salida enumera las nueve categorías gobernadas y, para cada una:

- `candidate_id` esperado;
- presencia de autorización y manifest;
- evidencia externa faltante;
- errores de schema, identidad, custodia, inspección, firmware y correlación;
- estado `awaiting_external_evidence`, `invalid_submission` o
  `validated_for_acceptance_gate`.

El preflight valida incrementalmente cada par autorización/manifest. Una
categoría `invalid_submission` hace fallar el comando; una categoría
`validated_for_acceptance_gate` superó el control individual, pero no promueve
soporte ni acepta la task. El único gate de aceptación 9/9 sigue siendo:

```bash
uv run --offline python -m openbrec.verify p1a-assets \
  --evidence-dir evidence/p1a/p1a-01
```

## Evidencia que debe aportar el responsable físico

Por cada categoría se requiere un registro de autorización y un capability
manifest de una unidad real. Deben incluir identidad exacta, dueño/autorizante,
custodio, hash de evidencia del serial, inspección física y pin de firmware
cuando corresponda. No se aceptan placeholders, seriales publicados en claro,
datos sintéticos ni declaraciones de una familia comercial como sustituto de
una unidad inspeccionada.

La solicitud fuente es
`docs/governance/p1a-01-asset-authorization-request.json`; el contrato del
manifest es `schemas/p1a/capability-manifest.schema.json`. P1a-02 permanece sin
iniciar hasta que el gate de aceptación de P1a-01 pase con 9/9 categorías.
