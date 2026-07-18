# OpenBREC Open Spec — plan spec-first

- Estado: activo
- Autoridad principal: Open Spec
- Versión objetivo: `1.0.0-draft.1`
- Progreso: `1 / 8` tasks aceptadas (`12.5%`)
- Carril físico: P1a opcional, `0 / 8`, no bloquea publicación

## Frontera normativa

OpenBREC publica contratos, perfiles de capacidad, alternativas, planos,
fixtures y criterios de aceptación sin exigir que el proyecto posea hardware.
P1a es un carril opcional de evidencia: sirve para elevar un claim específico a
`lab_validated` o `field_validated`, nunca para impedir que la spec avance.

Los candidatos comerciales son referencias sustituibles. Ningún fabricante,
SKU, firmware o bearer es obligatorio salvo que un perfil de implementación lo
declare explícitamente. La ausencia de evidence pack conserva `unverified`; no
invalida el contrato ni habilita claims físicos.

## Secuencia

- [x] **OS-01 — aceptada:** separar spec/publicación de validación física;
  publicar nueve perfiles abiertos, niveles de evidencia y gate normativo.
- [ ] **OS-02 — no iniciada:** arquitecturas de energía y solar por rol, cargas,
  almacenamiento, degradación y alternativas desacopladas.
- [ ] **OS-03 — no iniciada:** perfiles de transporte LoRaWAN, Meshtastic,
  MeshCore, Reticulum/RNode y carry bundle sin ganador universal.
- [ ] **OS-04 — no iniciada:** mensajería, estado, SOS y ubicación con contratos
  de interoperabilidad y seguridad de aplicación.
- [ ] **OS-05 — no iniciada:** beacons acústico, movimiento, térmico y extensiones
  con privacidad, abstención y datasets reutilizables.
- [ ] **OS-06 — no iniciada:** topologías recursivas, autonomía local, federación
  y operación de múltiples equipos/redes.
- [ ] **OS-07 — no iniciada:** planos, BOMs de referencia, adaptadores y guías de
  construcción/reutilización.
- [ ] **OS-08 — no iniciada:** conformance kit, matriz de decisión, publicación y
  proceso comunitario de evidence packs.

## Métrica

El numerador Open Spec cuenta tasks normativas aceptadas. No exige compra,
custodia ni ensayo físico. Los carriles se reportan siempre separados:

- Open Spec: `1 / 8` (`12.5%`).
- P1a física opcional: `0 / 8` (`0%`).

Un fixture sintético puede acreditar conformance o simulación, pero no
`lab_validated`. Un evidence pack físico puede elevar sólo la combinación exacta
que documenta; nunca convierte un candidato en requisito universal.

## Próxima task

OS-02 es la siguiente task gobernada. Este cierre no la inicia.
