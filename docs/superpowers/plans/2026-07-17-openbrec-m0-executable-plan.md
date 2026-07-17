# Plan ejecutable M0 de OpenBREC RF

- Estado: aprobado el 2026-07-17; M0-01 completado; M0-02 en validación
- Fecha: 2026-07-17
- Alcance: cierre exclusivo de F-01–F-06
- Autoridad de secuencia: `DELIVERY_BOARD.md`
- Autoridad contractual: `docs/superpowers/specs/2026-07-16-openbrec-core-contracts-replay-design.md`
- Condición: no habilita addons P0/P1/P2, compras, hardware, TX ni despliegues

## 1. Resultado buscado

Convertir el bundle de diseño actual en un M0 mínimo, offline, reproducible y verificable. Al terminar deben existir contratos normativos, consumidores generados, servicios mínimos construibles, preservación sin pérdida silenciosa, replay determinístico, simulación sintética, una PWA de explicación y gates separados con receipts.

El plan no implementa energía, comunicaciones off-grid, federación, mensajería humana, SOS ni beacons. Esas capacidades permanecen documentadas en la matriz, pero bloqueadas hasta aprobar la evidencia completa de salida M0.

## 2. Baseline y límites

El estado inicial verificable es:

- `python3 scripts/validate_bundle.py` acredita sólo estructura histórica;
- `docker-compose.yml` referencia `apps/api`, `apps/fusion-worker` y `apps/web`, todavía inexistentes;
- `services/README.md` declara placeholders;
- los schemas actuales quedan como legacy sin afirmar compatibilidad ni calidad normativa;
- el workflow actual ejecuta un único gate estructural.

Red lines durante todo M0:

- no TX activo ni control de hardware;
- no dependencias cloud ni descarga de red durante startup/replay;
- sólo datos sintéticos o fixtures sanitizados;
- ningún plugin escribe hechos directamente;
- ningún silencio o sensor negativo afirma ausencia;
- todo input recibe una disposición primaria auditable;
- los modelos generados no reemplazan la validación JSON Schema Draft 2020-12.

## 3. Forma de ejecución

Se ejecuta una task por vez y en el orden `M0-01` a `M0-06`. Una task sólo se marca completa cuando:

1. sus cambios están implementados;
2. sus checks estrechos pasan;
3. produce los receipts definidos;
4. se revisa el diff y la autoridad documental;
5. el commit queda identificado en el receipt.

Un fallo bloqueante detiene la secuencia. No se sustituye una evidencia faltante con texto manual ni se comienza la task siguiente para aparentar progreso.

Los comandos `python -m openbrec.verify ...` son la interfaz objetivo que M0 debe implementar. Antes de existir, deben figurar como `not_implemented`; no pueden declararse pasados.

## 4. Responsables lógicos

| Rol | Responsabilidad |
|---|---|
| `contract-maintainer` | catálogo, schemas, fixtures, generación y compatibilidad |
| `core-replay-maintainer` | canonicalización, engines, reconciliación y receipts |
| `runtime-maintainer` | API, worker, PWA, Compose y startup offline |
| `privacy-safety-reviewer` | handling, vault, quarantine, ledger y red lines |
| `release-reviewer` | aceptación de gates, versiones y M0 exit |

Una persona puede cubrir más de un rol, pero los cambios de campos sensibles, retención o preservación requieren una decisión explícita del `privacy-safety-reviewer`. El M0 exit requiere revisión separada del `release-reviewer`.

## 5. Layout objetivo mínimo

```text
apps/
  api/
  fusion-worker/
  web/
openbrec/
  contracts/
  handling/
  replay/
  simulator/
  verify/
schemas/
  legacy/catalog.json
  core/catalog.json
  core/1.0.0/*.schema.json
fixtures/
  contracts/core/1.0.0/{valid,invalid}/
  replay/{adapter,core}/
generated/
  python/
  typescript/
evidence/
  m0/<gate>/<receipt>.json
```

