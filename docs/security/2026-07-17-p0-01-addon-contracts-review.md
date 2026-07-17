# Review P0-01 — contratos addon y fixtures normativos

- Fecha: 2026-07-17
- Task: P0-01
- SHA evaluado: `9f741fd204c5abb89c1ca1b457b9d4cc9c910f24`
- Implementación: rol `contract-maintainer` (Codex)
- Review de boundary: rol `privacy-safety-reviewer` (revisión funcional separada)
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `addon-contracts`, `addon-fixtures`, `contracts-gen --check` y
`schema-compat` pasan sobre el mismo SHA, con `dirty: false`, errores y warnings
vacíos. La suite completa pasa 67 tests. Los receipts se conservan en
`evidence/p0/p0-01/` y su integridad fue comprobada con `validate_receipt` contra
el SHA evaluado y checkout limpio.

## Boundary aceptado

- Los 18 schemas addon están cerrados, versionados y catalogados como
  `experimental`; la compatibilidad queda congelada por bytes.
- Los payloads se integran bajo el `DomainEvent` core, que conserva provenance,
  handling e idempotencia; no se crea una autoridad de eventos paralela.
- `BeaconObservation` especializa `Observation` y limita las métricas a candidatos
  acústicos, PIR o térmicos. No admite ausencia, identidad ni presencia confirmada.
- `HumanMessageEvent` es append-only y rechaza un campo `state`; un ACK o estado
  del bearer no puede convertirse en estado operativo por contrato.
- `BearerCapability` permanece `experimental`, `unverified` o `unavailable`; P0-01
  no puede declarar un bearer `supported`.
- Los mensajes sólo contienen payload protegido y referencias criptográficas;
  P0-01 no implementa todavía autenticidad, AEAD, reducers ni transporte.

## Limitaciones y residuales

P0-R009 gobierna la diferencia expresiva de consumidores generados: JSON Schema
sigue siendo la autoridad. P0-R010 evita confundir contrato con runtime y asigna
la implementación a P0-02–P0-07. Los residuales anteriores sobre hardware,
regulación, energía real, datos beacon, custodia y bearers continúan vigentes.

No se validó radio física, TX, energía real, 72 horas, captura, usabilidad humana,
criptografía operativa ni desempeño de Meshtastic/MeshCore/Reticulum. Ninguno de
esos puntos cuenta como progreso de P0-01 ni queda habilitado por este review.

## Decisión

P0-01 cumple su Definition of Done contractual y se acepta como `1 / 9`. P0-02
queda elegible por dependencia, pero no se inicia en este closeout.
