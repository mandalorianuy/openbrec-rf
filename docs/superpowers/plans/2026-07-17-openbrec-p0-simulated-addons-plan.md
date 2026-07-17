# OpenBREC P0 — plan ejecutable de addons completamente simulados

- Estado: aprobado y activo para secuenciación
- Fecha: 2026-07-17
- Autoridad de secuencia: `DELIVERY_BOARD.md`
- Baseline requerido: M0 cerrado en `0dee758af0a1ea02578e0710f81d361933651756`
- Alcance: P0-01–P0-09, simulación, fixtures, replay, UI y receipts
- Estado de ejecución: `4 / 9` tasks aceptadas (`44.4%`); `P0-05` elegible, no iniciada
- Fuera de alcance: compra, hardware, TX, ensayo radiado, campo y claims físicos

## 1. Objetivo

Convertir las decisiones aprobadas de energía, comunicaciones, federación,
mensajería y beacons en contratos y experimentos reproducibles sobre el core M0.
P0 debe reducir incertidumbre antes de seleccionar hardware, sin confundir una
simulación con evidencia de radio, autonomía, detección o usabilidad humana.

El exit P0 produce support status por perfil, evidencia negativa y una decisión
de piloto P1a. No selecciona una mesh global, no acredita 72 horas y no afirma
presencia o ausencia de personas.

## 2. Autoridades y precedencia

1. `AGENTS.md` y ADR-0001 fijan las red lines.
2. `DELIVERY_BOARD.md` decide qué task puede ejecutarse.
3. Este documento decide orden, aceptación y stop conditions P0.
4. Las cuatro especificaciones hijas definen los contratos y boundaries.
5. La matriz conjunta y el estado del arte conservan alternativas y decisiones.
6. `docs/governance/P0_RESIDUAL_REGISTER.md` gobierna toda incertidumbre nueva.

Ante contradicción se detiene la task y se registra el residual; no se resuelve
por una implementación oportunista.

## 3. Frontera autorizada

P0 puede:

- agregar schemas, fixtures, modelos generados y migraciones sólo si una task lo exige;
- implementar simuladores, adapters modelados, replay, fault injection y UI offline;
- fijar versiones y formatos de entrada para reproducir propiedades documentadas;
- producir métricas, receipts, resultados negativos y decisiones por perfil.

P0 no puede:

- comprar o seleccionar flotas, radios, baterías, paneles o sensores;
- transmitir RF, controlar un generador o conectar un pack físico;
- capturar audio de personas o ambientes reales;
- usar credenciales, IDs o datos operacionales reales;
- declarar `supported` hardware, alcance RF, 72 horas, detección o readiness de campo;
- crear una dependencia cloud o un hub en el camino crítico;
- inferir ausencia, identidad, biometría o confirmación automática de presencia.

## 4. Roles lógicos

| Rol | Responsabilidad |
|---|---|
| `contract-maintainer` | Catálogo, schemas, fixtures, generación y compatibilidad. |
| `core-replay-maintainer` | Canonicalización, determinismo, disposición y simulación. |
| `energy-maintainer` | EnergyDomain, budget, FSM, brownout y degradación. |
| `radio-transport-maintainer` | Adapters modelados, perfiles, airtime y anti-loop. |
| `federation-maintainer` | Jerarquía recursiva, partición y reconciliación masiva. |
| `privacy-safety-reviewer` | Life-safety, autenticidad, retención y red lines. |
| `beacon-science-maintainer` | Modalidades, incertidumbre, OOD y evaluación científica. |
| `product-ux-reviewer` | Terminal offline, semántica SOS y accesibilidad verificable. |
| `release-reviewer` | Independencia de gates, receipts, residuales y exit P0. |

Los roles son funciones de revisión, no identidades personales. Una misma
persona puede implementar y revisar aspectos distintos, pero el acceptance
receipt identifica actor de implementación y actor de revisión por separado.

## 5. Reglas de ejecución