La implementación puede ajustar nombres internos mediante ADR, pero no puede cambiar las fronteras contractuales, la reconciliación o la interfaz de gates sin actualizar la especificación y aprobar el cambio.

## 6. Tasks

### M0-01 — ADR-0001, catálogo y baseline legacy

Mapeo: F-01.

Objetivo: establecer una única precedencia documental y congelar el punto de partida contractual antes de generar código.

Entregables:

- `docs/adr/ADR-0001-core-scope-authority-and-red-lines.md` aceptado;
- inventario `schemas/legacy/catalog.json` con path, `$id` observado, versión declarada y SHA-256 de cada schema existente;
- esqueleto `schemas/core/catalog.json` con Draft 2020-12, reglas de registro y versión `1.0.0` reservada;
- decisión de toolchain Python 3.12/Node, lockfiles y política offline;
- receipt del baseline estructural que diga expresamente `structural_only`.

Checks estrechos:

```text
python3 scripts/validate_bundle.py
python -m openbrec.verify bundle-structure
python -m openbrec.verify schema --catalog schemas/legacy/catalog.json
```

El segundo y tercer comando son parte del entregable; no se dan por existentes al comenzar.

Aceptación:

- ADR-0001 resuelve precedencia, core/addon boundary, red lines y política de cambios;
- cada schema legacy está inventariado y su hash queda congelado;
- el catálogo rechaza `$id` duplicados y rutas fuera de la raíz permitida;
- ningún schema legacy se mueve o corrige en esta task.

Stop conditions:

- un schema no puede identificarse de forma unívoca;
- toolchain o licencias impiden generación offline reproducible;
- ADR-0001 no obtiene aprobación.

### M0-02 — Contratos, fixtures y generación

Mapeo: F-01.

Dependencia: M0-01 cerrado.

Objetivo: materializar la familia core `1.0.0` y dos consumidores reproducibles sin crear aún lógica addon.

Entregables:

- schemas mínimos definidos por la especificación core, incluyendo `DomainEvent`, provenance, handling policy, capability/health, observation, evidence, fusion result, audit, validation failure y receipts;
- fixtures positivos/negativos por schema según la matriz mínima normativa;
- formatos custom, resolución de `$ref` local y catálogo cerrado;
- modelos Pydantic v2 y TypeScript generados y commiteados;
- política SemVer e historial de compatibilidad.

Checks estrechos:

```text
python -m openbrec.verify schema
python -m openbrec.verify fixtures
python -m openbrec.verify schema-compat
python -m openbrec.verify contracts-gen --check
```

Aceptación:

- todos los `$id` core son únicos y Draft 2020-12 válido;
- cada schema tiene instancias mínima/completa válidas y casos inválidos exigidos;
- fixtures válidos pasan schema y ambos consumidores; inválidos fallan antes de construir modelos;
- regenerar produce diff vacío y no contiene timestamps/rutas absolutas;
- los hashes legacy permanecen idénticos.

Stop conditions:

- el generador pierde un constraint normativo sin un runtime validator previo;
- aparecen refs remotos o generación dependiente de red;
- un cambio legacy no está explicado y aprobado.

### M0-03 — Runtime mínimo y startup offline

Mapeo: F-02.

Dependencia: M0-02 cerrado.

Objetivo: sustituir placeholders por servicios mínimos reales que acepten sólo contratos validados y arranquen sin Internet.

Entregables:

- API FastAPI con health/readiness e ingreso contractual;
- worker asyncio con consumo local, validación y publicación de estados;
- PWA React/TypeScript/Vite mínima instalable y usable offline;
- Mosquitto y PostgreSQL configurados para laboratorio, sin credenciales default publicadas ni exposición innecesaria;
- Compose `lab-sim` con builds, healthchecks, red interna y volúmenes declarados;
- smoke offline reproducible.

Checks estrechos:

