# Review P0-06 — terminal offline y semántica humana

- Fecha: 2026-07-17
- Task: P0-06
- SHA evaluado: `d100f75a3cd3d18abffa15573799726c545b96fe`
- Implementación: rol `product-ux-reviewer` (Codex)
- Review de privacidad y safety: rol `privacy-safety-reviewer`
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `terminal-ux`, `ui-smoke` y `accessibility` pasan sobre el mismo
SHA, con `dirty: false`, errores y warnings vacíos. `validate_receipt` confirmó
SHA, checkout limpio, runtimes, lockfiles, inputs y hash canónico del output. La
suite completa pasa 108 tests y los artefactos se conservan en
`evidence/p0/p0-06/`.

## Boundary aceptado

- El escenario funciona sin Internet, hub ni servicio superior. Siete mensajes
  cubren texto, estado, SOS y ubicación, y sus 26 eventos append-only derivan
  `queued`, `sent`, `delivered`, `seen`, `accepted`, `cancelled` y `expired`.
- Los siete historiales se reconcilian, hay cero edición directa de estado y la
  cancelación conserva tres eventos y un receipt previo; no elimina el SOS.
- Partición, cobertura parcial, cola, gap, expiración, incertidumbre y cuatro
  capacidades ausentes permanecen visibles. La copy no promete entrega,
  arribo, rescate ni ausencia por silencio.
- Chromium construye y opera la terminal, encola texto y SOS, exige confirmación
  textual para SOS, cancela sin borrar historia y recarga offline desde el
  service worker. La cola persiste y no hay errores de consola.
- Dieciocho checks técnicos confirman teclado, labels textuales, objetivos de
  44 px, cues redundantes y reducción de movimiento. No hubo participantes
  humanos ni se emite claim de comprensión.

Hashes normativos: `terminal-ux`
`3efd1a53896ff30f7539564c61368b08c99703366994de70a25555519f065cfd` y
`accessibility`
`111fe45ae1c6ad2cd055587677c939f933344b1408eebb11b243b8104fc04bb9`.

## Evidencia negativa y límites

La terminal y el log de interacción son una proyección de laboratorio. No se
ejecutaron dispositivos físicos, red o radio real, GNSS, botón SOS, audio,
haptic, lectores de pantalla reales, usuarios, estrés ni campo. Los checks
automáticos no acreditan WCAG completo, comprensión, tiempo de decisión,
prevención humana de errores ni field readiness.

El diseño aprobado refería a un `TerminalInteractionEvent`, pero P0-01 no fijó
ese schema como contrato normativo. P0-06 no muta retroactivamente el baseline:
usa `HumanMessage`/`HumanMessageEvent` como frontera normativa y trata los
eventos genéricos de UI sólo como proyección determinística. P0-R013 exige una
decisión contractual en P0-09 antes de cualquier runtime P1a.

## Decisión

P0-06 cumple su Definition of Done simulada y se acepta como `6 / 9` (`66.7%`).
P0-07 queda elegible por dependencia, pero no se inicia en este closeout. La
aceptación no habilita uso operativo, hardware, TX, campo ni claims de
accesibilidad o comprensión humana.