- Sólo una task P0 puede estar `in_progress` en el board.
- Una task comienza desde `main` limpio y sincronizado en rama `codex/` propia.
- Tests negativos preceden o acompañan cada nueva capacidad.
- JSON Schema continúa como autoridad; modelos generados no reemplazan validación.
- Cada input termina en accepted log, quarantine, vault o ledger.
- Todo gate escribe receipt con SHA, dirty state, runtimes, locks, inputs y outputs.
- Un resultado negativo se conserva y se vincula a task, fixture y residual.
- Un residual `planned` que llega a su task sin cierre pasa a `blocked`.
- Implementación, validación, entrega y aceptación se informan por separado.
- El cierre de una task no inicia automáticamente la siguiente.

Los nombres de comandos definidos abajo son interfaces de aceptación. Un comando
que todavía no existe no cuenta como gate y debe ser creado/testeado en su task.

## 6. Secuencia P0

### P0-01 — Contratos addon y fixtures normativos

- Owner: `contract-maintainer`
- Reviewer: `privacy-safety-reviewer`
- Dependencia: M0 aceptado
- Mapeo: E-01, C-03, C-04, C-06, C-09, B-01–B-06

Entregables:

- schemas de energía, mensaje/eventos humanos, envelope, transport profile,
  capability, policy decision, federación, terminal, beacon, placement,
  autorización de captura y review;
- catálogo/versiones y compatibilidad contra el baseline M0;
- fixtures válidos, inválidos, hostiles y de capabilities ausentes;
- Pydantic/TypeScript generados y comprobación de asignabilidad.

Validación objetivo:

```text
python -m openbrec.verify addon-contracts
python -m openbrec.verify addon-fixtures
python -m openbrec.verify contracts-gen --check
python -m openbrec.verify schema-compat
```

Aceptación:

- objetos cerrados, unidades/uncertainty normativas y provenance completo;
- `HumanMessage`, SOS y acuses no aceptan estados de transporte como estado operativo;
- observaciones beacon especializan `Observation`, sin cadena paralela;
- no existe clase de ausencia, identidad o presencia confirmada;
- fixtures negativos prueban cada boundary y la generación no deja diff.

Stop conditions:

- schema duplicado o incompatible sin decisión SemVer;
- `measurements` arbitrario vuelve a abrir el boundary;
- bytes de transporte o raw sensor aparecen como hechos;
- contrato vital puede descartarse sin disposition receipt.

Evidencia: `evidence/p0/p0-01/`.

### P0-02 — EnergyDomain, budget, FSM y brownout replay

- Owner: `energy-maintainer`
- Reviewer: `core-replay-maintainer`
- Dependencia: P0-01 aceptada
- Mapeo: E-01

Entregables:

- tres EnergyDomains simulados con cargas L0/L1/degradables;
- balance de energía con incertidumbre, pérdidas y runtime lower bound;
- FSM con hysteresis y estados de conservación/degradación;
- fallos de sensor, source loss, brownout, reinicio y SOC `unknown`.

Validación objetivo:

```text
python -m openbrec.verify energy-replay --scenario fixtures/p0/energy/three-domains.json
python -m openbrec.verify determinism --runs 10
```

Aceptación:

- conservación de energía y unidades dimensionalmente consistentes;
- mismo input/config produce mismo hash bajo orden, locale y timezone distintos;
- pérdida central no elimina reserva/estado local simulado;
- SOS/log desplazan carga degradable según política visible;
- nunca se emite un claim de 72 horas o funcionamiento indefinido.

Stop conditions:

- cálculo usa irradiancia, capacidad o load no declarado;
- brownout borra secuencia, accepted log o estado vital;
- `unknown` se convierte en cero o autonomía optimista.

Evidencia: `evidence/p0/p0-02/`.

### P0-03 — Mensajería segura, SOS append-only y transporte hostil

- Owner: `privacy-safety-reviewer`
- Reviewer: `core-replay-maintainer`
- Dependencias: P0-01 y P0-02 aceptadas
- Mapeo: C-03, C-09, B-02