```text
docker compose config --quiet
docker compose build
python -m openbrec.verify compose-build
python -m openbrec.verify offline-startup
```

La prueba offline debe arrancar con red externa denegada después de disponer de imágenes y dependencias fijadas. No se considera offline una ejecución que resuelve paquetes o consulta servicios externos durante startup.

Aceptación:

- cada directorio referenciado por Compose existe y construye;
- todos los healthchecks llegan a healthy sin cloud;
- una observación sintética válida atraviesa bus, API y worker;
- un input inválido no entra al accepted path;
- la PWA recarga su shell y última proyección sin conectividad externa.

Stop conditions:

- credenciales default o MQTT anónimo quedan expuestos fuera de una red de laboratorio contenida;
- startup depende de DNS/HTTP externo;
- un servicio acepta payload sin validación normativa.

### M0-04 — Disposición, preservación y replay determinístico

Mapeo: F-03 y F-04.

Dependencia: M0-03 cerrado.

Objetivo: demostrar que el core transforma inputs reproduciblemente y que ninguna unidad desaparece en errores, revisión o preservación.

Entregables:

- `AcceptedEventLog`, `ReviewQuarantine`, `EvidenceVault` y `RejectionLedger` con reconciliación por hash/offset;
- perfiles `routine_minimized` y `life_safety_preservation` con audit, TTL y break-glass contractual;
- adapter replay y core replay separados;
- RFC 8785 JCS, SHA-256, Decimal y orden normativo;
- receipts fallidos y exitosos sin filtrar material sensible;
- fixtures de duplicado, colisión, tardío, corrupto, schema desconocido y fuente ausente.

Checks estrechos:

```text
python -m openbrec.verify adapter-replay
python -m openbrec.verify core-replay
python -m openbrec.verify determinism --runs 10
python -m openbrec.verify review-quarantine
python -m openbrec.verify life-safety-preservation
python -m openbrec.verify privacy
python -m openbrec.verify security
```

Aceptación:

- diez corridas producen el mismo `result_sha256`;
- orden de archivos, locale y timezone no alteran el hash;
- colisión de idempotencia o input inválido aborta outputs derivados y genera receipt;
- cada input se reconcilia exactamente con un destino primario;
- objeto posiblemente vital se preserva sellado y nunca se borra sin review/receipt;
- secreto claramente ajeno no persiste en claro y deja `RejectionLedger` auditable;
- silencio o pérdida de fuente sólo degrada confianza/cobertura.

Stop conditions:

- cualquier pérdida o corrección silenciosa;
- acceso al vault sin audit o sin TTL;
- replay consulta red, reloj del host o aleatoriedad no fijada;
- falsa evidencia parcial después de un fallo.

### M0-05 — Simulador común y PWA explicable

Mapeo: F-05.

Dependencia: M0-04 cerrado.

Objetivo: ejecutar una campaña core sintética reproducible que pruebe degradación y explicación, sin simular todavía addons específicos.

Entregables:

- escenario versionado con seis nodos, dos tracks y tres zonas;
- reloj lógico y fault injection de pérdida, duplicado, partición, brownout lógico, reinicio y peer malicioso;
- capability manifests con sensores presentes/ausentes;
- proyección PWA de matriz de capacidades, mapa, timeline, fuentes, incertidumbre, explicación y abstención;
- bundle de replay y resultado esperado hasheado.

Checks estrechos:

```text
python -m openbrec.verify simulator --scenario fixtures/replay/core/m0-six-node.json
python -m openbrec.verify core-replay --bundle fixtures/replay/core/m0-six-node.json
python -m openbrec.verify determinism --runs 10
python -m openbrec.verify ui-smoke
```

Aceptación:

- el escenario se reproduce con el mismo resultado y las mismas disposiciones;
- perder un nodo o capacidad degrada cobertura/confianza sin crear ausencia;
- la UI distingue observación, evidencia e inferencia consolidada;
- cada resultado muestra timestamp, zona, precisión, confianza, fuentes, ausencias y explicación;
- ninguna pantalla afirma presencia/ausencia más allá del contrato.

