# Review P0-05 — federación masiva y autonomía recursiva

- Fecha: 2026-07-17
- Task: P0-05
- SHA evaluado: `de188c2ab13e19cdfe3ed15842df19575c25badc`
- Implementación: rol `federation-maintainer` (Codex)
- Review determinismo/replay: rol `core-replay-maintainer` (revisión separada)
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `federation-scale` y `federation-reconciliation` pasan sobre el
mismo SHA, con `dirty: false`, errores y warnings vacíos. `validate_receipt`
confirmó SHA, checkout limpio, runtimes, lockfiles, inputs y hash canónico del
output. La suite completa pasa 100 tests y los artefactos se conservan en
`evidence/p0/p0-05/`.

## Boundary aceptado

- El generador `1.0.0`, seed `50060`, crea 50.000 sites únicos, 60
  ResponseCells, 5 OperationalAreas, 60 deployments y una raíz de incidente:
  50.126 entidades, sin sites omitidos y con distribución de 833–834 por celda.
- Los 50.126 topology events se materializan y firman en el hash de campaña.
  Las cinco formas jerárquicas se validan contra
  `FederationTopologyEvent`; esto prueba el generador y sus formas, no una
  validación normativa individual de cada evento materializado.
- Bajo pérdida simultánea de los dos hubs durante 86.400 segundos, las 60
  celdas ejecutan 240 operaciones críticas y las 50.126 entidades ejecutan su
  transición local sin dependencia de broker, identidad, CA, DNS, cloud o hub.
- Sesenta gateways outbound-only generan 180 resúmenes autorizados y 60 carry
  bundles. Hay cero listeners entrantes, payloads raw, claves privadas en hubs,
  violaciones de disclosure mínimo o inputs no reconciliados.
- La campaña de reconciliación consume 215 inputs: 10 duplicados idénticos,
  5 conflictos same-ID/different-bytes, 5 handoffs concurrentes y 5
  asignaciones de recurso concurrentes. Diez órdenes de replay producen una
  sola proyección; 15 conflictos quedan visibles y `human_pending`, sin
  overwrite, pérdida silenciosa ni last-write-wins.
- Nueve casos de hub hostil pasan por una política independiente del resultado
  esperado. Ninguno crea firma de celda, aceptación operacional, TX o
  disclosure de contenido local; todos terminan `rejected` o
  `review_quarantine` con evidencia enlazada.

Hashes normativos: `federation-scale`
`75373845865ca37ffca83748cd521ce0322705af3da096c89a98621befaf86c4` y
`federation-reconciliation`
`1980e711c94d33118101601e09d37888690bcfa64f2e6177b70dd9239c92333f`.

## Evidencia negativa y límites

La campaña es sintética y acredita correctness/determinismo del modelo, no
performance, capacidad de infraestructura, latencia, disponibilidad real ni
representatividad de todas las distribuciones de un incidente. No se ejecutaron
red, broker, TLS/mTLS, almacenamiento distribuido, HSM, claves operacionales,
hardware, RF, TX ni campo. Las claves Ed25519 derivadas son exclusivamente
vectores `simulated-only` y no pueden reutilizarse operacionalmente.

Los hubs todavía pueden retrasar, omitir o analizar metadata de resúmenes
permitidos. Los conflictos quedan intencionalmente pendientes de resolución
humana, por lo que las vistas locales pueden divergir. TM-005 y TM-010 siguen
High; P0-R006 controla el claim de correctness y conserva performance y
representatividad como trabajo planificado.

## Decisión

P0-05 cumple su Definition of Done simulada y se acepta como `5 / 9` (`55.6%`).
P0-06 queda elegible por dependencia, pero no se inicia en este closeout. Esta
decisión no habilita un hub central en el camino crítico, hardware, red real,
TX, campo ni un claim de escala operativa.
