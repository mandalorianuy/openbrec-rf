# Review P0-07 — beacons, fusión y retención

- Fecha: 2026-07-17
- Task: P0-07
- SHA evaluado: `b5ddce10f10615e8247bdb2947a4943d55bf24a3`
- Implementación: rol `beacon-science-maintainer` (Codex)
- Review de privacidad y safety: rol `privacy-safety-reviewer`
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `beacon-replay`, `beacon-adversarial` y `retention-fault` pasan
sobre el mismo SHA, con `dirty: false`, errores y warnings vacíos.
`validate_receipt` confirmó SHA, checkout limpio, runtimes, lockfiles, inputs y
hash canónico del output. La suite completa pasa 115 tests y los artefactos se
conservan en `evidence/p0/p0-07/`.

## Boundary aceptado

- La campaña declara tres beacons, 12 observaciones acústicas feature-only,
  PIR y térmicas low-resolution, tres health records, cuatro placements y
  cuatro environment classes reales explícitamente omitidas.
- Cinco casos producen exactamente `single_modality_candidate`,
  `corroborated_candidate`, `sensor_artifact_likely`,
  `insufficient_coverage` y `unknown`. Diez órdenes generan una sola
  proyección; 12/12 observaciones quedan reconciliadas.
- Las modalidades de un beacon y las causas compartidas no se cuentan como
  evidencia independiente. Node move, baseline inválido, sensor ausente,
  relay loss, cobertura, OOD e incertidumbre quedan visibles.
- Doce casos hostiles cubren playback, animal, radio, herramientas, sol,
  equipo caliente, movimiento de rescatista, masking, node move, reloj, raw
  injection y causa correlacionada. Los 12 tienen disposición, con cero
  confirmación de presencia, ausencia, promoción raw o independencia falsa.
- Siete casos de captura cubren features-only, dual authorization, rechazo sin
  autorización, autorización expirada, break-glass, hold por expiry fault y
  borrado revisado. Cuatro materiales modelados tienen receipt; tres posibles
  life-safety se preservan y dos pasan a hold.
- No se conserva audio, waveform, grid térmico ni dato humano real. El fixture
  declara generación sintética, licencia CC0-1.0 y consentimiento no aplicable.

Hashes normativos: `beacon-replay`
`81af9595ddf2a5212026cbd0addf990357e0956f234e5a2baf0bf71131d6d8a5`,
`beacon-adversarial`
`b9c9a8677f1af5703a28af7b8aaf1e7b511c36ad274f1dcdb8368eeb8323548b` y
`retention-fault`
`814bd4d3e263fca03ebbe8b695433ee041e41f962c81bb3ed5eb5bdf0ef0e68b`.

## Evidencia negativa y límites

La campaña es sintética y acredita contratos, reglas y reconciliación, no
sensibilidad, precision, falsos positivos/hora, latencia, cobertura, acústica,
térmica, PIR, placement ni comportamiento físico. No hubo rubble, clima,
hardware, micrófono, sujetos, captura, cifrado, vault, retención o borrado real.

`CaptureAuthorizationEvent`, `ReviewTaskEvent` y `PreservationRecord` son
normativos. El estado auxiliar hold/deleted y su `disposition_receipt` son una
proyección de campaña, no un nuevo contrato canónico. P0-R014 exige decidir su
contrato o mapping en P0-09 antes de cualquier runtime P1a.

## Decisión

P0-07 cumple su Definition of Done simulada y se acepta como `7 / 9` (`77.8%`).
P0-08 queda elegible por dependencia, pero no se inicia en este closeout. La
aceptación no habilita sensing operativo, vigilancia, captura real, hardware,
campo ni claims de detección.