Stop conditions:

- campaña dependiente del reloj real o del orden del filesystem;
- UI oculta incertidumbre, capacidades ausentes o abstención;
- fault injection produce resultados no reconciliados.

### M0-06 — Gates CI, receipts y exit

Mapeo: F-06.

Dependencia: M0-01–M0-05 cerrados.

Objetivo: separar implementación de validación y convertir el M0 exit en evidencia reproducible.

Entregables:

- jobs independientes para `bundle-structure`, `schema`, `fixtures`, `schema-compat`, `contracts-gen`, `compose-build`, `offline-startup`, `adapter-replay`, `core-replay`, `determinism`, `review-quarantine`, `life-safety-preservation`, `privacy`, `security`, secret scan, SBOM y licencias;
- receipts JSON como artefactos, con git SHA/dirty state, runtimes, lockfile/input/output hashes, comando y resultado;
- pruebas negativas que demuestran fail-closed por fixture inválido, hash alterado y secret dummy;
- actualización de README, threat model, safety/privacy review y board;
- informe de M0 exit firmado por roles lógicos.

Checks de cierre:

```text
python -m openbrec.verify all --evidence-dir evidence/m0
git diff --exit-code
```

La primera línea no reemplaza jobs separados: sólo orquesta los mismos gates y conserva un receipt por gate.

Aceptación:

- cada job puede fallar de forma independiente y publica su propia evidencia;
- fallos negativos inyectados son detectados por el gate correcto;
- SBOM/licencias/secret scan son reproducibles y no contienen secretos reales;
- el checkout queda sin outputs generados pendientes;
- el `release-reviewer` verifica uno por uno todos los criterios del board;
- sólo después se marca M0 completo y se puede proponer, no ejecutar automáticamente, un plan P0.

Stop conditions:

- un gate se reemplaza con checklist manual;
- receipts no corresponden al git SHA evaluado;
- CI depende de red durante la prueba offline;
- cualquier criterio del M0 exit permanece sin evidencia.

## 7. Trazabilidad F-01–F-06

| Matriz | Tasks | Evidencia de cierre |
|---|---|---|
| F-01 | M0-01, M0-02 | catálogos, fixtures, compatibilidad y generación sin diff |
| F-02 | M0-03 | Compose build/start offline y smoke de servicios/PWA |
| F-03 | M0-04, M0-05 | receipts adapter/core y hashes determinísticos |
| F-04 | M0-04 | reconciliación accepted/quarantine/vault/ledger y privacy review |
| F-05 | M0-05 | campaña versionada de seis nodos con fault injection |
| F-06 | M0-06 | jobs independientes, receipts, pruebas negativas y SBOM |

## 8. Evidencia y commits

Cada task debe producir evidencia bajo `evidence/m0/<gate>/`. Los receipts incluyen el SHA evaluado; por eso la corrida final se realiza sobre el commit de implementación y un commit posterior sólo puede actualizar referencias documentales, sin alterar el material validado.

Fronteras de commit recomendadas:

1. ADR/catálogos/baseline.
2. Schemas/fixtures/generación.
3. Runtime/Compose/offline smoke.
4. Handling/replay/determinismo.
5. Simulador/PWA.
6. CI/evidence/exit docs.

No se hace squash entre una evidencia aprobada y su material sin regenerar los receipts para el SHA resultante.

## 9. Gate de aprobación y primera acción

El plan fue aprobado el 2026-07-17 y el check correspondiente quedó registrado en `DELIVERY_BOARD.md`. `M0-01` quedó completado con receipts evaluados sobre un SHA limpio. `M0-02` está implementado y en validación; no se cierra hasta producir receipts sobre un SHA limpio y reconciliar `docs/governance/M0_RESIDUAL_REGISTER.md`. M0-03 y todo P0 permanecen bloqueados.
