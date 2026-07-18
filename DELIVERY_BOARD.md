# OpenBREC RF — Delivery Board

- Autoridad de secuencia: este board
- Plan activo aprobado: `docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md`
- Último plan completado: `docs/superpowers/plans/2026-07-17-openbrec-p0-simulated-addons-plan.md`
- Baseline cerrado: `docs/superpowers/plans/2026-07-17-openbrec-m0-executable-plan.md`
- Estado real: M0/P0 completos; Open Spec `8 / 8` (`100%`); P1a física `0 / 8` (`0%`)
- Regla de avance: Open Spec está cerrada; P1a-01 es opcional y permanece `blocked_external_evidence`

## Decisiones de gobernanza cerradas

- [x] Cuatro especificaciones hijas aprobadas.
- [x] Revisión multi-bearer aprobada el 2026-07-17.
- [x] Matriz conjunta de energía, comunicaciones y beacons aprobada el 2026-07-17.
- [x] Plan M0 aprobado para ejecución el 2026-07-17.
- [x] Exit M0 aceptado y mergeado el 2026-07-17.
- [x] Plan P0 completamente simulado aprobado el 2026-07-17.
- [x] Plan P1a de banco/conducted y política fail-closed aprobados el 2026-07-17.
- [x] OS-01 corrige la autoridad a spec-first y separa publicación de evidencia física el 2026-07-18.
- [x] OS-02 publica energía/solar abierta, reemplazable y gobernada por claims acotados el 2026-07-18.
- [x] OS-03 publica selección multi-bearer abierta, overlay común y riesgo regulatorio acotado el 2026-07-18.
- [x] OS-04 publica contenido humano interoperable, lifecycle SOS y preservación de distress el 2026-07-18.
- [x] OS-05 publica beacons abiertos, extensiones gobernadas, abstención y datasets reutilizables el 2026-07-18.

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
- Receipts: 22 gates sobre `2648f38bbddac755f2064e59148bb6fb26bcffd0`, todos `dirty: false`, exit code cero e integridad canónica aprobada; manifiesto en `evidence/m0/m0-exit-manifest.json`.
- Review: `docs/security/2026-07-17-m0-06-exit-review.md`; residuales M0-R006/R007/R012/R015/R017 resueltos y M0-R016 controlado para laboratorio.

## Gate de salida M0

- [x] Todos los servicios referenciados por Compose existen, construyen y arrancan offline.
- [x] Catálogo, metaschemas y fixtures pasan; modelos generados se regeneran sin diff.
- [x] Replay adapter/core produce hashes estables en diez ejecuciones y bajo variación de orden, locale y timezone.
- [x] Cada input termina exactamente en accepted log, quarantine, vault o ledger; no existe descarte silencioso.
- [x] La UI muestra incertidumbre, fuentes, sensores/capacidades ausentes, degradación y abstención.
- [x] Gates de estructura, schema, fixtures, compatibilidad, generación, Compose, offline, replay, privacidad, seguridad y supply chain producen receipts verificables.
- [x] Threat model y safety/privacy review reflejan la implementación M0.

## Now — P0 addons completamente simulados

Progreso de aceptación: `9 / 9` (`100%`). Una task marcada sólo cambia después de
su implementación, validación, review y receipt; planificación o inicio no suman.

- [x] `P0-01`: contratos addon, catálogo, fixtures y modelos generados.
- [x] `P0-02`: EnergyDomain/FSM/budget y brownout replay.
- [x] `P0-03`: HumanMessage protegido, SOS append-only y transporte hostil.
- [x] `P0-04`: comparación Meshtastic/MeshCore/Reticulum por TransportProfile.
- [x] `P0-05`: federación 50k sites/60 cells/5 areas/2 hubs.
- [x] `P0-06`: terminal offline para texto, estado, SOS y ubicación.
- [x] `P0-07`: beacons acústico/PIR/térmico, fusión, review y retención.
- [x] `P0-08`: campaña integrada con fallos y adversarios.
- [x] `P0-09`: exit P0, support status por perfil y decisión P1a.

### Evidencia P0-01

- Contratos: 18 schemas addon Draft 2020-12 cerrados, catálogo experimental y
  baseline byte-inmutable con contract set
  `fdab8dcc94eeb6c63e40a206d60f07fe931e7d0d3da125dab76054c0ea22067b`.
- Fixtures: 36 válidos y 126 inválidos; Pydantic v2 y TypeScript estricto
  comprueban los ejemplos válidos y la regeneración deja diff vacío.
