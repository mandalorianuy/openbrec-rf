# OpenBREC RF — Delivery Board

- Autoridad de secuencia: este board
- Plan activo propuesto: `docs/superpowers/plans/2026-07-17-openbrec-m0-executable-plan.md`
- Estado real: bundle de diseño estructuralmente válido; M0 no implementado
- Regla de avance: una sola task M0 a la vez, con gate y receipt; no iniciar addons antes del M0 exit

## Decisiones de gobernanza cerradas

- [x] Cuatro especificaciones hijas aprobadas.
- [x] Revisión multi-bearer aprobada el 2026-07-17.
- [x] Matriz conjunta de energía, comunicaciones y beacons aprobada el 2026-07-17.
- [ ] Plan M0 aprobado para ejecución.

## Now — M0 Fundación

Los checks permanecen abiertos hasta producir la evidencia exigida por el plan. El orden es obligatorio.

- [ ] `M0-01` / F-01: aceptar ADR-0001, catálogo core y registro inmutable de schemas legacy.
- [ ] `M0-02` / F-01: implementar schemas, fixtures, modelos Pydantic/TypeScript y compatibilidad SemVer.
- [ ] `M0-03` / F-02: crear API, worker y PWA mínimos; construir y arrancar `lab-sim` sin Internet.
- [ ] `M0-04` / F-03–F-04: implementar accepted log, vault/quarantine/ledger y replay determinístico en dos niveles.
- [ ] `M0-05` / F-05: simular seis nodos, dos tracks y tres zonas; mostrar capacidades, mapa, timeline y explicación.
- [ ] `M0-06` / F-06: separar gates CI, generar receipts y demostrar el M0 exit completo.

## Gate de salida M0

- [ ] Todos los servicios referenciados por Compose existen, construyen y arrancan offline.
- [ ] Catálogo, metaschemas y fixtures pasan; modelos generados se regeneran sin diff.
- [ ] Replay adapter/core produce hashes estables en diez ejecuciones y bajo variación de orden, locale y timezone.
- [ ] Cada input termina exactamente en accepted log, quarantine, vault o ledger; no existe descarte silencioso.
- [ ] La UI muestra incertidumbre, fuentes, sensores/capacidades ausentes, degradación y abstención.
- [ ] Gates de estructura, schema, fixtures, compatibilidad, generación, Compose, offline, replay, privacidad, seguridad y SBOM producen receipts verificables.
- [ ] Threat model y safety/privacy review reflejan la implementación M0.

## Blocked — Addons P0

La matriz aprobada conserva todas las opciones y resultados para revisión, pero ninguno de estos frentes es ejecutable hasta cerrar y aprobar el gate M0:

- Energía, storage, solar, generadores y autonomía de 72 horas.
- LoRaWAN, Meshtastic, MeshCore, Reticulum/RNode y selección multi-bearer.
- Mensajería humana, estado, SOS, ubicación, federación y operación masiva multi-equipo.
- Beacons acústicos, PIR/movimiento, térmicos y otras modalidades.
- Compra de hardware, TX radiado, banco P1 y despliegue de campo.

Autoridades: `docs/decision-matrices/2026-07-17-offgrid-addons-decision-matrix.md` y `docs/research/2026-07-17-offgrid-communications-state-of-art.md`.

## After M0 — roadmap existente sujeto a replan

### M1 RF pasivo

- [ ] Collector Kismet desde fixture sanitizado.
- [ ] Collector BLE sintético y luego BlueZ/nRF52840.
- [ ] HMAC rotativo por incidente.
- [ ] Métricas RSSI/sector y estado de radio/canal.
- [ ] Gate que demuestra que no se persisten payloads.

### M2 CSI y campo

- [ ] Firmware ESP32-S3 con telemetría de salud y CSI.
- [ ] Registro de radio, cable, antena, azimut, altura y polarización.
- [ ] Baseline/adaptive change detection sin ML.
- [ ] Cajas, energía, tripods y procedimientos de calibración.
- [ ] Banco de escombros instrumentado y protocolo ciego.

### Experimental

- [ ] SDR receive-only.
- [ ] 802.15.4.
- [ ] BFI/Wi-BFI con clase unknown y OOD.
- [ ] UWB para rescatistas/nodos.
- [ ] mmWave, acústica y sísmica como plugins.

### M7 — RuView adapter

- [ ] ADR-018 UDP decoder and replay fixture.
- [ ] JSONL/RVF compatibility gate.
- [ ] Sidecar model adapter with OOD.

### M8 — Drone-deployed sensing

- [ ] Drop Pod prototype and FSM.
- [ ] MAVLink read-only bridge.
- [ ] Human-confirmed release simulator.
- [ ] Drone EMI baseline protocol.

### M9 — RF Quieting

- [ ] Curtain sample characterization.
- [ ] IsolationProfile ingest/UI.
- [ ] Independent communications safety gate.

## Gates permanentes

- [ ] Offline startup.
- [ ] Deterministic replay.
- [ ] Schema compatibility.
- [ ] No payload retention fuera de preservación life-safety autorizada.
- [ ] No offensive RF features.
- [ ] Node-loss degradation.
- [ ] Explainability and abstention.
