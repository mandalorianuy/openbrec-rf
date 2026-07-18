# Review P0-08 — campaña integrada de fallos

- Fecha: 2026-07-17
- Task: P0-08
- SHA evaluado: `6eb7bcbbd9e4fdde3d63437e097d385577fd422c`
- Implementación: rol `core-replay-maintainer` (Codex)
- Review: rol `release-reviewer`
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

El receipt de `p0-integrated` pasa sobre el SHA indicado con `dirty: false`,
errores y warnings vacíos. `validate_receipt` confirmó SHA, checkout limpio,
runtimes, lockfiles, ocho inputs y hash canónico del output. El gate recompone
13 gates de P0-02 a P0-07; no confía en receipts históricos como sustituto. El
job integrado instala explícitamente el runtime browser requerido por el gate
de accesibilidad; una regresión impide volver a omitirlo.

La regresión completa pasó 122 tests en procesos aislados por módulo. La
invocación monolítica no produjo resumen al exceder la ventana del executor y no
se cuenta como evidencia. Los cuatro comandos objetivo `p0-integrated`,
`determinism --runs 10`, `privacy` y `security` pasaron independientemente.

## Boundary aceptado

- La campaña fija seis escenarios componentes, tres celdas con Meshtastic,
  MeshCore y Reticulum, carry bundle por celda y partición de 86.400 segundos.
- Once fallos únicos cubren partition, node/relay/source/hub loss, brownout,
  forged distress, replay, terminal robado, spoofed sensor y hub malicioso.
  Los 11 tienen disposición visible y quedan reconciliados.
- Los 13 gates componentes pasan. Se proyectan offline energía, comunicación,
  mensajes, beacon y review; seis límites componentes permanecen visibles.
- Las tres celdas continúan localmente sin superior; los tres carry bundles se
  reconcilian. Energía, radio y sensing degradan explícitamente.
- Hay cero false acceptance, false confirmation, false absence, silent success,
  prioridad SOS invertida, pérdida de accepted log o pérdida de estado vital.
  Cuatro distress no verificables se preservan para review.
- Diez variaciones de orden producen una única proyección. El hash congelado es
  `54c52e8383cd4ed4cc57604c6cb74c85425b80e333e9eb5184f445edf5351441`.

## Evidencia negativa y límites

La composición ejecuta funciones determinísticas en un proceso. No desplegó
servicios addon distribuidos, no midió contención de CPU/memoria/espectro, no
ejecutó red, radio, hardware, terminal humano, sensores, storage ni power-cut
físico. P0-R015 conserva ese límite y P0-R011 mantiene la porción física.

Los resultados negativos no se descartan: fallos de bearer, budgets
`insufficient`/`unknown`, gaps de sensing, conflictos pendientes y material en
hold continúan dentro de las proyecciones fuente y sus receipts P0-02–P0-07.

## Decisión

P0-08 cumple su Definition of Done simulada y se acepta como `8 / 9` (`88.9%`).
P0-09 queda elegible por dependencia, pero no se inicia en este closeout. La
aceptación no habilita P1a, compras, TX, captura, campo ni claims físicos.