- Safety: estado operativo no se acepta desde transporte, bearer no puede elevarse
  a `supported`, y beacon no admite `person_present`, ausencia ni identidad.
- Validación: 67 tests pasan; cuatro receipts P0-01 pasan sobre
  `9f741fd204c5abb89c1ca1b457b9d4cc9c910f24`, todos con `dirty: false`.
- Review: `docs/security/2026-07-17-p0-01-addon-contracts-review.md`.
- Residuales: P0-R009 controlado permanentemente y P0-R010 planificado por las
  tasks consumidoras; ninguno habilita runtime, hardware, TX o campo.

### Evidencia P0-02

- Replay: tres dominios energéticos autónomos simulan cargas L0–L3, pérdidas,
  incertidumbre, source loss, SOS, brownout, restart y SOC `unknown`.
- Presupuesto: capacidad utilizable, carga crítica superior, reservas y margen
  storage-only permanecen separados; la generación auxiliar se declara pero no
  se acredita a la reserva. SOC desconocido conserva resultado `unknown`.
- FSM: hysteresis visible, degradación de cargas L2/L3 y reserva L0/L1; el modelo
  de brownout preserva secuencia, accepted-log y estado vital en supervivencia.
- Determinismo: diez corridas con orden, locale y timezone alternados producen
  un solo hash energético
  `ab3427bee8d71163cfdbcbe8c900426e63364a333f8ec45a67dd85915fc66833`;
  el hash core permanece
  `bf4ad6c38a7ed8bdcd2e0f0106aec916f9d2a36b55bd104293206cc754a132fe`.
- Receipts: `evidence/p0/p0-02/{energy-replay,determinism}/`, evaluados sobre
  `91c78a09200b592aa1c4b1bb6c416026213d1a1d`, con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-02-energy-replay-review.md`.
- Residuales: P0-R003 continúa controlando claims físicos; P0-R010 queda resuelto
  para energía y sigue planificado para P0-03–P0-07; P0-R011 gobierna recovery
  durable y power-cut real.

### Evidencia P0-03

- Seguridad de aplicación: Ed25519 y AES-256-GCM sobre JCS, AAD ligada a
  incidente/celda/actor/dispositivo/destino/tipo/secuencia/TTL y vectores
  sintéticos reproducibles; cero autenticaciones falsas.
- Identidad offline: bindings por incidente, enrolamiento local con fingerprint,
  derechos mínimos, revocación cacheada y rekey grupal epoch 2 sin red. Clave
  anterior, default/shared secret, rol insuficiente, replay, nonce reuse y
  sequence rollback fallan cerrados con eventos de seguridad.
- SOS: seis eventos append-only derivan estado técnico `gateway_received` y
  estado operativo `accepted` por separado; un transporte no puede crear
  `operator.accepted` y el intento se preserva como distress no verificado.
- Transporte hostil: un mensaje lógico llega por Meshtastic, MeshCore y
  carry-bundle con tres receipts; dos caminos quedan deduplicados, loops/raw
  bridge/payload alterado se rechazan y la decisión de política valida schema.
- Hashes normativos: `human-message-security`
  `1873e747c33026e186ff0a32dd8c66c97f4f7213cb69d875d2a3162ef05cda64`,
  `sos-state-replay`
  `7fcbea861218c18b03811c5a3b58a2be6963633e13deb036bc295ab3cdb0b839`
  y `transport-policy`
  `002488b7837dedd562abeda05e6e5314aec5878b6b958680939221e1e5a4cf95`.
- Receipts: `evidence/p0/p0-03/`, evaluados sobre
  `c6a3dc15ccf045dac60148080870a5f44eb2027c` con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-03-secure-messaging-review.md`.
- Residuales: P0-R001/P0-R008 siguen gobernando adapters reales; P0-R007
  conserva custodia física; P0-R010 queda resuelto para P0-03 y P0-R012 impide
  reutilizar claves sintéticas fuera del replay.

### Evidencia P0-04

- Modelos: Meshtastic `v2.7.26.54e0d8d`, MeshCore
  `companion-v1.16.0` y Reticulum `1.3.8` quedan fijados por commit, fuente,
  licencia, fecha y limitaciones; todos continúan `unverified`.
- Comparación: 27 corridas cubren tres perfiles y escalas 12/40/100 con SOS,
  estado, ubicación y 23 eventos de seis clases de falla. Los tres modelos consumen el mismo
  `OpenBRECEnvelope`; no se puentean frames ni floods nativos.
