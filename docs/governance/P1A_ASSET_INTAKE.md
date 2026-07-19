# Preflight de evidencia física P1a-01

Este preflight convierte el bloqueo de P1a-01 en un checklist accionable por
categoría. Es informativo: **no acepta P1a-01**, no autoriza compras, préstamos,
inspecciones ni uso de hardware, y mantiene el avance físico en `0 / 8`.

## Consultar el estado

```bash
uv run --offline python -m openbrec.verify p1a-assets-intake \
  --evidence-dir evidence/p1a/p1a-01 \
  --authorization-schema schemas/p1a/asset-authorization-register.schema.json
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

El registro completo está gobernado por
`schemas/p1a/asset-authorization-register.schema.json`. El contrato usa
`additionalProperties: false`, correlaciona categoría/candidato y exige
evidencia específica para `purchase` o `loan`; un campo implícito o desconocido
invalida la submission.

```bash
uv run --offline python -m openbrec.verify p1a-assets \
  --evidence-dir evidence/p1a/p1a-01 \
  --authorization-schema schemas/p1a/asset-authorization-register.schema.json
```

## Evidencia que debe aportar el responsable físico

Por cada categoría se requiere un registro de autorización y un capability
manifest de una unidad real. Deben incluir identidad exacta, dueño/autorizante,
custodio, hash de evidencia del serial, inspección física y pin de firmware
cuando corresponda. No se aceptan placeholders, seriales publicados en claro,
datos sintéticos ni declaraciones de una familia comercial como sustituto de
una unidad inspeccionada. Esos identificadores no pueden reutilizarse entre
categorías: aplica tanto a `asset_id` como a `serial_evidence_sha256`; el intake
invalida todas las submissions implicadas y el gate 9/9 rechaza el conjunto.
También se exige un `authorization_id` y evidencia de autorización distintos por
asset. El `custody.receipt_sha256` del manifest debe coincidir con la evidencia
de autorización aplicable (`evidence_sha256`, `loan_receipt_sha256` o
`purchase_receipt_sha256` según el método), y esos receipts no pueden
reutilizarse entre categorías. Los receipts reportan por separado IDs/evidencia
duplicados, receipts de custodia duplicados y bindings incompatibles.

La cronología declarada también falla cerrada: `authorized_at` debe ser anterior
o igual a `physical_inspection.inspected_at`, y cada fuente de advisory debe
haber sido recuperada a más tardar en `reviewed_at`. Los receipts exponen
`authorization_inspection_order_errors` y `advisory_source_order_errors`; estos
controles prueban orden interno, no autenticidad ni fecha real.

## Firmware y advisories

El contrato vigente es `manifest_version: 2.0.0` en
`schemas/p1a/capability-manifest.schema.json`. Para todo asset programable exige
un `advisory_review` cerrado con reviewer, fecha, fuentes recuperables, hashes de
evidencia, disposición y razón. La disposición puede ser `no_known_blocker` o
`block_firmware_use`; esta última permanece visible en summary/receipt y nunca
autoriza flashing, testing ni P1a-02.

La versión anterior queda preservada en
`schemas/p1a/capability-manifest-1.0.0.schema.json` sólo para review y migración;
no satisface el gate vigente. Este control no ejecuta una revisión real ni
afirma que el firmware sea seguro: la persona responsable debe aportar la
evidencia externa al seleccionar la unidad y el pin exactos.

La solicitud fuente es
`docs/governance/p1a-01-asset-authorization-request.json`; el contrato del
manifest es `schemas/p1a/capability-manifest.schema.json`. P1a-02 permanece sin
iniciar hasta que el gate de aceptación de P1a-01 pase con 9/9 categorías.
