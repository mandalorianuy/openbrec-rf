# Review P0-02 — replay energético, FSM y brownout lógico

- Fecha: 2026-07-17
- Task: P0-02
- SHA evaluado: `91c78a09200b592aa1c4b1bb6c416026213d1a1d`
- Implementación: rol `energy-maintainer` (Codex)
- Review funcional: rol `core-replay-maintainer` (revisión de replay separada)
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `energy-replay` y `determinism` pasan sobre el mismo SHA, con
`dirty: false`, errores y warnings vacíos. `validate_receipt` confirmó SHA,
checkout limpio, runtimes, lockfiles, inputs y hash canónico de output. Los
receipts y su manifiesto de aceptación se conservan en `evidence/p0/p0-02/`.

La suite enfocada cubre 14 casos y la suite completa cubre 81 tests. El fixture
normativo congela el hash energético
`ab3427bee8d71163cfdbcbe8c900426e63364a333f8ec45a67dd85915fc66833`;
diez ejecuciones alternan orden, `UTC`/`Pacific/Auckland` y
`C`/`C.UTF-8` sin producir un segundo hash.

## Boundary aceptado

- Tres EnergyDomains autónomos modelan cargas L0 life-safety, L1 críticas y
  cargas degradables L2/L3 con fuentes, storage y reservas declaradas.
- El presupuesto usa capacidad inferior, incertidumbre de SOC, DoD, temperatura,
  envejecimiento, eficiencia inferior y margen explícito. La generación auxiliar
  permanece separada y acredita cero Wh a la reserva storage-only.
- Un SOC desconocido no se normaliza a cero ni genera autonomía optimista:
  conserva capacidad declarada, energía restante y runtime como desconocidos.
- La FSM aplica hysteresis y muestra cada transición. SOS preserva L0/L1 y
  desplaza carga L3; estados críticos degradan cargas no vitales de forma visible.
- Source loss no elimina la reserva local simulada. Brownout/restart generan una
  nueva boot identity determinística y preservan secuencia, accepted-log y estado
  vital en el checkpoint lógico.
- Cada evento termina aceptado o reconciliado; el escenario reporta cero inputs
  no reconciliados y valida budgets/status contra los schemas addon normativos.
- El resultado declara `simulation_only` y prohíbe claims de 72 horas,
  funcionamiento indefinido o sostenibilidad física.

## Evidencia negativa y límites

El relay resulta `insufficient` bajo el modelo y el beacon resulta `unknown` por
SOC ausente; ambos resultados se preservan, no se ajustan para obtener éxito. No
se validaron cargas físicas, irradiancia, capacidad descargable, BMS, batería,
panel, generador, convertidor, power-cut real, storage durable, temperatura real
ni autonomía de 72 horas. Tampoco se validaron radio, TX o campo.

P0-R003 conserva la frontera entre simulación y energía física. P0-R010 queda
resuelto sólo para la porción energética y permanece planificado para P0-03–P0-07.
P0-R011 gobierna la diferencia entre el checkpoint lógico demostrado aquí y la
recuperación durable/integrada que requiere P0-08 y evidencia física P1a.

## Decisión

P0-02 cumple su Definition of Done simulada y se acepta como `2 / 9`. P0-03
queda elegible por dependencia, pero no se inicia en este closeout. Esta decisión
no habilita compra, hardware, TX, captura real, ensayo físico ni claim de campo.