- Denominador: 4.104 mensajes, 3.138 entregados modelados y 966 fallidos
  modelados; cero omisiones, cero prioridad SOS invertida y cero ganador global.
- Métricas: PDR, p50/p95/p99, airtime, retries, duplicates, convergencia,
  energía modelada y metadata disclosure quedan limitadas a modelo/versión,
  perfil y escala; no son benchmarks ni claims físicos.
- Adversarios: 11/11 casos tienen disposición explícita, cero raw bridges, cero
  pérdida silenciosa y cero aceptación operacional falsa.
- Receipts: `evidence/p0/p0-04/`, evaluados sobre
  `7e01320ec9520316add7a7d2915fbb1426106bc1` con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-04-transport-comparison-review.md`.
- Residuales: P0-R001 queda controlado para simulación y planificado para P1a;
  P0-R008 queda controlado por pins con reapertura obligatoria; P0-R010 queda
  resuelto para P0-04 y sigue planificado para P0-05–P0-07.

### Evidencia P0-05

- Escala: generador `1.0.0`/seed `50060` materializa 50.000 sites, 60 cells,
  5 areas, 60 deployments y una raíz; 50.126 topology events quedan firmados y
  las cinco formas se validan contra el schema normativo.
- Autonomía: pérdida de ambos hubs durante 86.400 segundos deja 60/60 celdas y
  50.126/50.126 entidades operando localmente; 240/240 operaciones críticas se
  ejecutan sin dependencias centrales.
- Federación: 60 gateways outbound-only, 180 resúmenes autorizados y 60 carry
  bundles; cero listeners, raw payloads, claves de celda en hubs, disclosure
  excesivo, aceptación falsa o inputs no reconciliados.
- Reconciliación: 215 inputs en 10 órdenes producen una proyección; 10
  duplicados, 5 conflictos de integridad, 5 handoffs y 5 asignaciones quedan
  contabilizados, con 15 resoluciones humanas pendientes y cero overwrite,
  pérdida silenciosa o last-write-wins.
- Hub hostil: 9/9 casos tienen disposición calculada; cero firmas/aceptaciones
  falsas, órdenes TX ejecutadas o disclosure local.
- Receipts: `evidence/p0/p0-05/`, evaluados sobre
  `de188c2ab13e19cdfe3ed15842df19575c25badc` con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-05-federation-autonomy-review.md`.
- Residuales: P0-R006 queda controlado para correctness simulado y planificado
  para performance/representatividad; P0-R010 se resuelve para P0-05 y sigue
  planificado para P0-06–P0-07. TM-005/TM-010 permanecen High.

### Evidencia P0-06

- Terminal: cuatro flujos offline y siete historiales derivados de 26 eventos
  append-only, con cero edición directa de estado y `unreconciled: 0`.
- Safety: aceptación no promete arribo/rescate, silencio no implica ausencia y
  la cancelación conserva SOS, tres eventos y un receipt previo.
- Degradación visible: partición, cobertura parcial, cola/gap, expiración,
  incertidumbre y cuatro capacidades ausentes quedan expuestas.
- Browser: Chromium encola texto/SOS, exige confirmación textual para SOS,
  cancela sin borrar historia y recarga offline con cola persistente; cero
  errores de consola.
- Accesibilidad técnica: 18/18 checks pasan para teclado, labels textuales,
  objetivos de 44 px, cues redundantes y reduced motion; cero participantes y
  ningún claim de comprensión humana.