Entregables:

- firma/autenticidad de aplicación, AEAD y vectores reproducibles;
- identidad por incidente, enrolamiento modelado, revocación y rekey offline;
- reducer SOS append-only con estados técnicos y operativos separados;
- deduplicación, TTL, anti-replay, anti-loop y receipts por bearer;
- fixtures forged, replayed, revoked, late, duplicate y malicious transport.

Validación objetivo:

```text
python -m openbrec.verify human-message-security
python -m openbrec.verify sos-state-replay
python -m openbrec.verify transport-policy
```

Aceptación:

- cero false `operator.accepted`;
- ACK técnico nunca equivale a visto, aceptado o asignado;
- default/shared incident secrets fallan el gate;
- reinicio/rollback no reutiliza nonce ni secuencia;
- duplicación por múltiples bearers produce un mensaje lógico y receipts separados.

Stop conditions:

- estado recibido reemplaza el log de eventos;
- transporte puede suplantar actor o elevar rol;
- revocación depende de hub/Internet para proteger la celda local.

Evidencia: `evidence/p0/p0-03/`.

### P0-04 — Comparación multi-bearer por TransportProfile

- Owner: `radio-transport-maintainer`
- Reviewer: `privacy-safety-reviewer`
- Dependencia: P0-03 aceptada
- Mapeo: C-01, C-02, C-09, A-01, A-02

Entregables:

- adapters/modelos versionados para Meshtastic, MeshCore y Reticulum;
- perfiles `mobile_spontaneous_team`, `planned_urban_response_cell` y
  `heterogeneous_gateway_backbone`;
- workloads comunes de 12, 40 y 100 nodos, movilidad, relay loss, path churn,
  flood, partición, carry y tráfico SOS/estado/ubicación;
- métricas PDR, p50/p95/p99, airtime, retries, duplicates, convergencia,
  energía modelada y metadata disclosure.

Validación objetivo:

```text
python -m openbrec.verify transport-comparison --workload fixtures/p0/transports/common-workload.json
python -m openbrec.verify malicious-transport
```

Aceptación:

- los tres candidatos consumen el mismo `OpenBRECEnvelope`;
- cero false operational acceptance y denominadores completos;
- no se puentean frames/floods crudos;
- cada resultado queda limitado a versión, modelo y perfil;
- no existe ganador global ni claim de rango/hops físicos.

Stop conditions:

- modelo atribuye al protocolo una propiedad no documentada o no fijada;
- se omiten mensajes fallidos del denominador;
- SOS no conserva prioridad antes de entrar al bearer.

Evidencia: `evidence/p0/p0-04/`.

### P0-05 — Federación masiva y autonomía recursiva

- Owner: `federation-maintainer`
- Reviewer: `core-replay-maintainer`
- Dependencias: P0-03 y P0-04 aceptadas
- Mapeo: C-04, C-06

Entregables:

- escenario de 50.000 sites, 60 ResponseCells, 5 OperationalAreas y 2 hubs;
- operación local durante pérdida de ambos hubs y partición de 24 horas;
- outbound-only federation, carry bundles, handoff y conflicto visible;
- reconciliación determinística ante IDs concurrentes, duplicados y hub hostil.

Validación objetivo:

```text
python -m openbrec.verify federation-scale --scenario fixtures/p0/federation/50k-sites.json
python -m openbrec.verify federation-reconciliation
```

Aceptación:

- cada componente jerárquico opera sin depender del superior;
- cero overwrite o pérdida silenciosa;
- un hub no falsifica firmas, descifra contenido local ni ordena TX;
- sólo eventos/resúmenes autorizados cruzan fronteras;
- replay reproduce conflictos y resoluciones humanas pendientes.

Stop conditions:

- broker, identidad o CA central entra al camino crítico;
- una partición detiene SOS, sensing o decisiones locales;
- conflicto se resuelve por last-write-wins silencioso.

Evidencia: `evidence/p0/p0-05/`.

### P0-06 — Terminal offline y semántica humana

