# OpenBREC Open Spec — plan spec-first

- Estado: activo
- Autoridad principal: Open Spec
- Versión objetivo: `1.0.0-draft.1`
- Progreso: `6 / 8` tasks aceptadas (`75.0%`)
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
- [x] **OS-02 — aceptada:** cuatro arquitecturas abiertas de energía por
  componente, sitio compartido, híbrida y logística/reemplazo; nueve mappings de
  rol, ocho source adapters, cargas L0–L3, degradación y claims acotados. Solar es
  opcional y `sustainable_under_profile` nunca significa operación perpetua.
- [x] **OS-03 — aceptada:** cinco perfiles reemplazables para LoRaWAN privado,
  Meshtastic, MeshCore, Reticulum/RNode y carry bundle sin ganador universal;
  overlay OpenBREC independiente, selección por misión/ruta y modos regulatorios
  `receive_only`, `conducted_only`, `jurisdiction_validated` y
  `emergency_assumed_risk`. El último es una decisión vital acotada, auditable,
  expirable y con kill switch; no constituye autorización legal.
- [x] **OS-04 — aceptada:** texto breve, estado, SOS y ubicación con contenidos
  cerrados, seguridad de aplicación por encima del bearer y lifecycle SOS
  append-only. Recepción técnica, lectura humana y aceptación operativa son
  estados separados; ninguna garantiza rescate. `unverified_distress` se
  preserva en vault/quarantine para review sin elevarlo a autenticado.
- [x] **OS-05 — aceptada:** perfiles abiertos acústico, movimiento y térmico con
  mínimo de una modalidad y referencia tri-modal opcional; extensiones bajo
  namespace/schema/reviews propios, abstención, privacidad, datasets con
  provenance y resultados negativos. Ningún indicio confirma presencia o ausencia.
- [x] **OS-06 — aceptada:** jerarquía recursiva
  `IncidentFederation → OperationalArea → ResponseCell → Deployment → Site`,
  con autonomía local en cada nivel, redes aisladas por celda, peering explícito,
  hubs opcionales no autoritativos y reconciliación append-only determinística.
  La simulación de 50.000 sitios prueba corrección, no capacidad ni readiness.
- [ ] **OS-07 — no iniciada:** planos, BOMs de referencia, adaptadores y guías de
  construcción/reutilización.
- [ ] **OS-08 — no iniciada:** conformance kit, matriz de decisión, publicación y
  proceso comunitario de evidence packs.

## Métrica

El numerador Open Spec cuenta tasks normativas aceptadas. No exige compra,
custodia ni ensayo físico. Los carriles se reportan siempre separados:

- Open Spec: `6 / 8` (`75.0%`).
- P1a física opcional: `0 / 8` (`0%`).

Un fixture sintético puede acreditar conformance o simulación, pero no
`lab_validated`. Un evidence pack físico puede elevar sólo la combinación exacta
que documenta; nunca convierte un candidato en requisito universal.

## Próxima task

OS-07 es la siguiente task gobernada. Este cierre no la inicia.
