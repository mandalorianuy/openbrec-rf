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
- estado `awaiting_external_evidence` o `submitted_for_gate_review`.

`submitted_for_gate_review` sólo indica que existen ambos archivos. No valida
su contenido ni promueve soporte. El único gate de aceptación sigue siendo:

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