- Owner: `product-ux-reviewer`
- Reviewer: `privacy-safety-reviewer`
- Dependencias: P0-03 y P0-05 aceptadas
- Mapeo: B-01, B-02

Entregables:

- flujos offline para texto breve, estado, SOS y ubicación;
- estados queued/sent/delivered/seen/accepted/cancelled/expired derivados del log;
- cobertura, capacidades ausentes, incertidumbre y cola visibles;
- copy explícito: aceptación no garantiza arribo y silencio no implica ausencia;
- UI smoke automatizado, accesibilidad técnica y guion P1a de comprensión humana.

Validación objetivo:

```text
python -m openbrec.verify terminal-ux
python -m openbrec.verify ui-smoke
python -m openbrec.verify accessibility
```

Aceptación:

- terminal usable sin Internet, hub o servicio superior;
- ninguna acción crítica depende sólo de color, audio o haptic;
- cancelación no borra SOS ni receipts anteriores;
- pérdida de bearer deja cola/gap visible;
- P0 no afirma comprensión humana: deja protocolo P1a versionado.

Stop conditions:

- copy promete rescate/entrega no demostrada;
- UI oculta missing capability, expiry, incertidumbre o partición;
- estado operativo se edita directamente.

Evidencia: `evidence/p0/p0-06/`.

### P0-07 — Beacons, fusión determinística y retención

- Owner: `beacon-science-maintainer`
- Reviewer: `privacy-safety-reviewer`
- Dependencias: P0-01, P0-02 y P0-06 aceptadas
- Mapeo: B-03, B-04, B-05, B-06

Entregables:

- fixtures acústicos feature-only, PIR/movimiento y térmicos low-resolution;
- capabilities, placement, health, uncertainty, OOD y sensor missing;
- baseline determinístico single/corroborated/unknown/artifact;
- snippet authorization modelada, vault, hold, review y retention faults;
- spoofed sound/heat/motion y causas correlacionadas.

Validación objetivo:

```text
python -m openbrec.verify beacon-replay
python -m openbrec.verify beacon-adversarial
python -m openbrec.verify retention-fault
```

Aceptación:

- cero outputs automáticos de presencia confirmada o ausencia;
- raw/transport bytes no se convierten en hechos;
- todo sensor ausente, gap, node move y baseline inválido es visible;
- material posible life-safety se preserva para review antes de minimizar;
- modalidades co-localizadas no se cuentan como evidencia independiente.

Stop conditions:

- fixture real carece de licencia, consentimiento o provenance;
- expiry borra material sin disposition receipt;
- resultado oculta falsos positivos, OOD o cobertura insuficiente.

Evidencia: `evidence/p0/p0-07/`.

### P0-08 — Campaña integrada de fallos

- Owner: `core-replay-maintainer`
- Reviewer: `release-reviewer`
- Dependencias: P0-02–P0-07 aceptadas
- Mapeo: F-05 y todos los addons P0

Entregables:

- campaña conjunta con partición 24h, node/relay/source/hub loss y brownout;
- forged distress, replay, terminal robado, spoofed sensor y hub malicioso;
- operación de múltiples celdas con bearers distintos y carry bundle;
- proyección offline de energía, comunicación, mensajes, beacon y review.

Validación objetivo:

```text
python -m openbrec.verify p0-integrated --scenario fixtures/p0/integrated/campaign.json
python -m openbrec.verify determinism --runs 10
python -m openbrec.verify privacy
python -m openbrec.verify security
```

Aceptación:

- cero false acceptance, confirmation o absence;
- cero inputs no reconciliados y 100% de gaps reportados;
- cada celda continúa localmente sin hubs/backhaul;
- energía/radio/sensing degradan con estado y explicación visibles;
- misma campaña produce el mismo hash bajo variaciones de ejecución.

Stop conditions:

- un addon evita contratos/replay/disposition M0;
- un fallo genera éxito silencioso;
- el escenario sólo pasa reduciendo denominadores o quitando negativos.

