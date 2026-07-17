# OpenBREC RF — Delivery Board

- Autoridad de secuencia: este board
- Plan activo aprobado: `docs/superpowers/plans/2026-07-17-openbrec-m0-executable-plan.md`
- Estado real: M0 completo; M0-01–M0-06 cerrados sobre evidencia limpia
- Regla de avance: addons P0 sólo mediante plan explícito posterior; el cierre M0 no los inicia automáticamente

## Decisiones de gobernanza cerradas

- [x] Cuatro especificaciones hijas aprobadas.
- [x] Revisión multi-bearer aprobada el 2026-07-17.
- [x] Matriz conjunta de energía, comunicaciones y beacons aprobada el 2026-07-17.
- [x] Plan M0 aprobado para ejecución el 2026-07-17.

## Now — M0 Fundación

Los checks permanecen abiertos hasta producir la evidencia exigida por el plan. El orden es obligatorio.

- [x] `M0-01` / F-01: aceptar ADR-0001, catálogo core y registro inmutable de schemas legacy.
- [x] `M0-02` / F-01: implementar schemas, fixtures, modelos Pydantic/TypeScript y compatibilidad SemVer.
- [x] `M0-03` / F-02: crear API, worker y PWA mínimos; construir y arrancar `lab-sim` sin Internet.
- [x] `M0-04` / F-03–F-04: implementar accepted log, vault/quarantine/ledger y replay determinístico en dos niveles.
- [x] `M0-05` / F-05: simular seis nodos, dos tracks y tres zonas; mostrar capacidades, mapa, timeline y explicación.
- [x] `M0-06` / F-06: separar gates CI, generar receipts y demostrar el M0 exit completo.

### Evidencia M0-01

- ADR aceptado: `docs/adr/ADR-0001-core-scope-authority-and-red-lines.md`.
- Baseline legacy: seis schemas registrados por path, `$id`, versión declarada y SHA-256.
- Catálogo core: reservado y vacío hasta M0-02; no afirma contratos inexistentes.
- Gates mínimos: `bundle-structure` con alcance `structural_only` y `schema` con alcance `catalog_integrity_only`.
- Receipts: `evidence/m0/bundle-structure/receipt.json` y `evidence/m0/schema/*-catalog-receipt.json`, evaluados sobre `b10c2c587cec746a5fbfd91a81ce8bedebb173ea` con `dirty: false`.
- Residual M0-01 `M0-R001`: resuelto en M0-02 al fijar PyYAML; el nuevo receipt debe demostrar `warnings: []`.

Registro obligatorio: `docs/governance/M0_RESIDUAL_REGISTER.md`.

### Evidencia M0-02

- Catálogo core: 18 schemas Draft 2020-12, `$id` únicos y `contract_set_sha256` verificable.
- Fixtures: 36 válidos y 126 inválidos; validación normativa con formatos y resolución local de refs.
- Consumidores: 20 archivos Python/Pydantic estrictos y 21 TypeScript; 36 fixtures válidos compilados con TypeScript estricto.
- Compatibilidad: seis schemas legacy y 18 core congelados en `schemas/core/compatibility-baseline.json`.
- Receipts: `evidence/m0/{bundle-structure,schema,fixtures,schema-compat,contracts-gen}/`, evaluados sobre `eaa3fa8816e6d7bf48816655f4b574b13627ed72` con `dirty: false`.
- Residuales: todos registrados como `resolved`, `controlled` o `planned`; M0-R003/M0-R004/M0-R009 bloquean el cierre de M0-04 y M0-R006/M0-R007 el M0 exit.

### Evidencia M0-03

- Runtime: API FastAPI y worker asyncio revalidan `Observation` contra el schema normativo antes de publicar/procesar.
- PWA: React/TypeScript/Vite compila con lockfile offline; manifest y service worker forman un shell cacheable.
- Compose: Mosquitto y PostgreSQL sin puertos publicados, password PostgreSQL por secret, cinco healthchecks y red `lab-core` con `internal: true`.
- Smoke: observación válida procesada API → MQTT → worker; inválida rechazada con HTTP 422; shell/manifest/service worker disponibles; egress externo denegado.
- Receipts: `evidence/m0/{compose-build,offline-startup}/m0-03-receipt.json`, evaluados sobre `a2b446f8a5214ff2cfcb115f1a82573acc31d142` con `dirty: false` y `warnings: []`.
- Residuales M0-R011–M0-R015: uno `controlled` y cuatro `planned` con owners y stop conditions para M0-04/M0-05/M0-06.

### Evidencia M0-04