- Receipts: `evidence/p0/p0-06/`, evaluados sobre
  `d100f75a3cd3d18abffa15573799726c545b96fe` con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-06-offline-terminal-review.md`.
- Residuales: P0-R005 controla comprensión/accesibilidad humana; P0-R010 queda
  resuelto para P0-06 y planificado sólo para P0-07; P0-R013 gobierna la falta
  de contrato normativo para el log genérico de interacción. TM-013 sigue High.

### Evidencia P0-07

- Campaña: tres beacons, 12 observaciones, tres health records, cuatro
  placements y acoustic features/PIR/thermal low-resolution bajo provenance
  sintética CC0-1.0; cuatro environment classes reales quedan omitidas visibles.
- Fusión: cinco casos cubren single, corroborated, artifact, insufficient y
  unknown; diez órdenes producen una sola proyección, 12/12 inputs se
  reconcilian y causas/modalidades correlacionadas no cuentan independientes.
- Adversarios: 12/12 casos de sonido, calor, movimiento, masking, node move,
  reloj, raw injection y causa común tienen disposición explícita; cero
  confirmación de presencia, ausencia, promoción raw o independencia falsa.
- Retención: 7/7 casos reconciliados; cuatro materiales modelados trazan cuatro
  receipts, tres life-safety se preservan y dos pasan a hold. Cero captura no
  autorizada, material sin cifrado, over-cap o borrado sin review/receipt.
- Receipts: `evidence/p0/p0-07/`, evaluados sobre
  `b5ddce10f10615e8247bdb2947a4943d55bf24a3` con `dirty: false` e integridad
  canónica aprobada.
- Review: `docs/security/2026-07-17-p0-07-beacon-fusion-retention-review.md`.
- Residuales: P0-R004 queda controlado para simulación y planificado para P1;
  P0-R010 se resuelve; P0-R014 gobierna el contrato pendiente de hold/deletion
  y disposition receipt. TM-011/TM-012 permanecen High.

### Evidencia P0-08

- Composición: `p0-integrated` ejecuta 13/13 gates de P0-02–P0-07 y proyecta
  energía, comunicación, mensajes, beacon y review sin sustituirlos por claims.
- Campaña: tres celdas Meshtastic/MeshCore/Reticulum, carry bundle en cada una,
  partición de 86.400 segundos y 11/11 fallos/adversarios con disposición.
- Safety: cero false acceptance/confirmation/absence, silent success, pérdida de
  accepted log/estado vital o inversión SOS; cuatro distress quedan en review.
- Autonomía: 3/3 celdas operan sin superior, 3/3 carry bundles se reconcilian y
  energía/radio/sensing degradan con seis gaps componentes visibles.
- Determinismo: diez órdenes producen un único hash integrado
  `54c52e8383cd4ed4cc57604c6cb74c85425b80e333e9eb5184f445edf5351441`.
- Receipt: `evidence/p0/p0-08/p0-integrated/p0-08-receipt.json`, evaluado sobre
  `6eb7bcbbd9e4fdde3d63437e097d385577fd422c` con `dirty: false` e integridad.
- Review: `docs/security/2026-07-17-p0-08-integrated-fault-review.md`.
- Residuales: P0-R011 cierra integración simulada y conserva power-cut físico;
  P0-R015 gobierna que la composición in-process no es runtime distribuido.

### Evidencia P0-09

- Exit: `p0-all` pasó 27/27 gates independientes sobre
  `53fe18e4d1427cc355e423103cfe6b263ad0e3b3`, con receipts íntegros y repo
  limpio en `evidence/p0/p0-09/`.
- Supply chain: SBOM CycloneDX 1.7 con 124 componentes, 124/124 licencias
  revisadas, cero vulnerabilidades conocidas en los lockfiles y cero secretos
  en 701 archivos; los negativos sintéticos fueron detectados.
- Soporte: matriz 3×3 por perfil/bearer; sólo `experimental` o `unverified`,
  sin ganador global ni hardware `supported`.
- Decisión física: nueve categorías con una unidad candidata cada una, todas
  `unverified`, `shortlisted_no_purchase` y sujetas a autorización separada.
- Residuales: P0-R001–P0-R015 tienen estado, owner, gate/plan y stop condition;
  ninguno queda vencido en P0-09.

P0 está cerrado.

## Now — Open Spec

Progreso de aceptación: Open Spec `8 / 8` (`100%`). Los contratos y perfiles
abiertos avanzan sin exigir hardware propio; los evidence packs sólo elevan el
nivel de evidencia de una implementación exacta.

- [x] `OS-01`: frontera spec/evidencia, nueve perfiles de capacidad y claim schema.
- [x] `OS-02`: cuatro topologías energéticas, nueve mappings de rol, ocho source
  adapters, cargas L0–L3, solar opcional y claims acotados.
- [x] `OS-03`: cinco perfiles multi-bearer abiertos, selección por misión y sin ganador universal.
- [x] `OS-04`: mensajería, estado, SOS y ubicación interoperables.
- [x] `OS-05`: beacons y extensiones modales.
- [x] `OS-06`: federación recursiva y autonomía local; cinco niveles autónomos,
  aislamiento por ResponseCell, peering explícito, hubs no autoritativos y
  reconciliación determinística. La referencia 50k no acredita capacidad física.
- [x] `OS-07`: cinco planos/BOMs por capacidades, once adapters y cinco guías;
  construcción abierta, reutilización e híbrida son rutas equivalentes. Ningún
  vendor/SKU es obligatorio y `specified` no acredita performance física.
- [x] `OS-08`: conformance kit, submission schema, matriz normativa, publicación
  offline y proceso comunitario append-only para evidence packs.

Plan activo: `docs/superpowers/plans/2026-07-18-openbrec-open-spec-plan.md`.
OS-04 define cuatro contenidos cerrados y eventos SOS append-only. Separa
recepción técnica, lectura humana, aceptación operativa y lifecycle; ninguna
garantiza rescate. Distress inválido o expirado se preserva como
`unverified_distress` para review, nunca se descarta ni autentica automáticamente.
Los fixtures son simulados y no prueban entrega RF, comprensión humana, custodia
de claves, precisión de ubicación ni resultado de rescate.

OS-05 fija una modalidad como mínimo conformante y tres como referencia opcional.
Acústica opera por features locales; movimiento y térmica no prueban ocupación,
identidad, diagnóstico ni ausencia. Las extensiones requieren namespace, schema,
dataset y reviews propios. Los fixtures sintéticos prueban conformance, abstención
y replay determinístico, no performance física ni representatividad.

Open Spec está cerrada. La próxima task gobernada es `P1a-01`, dentro del carril
físico opcional; no fue iniciada y sigue `blocked_external_evidence` hasta que
existan autorización, custodia y manifests exactos para nueve assets.

## Optional validation lane — P1a banco y conducted

Progreso de aceptación: `0 / 8` (`0%`). El paquete de readiness no suma una
task P1a.

- [ ] `P1a-01`: assets exactos, custodia y capability manifests.
- [ ] `P1a-02`: LoRaWAN/Meshtastic/MeshCore/RNode conducted.
- [ ] `P1a-03`: comprensión de terminal con 8+8 participantes.
- [ ] `P1a-04`: un beacon tri-modal aislado.
- [ ] `P1a-05`: tres beacons y fallos correlacionados.
- [ ] `P1a-06`: caracterización energética exacta.
- [ ] `P1a-07`: ensayo storage-only 72 horas.
- [ ] `P1a-08`: tres ResponseCells por cable/IP.

Readiness: plan de ocho tasks, schema de manifest exacto, política que deja
compra/préstamo/hardware/conducted/personas/captura como `not_authorized`, TX
radiado `prohibited_in_p1a` y ocho residuales gobernados. `P1a-01` queda como
siguiente task, no iniciada: requiere autorización explícita de asset/custodia.

Evidencia readiness: gate `p1a-readiness` aceptado sobre
`922cc7fd2c505d8bfa10dd7367299adccd996b70`, con `dirty: false`, ocho tasks
planificadas, cero aceptadas, cero acciones físicas autorizadas y receipt en
`evidence/p1a/readiness/`. Este readiness no incrementa el numerador P1a.

Plan activo: `docs/superpowers/plans/2026-07-17-openbrec-p1a-bench-conducted-plan.md`.
Residuales activos: `docs/governance/p1a-residuals.json`.

Este plan ya no es la autoridad principal. P1a preserva evidencia física y
permite claims `lab_validated`/`field_validated`; su bloqueo no impide publicar
la Open Spec.

Estado P1a-01: `blocked_external_evidence`. El gate `p1a-assets` exige 9/9
categorías exactas, autorización correlacionada, custodia, inspección, serial
evidence hasheada y firmware pin donde aplica. El repositorio no contiene ni
fabrica esos nueve assets: la solicitud trazable está en
`docs/governance/p1a-01-asset-authorization-request.json`. Progreso: `0 / 8`
(`0%`). P1a-02 no iniciada.

El comando `openbrec.verify p1a-assets-intake` publica un checklist determinístico
por las nueve categorías y queda documentado en
`docs/governance/P1A_ASSET_INTAKE.md`. Es un preflight no contable: no autoriza
acciones físicas, valida submissions parciales antes de contarlas como listas
para el gate, no acepta P1a-01 y no cambia el numerador `0 / 8`.

Frontera: P0 no autoriza compra, hardware, TX, captura real, ensayo de 72 horas,
campo ni claims físicos. Solar, storage, generadores, conducted/radiated radio,
beacons físicos y validación humana pertenecen a planes posteriores.

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