Evidencia: `evidence/p0/p0-08/`.

### P0-09 — Exit, support status y decisión P1a

- Owner: `release-reviewer`
- Reviewers: todos los roles P0
- Dependencia: P0-01–P0-08 aceptadas

Entregables:

- jobs independientes y un receipt por gate P0;
- matriz de trazabilidad requisito → fixture → gate → receipt;
- support status por `TransportProfile`, versión y escenario;
- SBOM/licencias/vulnerabilidades/secret scan actualizados;
- review de privacidad, seguridad, ciencia, UX y residual register;
- shortlist P1a de una unidad por categoría, sin compra automática.

Validación objetivo:

```text
python -m openbrec.verify p0-all --evidence-dir evidence/p0
git diff --exit-code
```

Aceptación:

- todos los gates P0 fallan de forma independiente y sus receipts son íntegros;
- cada alternativa queda `experimental`, `unverified`, `unavailable` o `deferred`
  por perfil, nunca `supported` global;
- resultados negativos y opciones descartadas permanecen revisables;
- cero residuales sin estado/owner/gate/stop condition;
- P1a sólo queda elegible mediante plan y autorización separados.

Stop conditions:

- receipt no corresponde al SHA evaluado;
- un claim físico deriva sólo de simulación;
- hardware aparece `supported` o comprado sin P1a;
- un residual queda como comentario o diferido sin owner.

Evidencia: `evidence/p0/p0-09/` y `evidence/p0/p0-exit-manifest.json`.

## 7. Gate de salida P0

P0 termina únicamente cuando:

- P0-01–P0-09 están aceptadas individualmente;
- cero false `operator.accepted`;
- cero outputs automáticos de presencia confirmada o ausencia;
- cero overwrite, descarte o pérdida silenciosa;
- todas las celdas operan aisladas bajo partición;
- energía, radio y sensing degradan con gaps visibles;
- el workload común compara Meshtastic, MeshCore y Reticulum sin ganador global;
- la federación masiva reconcilia conflictos determinísticamente;
- cada candidato físico continúa `unverified`;
- threat model, reviews, SBOM y residuales corresponden al SHA final.

## 8. Métrica de avance

El único numerador de progreso es `tasks aceptadas / 9`.

- task documentada, iniciada, implementada o con tests parciales: no aceptada;
- CI verde sin review/receipt de la task: no aceptada;
- investigación, matriz, mockup o selección verbal: no aceptada;
- simulación P0: no cuenta como progreso P1 ni evidencia física;
- cierre de una task no suma la siguiente ni autoriza trabajo oportunista.

## 9. Estado de ejecución gobernado

P0-01 fue aceptada el 2026-07-17 sobre el SHA de implementación
`9f741fd204c5abb89c1ca1b457b9d4cc9c910f24`; sus cuatro receipts limpios viven
en `evidence/p0/p0-01/` y su review en
`docs/security/2026-07-17-p0-01-addon-contracts-review.md`.

P0-02 fue aceptada el 2026-07-17 sobre el SHA de implementación
`91c78a09200b592aa1c4b1bb6c416026213d1a1d`; sus receipts limpios viven en
`evidence/p0/p0-02/` y su review en
`docs/security/2026-07-17-p0-02-energy-replay-review.md`.

P0-03 fue aceptada el 2026-07-17 sobre el SHA de implementación
`c6a3dc15ccf045dac60148080870a5f44eb2027c`; sus receipts limpios viven en
`evidence/p0/p0-03/` y su review en
`docs/security/2026-07-17-p0-03-secure-messaging-review.md`.

P0-04 fue aceptada el 2026-07-17 sobre el SHA de implementación
`7e01320ec9520316add7a7d2915fbb1426106bc1`; sus receipts limpios viven en
`evidence/p0/p0-04/` y su review en
`docs/security/2026-07-17-p0-04-transport-comparison-review.md`. P0-05 queda
como única task elegible, pero este closeout no la inicia. El progreso P0 es
`4 / 9` (`44.4%`).