- Replay: adaptador y core separados, vínculo verificable con receipt upstream, JCS RFC 8785, SHA-256, orden normativo y reglas semánticas antes de derivar.
- Determinismo: diez corridas con orden invertido, `UTC`/`Pacific/Auckland` y `C`/`C.UTF-8` producen un único `result_sha256` (`bf4ad6c38a7ed8bdcd2e0f0106aec916f9d2a36b55bd104293206cc754a132fe`).
- Disposición: cuatro inputs sintéticos terminan uno por destino en accepted log, quarantine, vault y ledger, con `unreconciled: 0`.
- Life safety y privacidad: posible material vital se cifra y conserva antes de minimizar; break-glass, lectura, TTL y borrado requieren audit/review; secretos ajenos no persisten en claro.
- Seguridad: fixture/ciphertext alterado, JSON con claves duplicadas, schema desconocido, tardío, colisión y secuencia regresiva fallan cerrados; el replay funciona con red, reloj del host y aleatoriedad bloqueados.
- Receipts: siete `evidence/m0/*/m0-04-receipt.json`, todos sobre `803f4c196f50ab7d45156190428748996961d860`, `dirty: false`, sin errores ni warnings.
- Límite: SQLite acredita la semántica portable de laboratorio. PostgreSQL/runtime, custodia/rotación de master key y rollback/concurrencia permanecen planificados para M0-06 y bloquean el M0 exit; campo sigue `unverified`.

### Evidencia M0-05

- Campaña: fixture versionado de seis nodos, dos tracks y tres zonas, con pérdida, duplicado, partición, brownout lógico, reinicio y peer malicioso.
- Determinismo: diez variaciones de orden producen un único `result_sha256` (`87bf68033121549586c97341370c40ce647b800002584d71cbf87e1d632f844f`) y la proyección coincide con `8f8dec4f9372cc0e7d7249bbc0f31c5b68e54eabaf376d5d237aed9240d4c557`.
- Safety: los tres resultados permanecen en `abstained`; pérdida y capacidades ausentes sólo degradan cobertura/confianza; las seis unidades terminan en accepted log o quarantine con `unreconciled: 0`.
- PWA: mapa, matriz de capacidades, timeline e inspector separan observación, evidencia e inferencia; muestran fuentes, precisión, confianza, cobertura, explicación y capacidades ausentes.
- Browser/offline: Chromium selecciona zona, filtra tres inferencias y recarga desde service worker sin red ni errores de consola. El ingress web se limita a `127.0.0.1` y `offline-startup` mantiene egress core denegado.
- Receipts: `evidence/m0/{simulator,core-replay,determinism,ui-smoke,offline-startup}/m0-05-receipt.json`, todos sobre `1a805cca90521d48dd45026ee37f8ef0cfc5ff80`, `dirty: false`, sin errores ni warnings.
- Residual M0-R013: resuelto para `lab-sim`; Playwright/Chromium y la cadena final de dependencias siguen gobernados por M0-R007/M0-R012 para M0-06. Campo permanece `unverified`.

### Evidencia M0-06

- Runtime durable: API envuelve `Observation` en `DomainEvent`; el worker valida y ejecuta una transacción PostgreSQL antes de publicar `durably_processed`.
- PostgreSQL: cuatro destinos, migración, duplicado idempotente, rollback inyectado, restart y concurrencia pasan con `unreconciled: 0`; secretos rechazados no persisten en claro.
- Claves: perfil sustituible de laboratorio con key IDs, epoch monotónico, rotación, recovery, revocación, zeroization best-effort y rollback fail-closed; campo permanece `unverified`.
- Supply chain: cinco imágenes fijadas por digest, SBOM CycloneDX 1.7 con 124 componentes, cero licencias faltantes/denegadas, cero secretos y cero vulnerabilidades conocidas al 2026-07-17.
- CI: siete jobs independientes (`contracts`, `runtime`, `replay`, `privacy-security`, `simulation-ui`, `supply-chain`, `m0-exit`) y un receipt por gate.
- Receipts: 22 gates sobre `fb82384d08dbcc1618e080f542a5b0dbfaee9450`, todos `dirty: false`, exit code cero e integridad canónica aprobada; manifiesto en `evidence/m0/m0-exit-manifest.json`.
- Review: `docs/security/2026-07-17-m0-06-exit-review.md`; residuales M0-R006/R007/R012/R015/R017 resueltos y M0-R016 controlado para laboratorio.

## Gate de salida M0

- [x] Todos los servicios referenciados por Compose existen, construyen y arrancan offline.
- [x] Catálogo, metaschemas y fixtures pasan; modelos generados se regeneran sin diff.
- [x] Replay adapter/core produce hashes estables en diez ejecuciones y bajo variación de orden, locale y timezone.
- [x] Cada input termina exactamente en accepted log, quarantine, vault o ledger; no existe descarte silencioso.
- [x] La UI muestra incertidumbre, fuentes, sensores/capacidades ausentes, degradación y abstención.
- [x] Gates de estructura, schema, fixtures, compatibilidad, generación, Compose, offline, replay, privacidad, seguridad y supply chain producen receipts verificables.
- [x] Threat model y safety/privacy review reflejan la implementación M0.

## Eligible para planificación — Addons P0

La matriz aprobada conserva todas las opciones y resultados para revisión. El gate M0 está cerrado, pero ninguno de estos frentes se inicia sin seleccionar alcance P0, criterios de aceptación y owners:

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
