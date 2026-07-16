# Contratos core y replay determinístico de OpenBREC RF

- Estado: diseño conversacional aprobado; documento pendiente de revisión
- Fecha: 2026-07-16
- Especificación padre: `2026-07-16-offgrid-energy-lora-beacons-design.md`
- Alcance: autoridad contractual común de M0 y replay en dos niveles
- Fuera de alcance: API, UI, Compose ejecutable, radio, energía y schemas específicos de addons

## 1. Propósito y condición de avance

Esta especificación convierte los principios actuales de OpenBREC RF en contratos verificables para el primer M0 ejecutable. Define:

- una familia canónica nueva de JSON Schemas;
- el envelope común de eventos;
- la separación `Observation → Evidence → FusionResult`;
- generación reproducible de modelos Pydantic y TypeScript;
- versionado y compatibilidad;
- replay de adapters y replay del core;
- cuarentena, preservación life-safety-first y recibos de rechazo;
- gates, responsables y artefactos de evidencia.

Este documento no autoriza todavía implementación ni un plan P0 off-grid. Después de su aprobación se continuará con las otras tres especificaciones hijas definidas por la especificación padre. El plan conjunto permanece bloqueado hasta aprobarlas y completar M0.

## 2. Autoridad y precedencia

La autoridad aplicable será, en orden:

1. `AGENTS.md` para safety, privacidad y red lines.
2. ADR-0001 aceptado para alcance del core y precedencia documental.
3. Esta especificación para semántica y aceptación de contratos/replay.
4. JSON Schema Draft 2020-12 publicado en el catálogo canónico para la forma de datos.
5. `DELIVERY_BOARD.md` para secuencia y estado.
6. Diseño técnico y prompt maestro como contexto no normativo ante conflictos.

Un modelo generado, fixture, implementación Pydantic, tipo TypeScript o documentación no puede cambiar la semántica del JSON Schema fuente.

## 3. Decisiones aprobadas

1. El core M0 define sólo contratos comunes y puntos de extensión.
2. Energía, mensajería humana y beacons tendrán schemas concretos en sus propias especificaciones.
3. Los `$id` son inmutables y versionados con SemVer.
4. Replay se divide en adapter y core, con receipts encadenables.
5. Pydantic y TypeScript se generan, versionan en Git y verifican sin diff.
6. Los schemas existentes se conservan como `legacy-unverified` sin reescribirlos.
7. La familia canónica nueva usa el namespace `/schemas/core/<schema-name>/<semver>`.
8. La estructura elegida es un envelope OpenBREC cerrado con payload tipado.
9. Ningún dato desaparece silenciosamente.
10. En operaciones BREC, la protección de vida prevalece sobre minimización y privacidad, con preservación sellada, proporcional y auditable.

## 4. Límites del core

El core puede:

- validar envelopes y payloads registrados;
- registrar eventos normalizados append-only;
- deduplicar y ordenar eventos;
- transformar observaciones en evidencia mediante reglas versionadas;
- fusionar evidencia mediante un engine versionado;
- producir receipts y auditoría;
- registrar schemas de addons sin importar su implementación.

El core no puede:

- importar SDKs o protobufs de hardware y transportes;
- interpretar bytes crudos de un sensor;
- permitir que un adapter publique `Evidence` o `FusionResult`;
- corregir silenciosamente un evento inválido;
- inferir ausencia de víctima por silencio de sensor, radio o red;
- confiar en modelos generados como autoridad de validación;
- incorporar contratos concretos de radio, energía, mensajería o beacons en esta familia inicial.

## 5. Arquitectura contractual

```text
fixture o fuente
  → adapter versionado
  → validación de DomainEvent + payload
  → accepted-event-log o ruta de revisión
  → Evidence Engine
  → Fusion Engine
  → outputs normalizados
  → CoreReplayReceipt
```

El core consumirá sólo `DomainEvent`. Cada evento contiene un envelope estable y un `payload` discriminado por `event_type` y `schema_ref`.

Los payloads evolucionan de forma independiente. Un addon registra un payload nuevo mediante catálogo y fixtures, pero no agrega campos al envelope ni cambia contratos del core.

### 5.1 Componentes lógicos

- `SchemaCatalog`: registra IDs exactos, hashes, versión, estado y dependencias.
- `ContractValidator`: valida metaschema, formatos, referencias y payload.
- `GeneratedModels`: proyecciones Pydantic v2 y TypeScript versionadas.
- `AcceptedEventLog`: log append-only de eventos válidos.
- `ReviewQuarantine`: almacén revisable de material inválido permitido.
- `EvidenceVault`: preservación sellada de material potencialmente vital.
- `RejectionLedger`: recibos de material que no debe persistirse en claro.
- `AdapterReplayRunner`: fixture crudo/sanitizado a eventos normalizados.
- `CoreReplayRunner`: eventos normalizados a evidencia y fusión.
- `ReceiptWriter`: recibos determinísticos y operacionales separados.

## 6. Catálogo y layout normativo

El layout objetivo será:

```text
schemas/
  legacy/
    catalog.json
  core/
    catalog.json
    1.0.0/
      domain-event.schema.json
      provenance.schema.json
      handling-policy.schema.json
      incident-event.schema.json
      deployment-event.schema.json
      zone-event.schema.json
      node-event.schema.json
      capability-manifest.schema.json
      health-status.schema.json
      observation.schema.json
      evidence.schema.json
      fusion-result.schema.json
      operator-annotation.schema.json
      audit-event.schema.json
      validation-failure.schema.json
      preservation-record.schema.json
      adapter-replay-receipt.schema.json
      core-replay-receipt.schema.json
fixtures/
  contracts/core/1.0.0/<schema-name>/{valid,invalid}/
  replay/{adapter,core}/
packages/contracts/generated/{python,typescript}/
```

No se moverán ni modificarán inicialmente los schemas existentes. `schemas/legacy/catalog.json` registrará su ruta actual, `$id`, SHA-256 y estado `legacy-unverified`. No se prometerá migración o compatibilidad hasta demostrarla con fixtures.

Cada entrada canónica de `schemas/core/catalog.json` incluirá:

- `$id` exacto;
- versión SemVer;
- ruta relativa;
- SHA-256 del archivo;
- categoría `envelope`, `payload`, `receipt` o `policy`;
- estado `supported`, `experimental`, `unverified` o `unavailable`;
- IDs de dependencias;
- versión mínima de generadores validada;
- responsable de contrato;
- fecha de aceptación.

El hash individual de cada schema será SHA-256 de sus bytes UTF-8 exactos. `contract_set_sha256` será SHA-256 hexadecimal minúsculo del JCS de un array de objetos `{id, sha256}` ordenado por `id`.

## 7. DomainEvent

`domain-event.schema.json` será un objeto cerrado. Sus grupos normativos serán:

### 7.1 Identidad y tipo

- `schema_version`: versión exacta del envelope.
- `schema_ref`: `$id` exacto del payload.
- `event_type`: discriminador registrado y estable.
- `event_id`: UUID v5 canónico en minúsculas, derivado determinísticamente de `idempotency_id`.
- `idempotency_id`: `urn:sha256:<64 hex minúsculos>`.
- `correlation_id`: UUID v4 del flujo operacional.
- `causation_event_ids`: array ordenado lexicográficamente y sin duplicados; vacío sólo para eventos raíz permitidos.
- `derivation_key`: obligatorio sólo para eventos derivados; identifica de forma estable ventana, zona y slot de salida, por ejemplo `zone:<zone_id>/window:<start>/<end>/slot:<n>`.

### 7.2 Contexto

- `incident_id`: UUID v4 obligatorio.
- `deployment_id`: UUID v4 obligatorio excepto en el alta inicial del incidente.
- `zone_id`: ausente cuando no aplica; nunca `null` por conveniencia.
- `source_node_id`: identificador efímero por incidente cuando exista nodo.

### 7.3 Fuente, arranque y secuencia

- `origin`: `external`, `adapter`, `core` u `operator`. Replay conserva el origin original y se registra en el receipt, no muta el evento.
- `source_event_id`: obligatorio para `external`, `adapter` y `operator`; ausente para raíces internas sin fuente externa.
- `boot_id`: UUID v4 nuevo por arranque, persistido antes del primer evento.
- `session_id`: UUID v4 de la sesión lógica.
- `sequence`: entero entre 0 y 2^63-1, monotónico dentro de `(source_node_id, boot_id)`.

Si la fuente no ofrece ID, el adapter construirá `source_event_id` a partir del hash del fixture/frame y su offset estable. La receta concreta pertenece al contrato del adapter y se registra en provenance.

Para eventos adaptados, `idempotency_id` será el SHA-256 del JCS de:

```json
{
  "source_namespace": "urn:openbrec:adapter:kismet",
  "source_event_id": "urn:sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "boot_id": "123e4567-e89b-42d3-a456-426614174000",
  "sequence": 0,
  "schema_ref": "https://openbrec.org/schemas/core/observation/1.0.0"
}
```

Para eventos derivados será el SHA-256 del JCS de engine, versión, hash de configuración, `event_type`, `causation_event_ids` ordenados y `derivation_key`.

Después de calcular `idempotency_id`, todo `event_id` será:

```text
UUIDv5(NAMESPACE_URL, "https://openbrec.org/event/" + idempotency_id)
```

`NAMESPACE_URL` será el namespace UUID estándar `6ba7b811-9dad-11d1-80b4-00c04fd430c8`. UUID v5 se usa aquí sólo como identificador determinístico, no como función de seguridad; la integridad depende de SHA-256 y los receipts. De esta forma un mismo input/configuración produce IDs idénticos sin depender de aleatoriedad del host. Dos outputs del mismo tipo y causas deben tener `derivation_key` distinto o el replay falla por colisión.

### 7.4 Tiempo

- `captured_at`: tiempo atribuido al evento por la fuente.
- `received_at`: tiempo de ingreso a la frontera OpenBREC.
- `clock_uncertainty_ms`: entero no negativo.
- `clock_source`: enum registrado.

Los timestamps usarán UTC RFC 3339 con exactamente seis dígitos fraccionarios y `Z`. El schema rechazará offsets, precisión variable, leap seconds no representables, fecha imposible y timestamps sin zona.

### 7.5 Provenance

`provenance` será un objeto cerrado con:

- nombre y versión del adapter o engine;
- commit o digest del artefacto ejecutado;
- firmware y hardware cuando existan;
- hashes de modelo, calibración y configuración cuando apliquen;
- capacidades presentes y ausentes;
- limitaciones declaradas;
- referencia al receipt upstream cuando exista.

Ausencia significa “no aplica/no fue aportado”. `null` sólo se acepta en un campo cuyo schema declare “intentado pero desconocido”.

### 7.6 Política y payload

- `handling_policy`: referencia exacta al perfil de tratamiento activo.
- `retention_policy_id`: ID versionado.
- `privacy_flags`: flags cerrados y definidos por schema.
- `payload`: debe validar exclusivamente contra `schema_ref`.

El envelope completo y el payload tendrán `additionalProperties: false`. Extensiones sólo vivirán dentro de `extensions`, con claves URI/namespace y schema registrado.

## 8. Payloads core

### 8.1 Ciclo operacional

- `IncidentEvent`: alta, activación, cambio de perfil, cierre y reapertura autorizada.
- `DeploymentEvent`: creación, activación, degradación y cierre de deployment.
- `ZoneEvent`: definición/versionado de zona y geometría.
- `NodeEvent`: alta, sesión, salud, degradación y baja.
- `CapabilityManifest`: capacidades y nivel de evidencia por nodo.
- `HealthStatus`: salud, reloj, energía resumida y capacidades ausentes.

Estos payloads no incorporarán protocolos o campos específicos de un addon.

### 8.2 Observation

`Observation` representa una medición normalizada, no una inferencia. Incluirá:

- `observation_id`;
- sensor y `sensor_type` registrado;
- zona/geometría cuando existan;
- `measurements` discriminadas por tipo;
- calidad e incertidumbre;
- cobertura observada;
- sensores/capacidades ausentes;
- referencia de calibración;
- limitaciones.

Cada medición será un objeto cerrado con `metric`, `value`, `unit`, `uncertainty`, `quality` y `method`. Las unidades usarán UCUM. Los rangos, escala y `multipleOf` se definirán por métrica. NaN e Infinity están prohibidos.

`Observation` nunca declara presencia, ausencia, identidad ni diagnóstico. `no_event_detected` sólo puede describir la salida del sensor dentro de una ventana y cobertura explícitas; no significa ausencia de persona.

### 8.3 Evidence

`Evidence` sólo puede ser emitido por un Evidence Engine registrado. Incluirá:

- `evidence_id` y regla/engine versionado;
- observaciones fuente;
- hipótesis acotada apoyada;
- afirmaciones explícitamente no respaldadas;
- zona, ventana y cobertura;
- confianza e incertidumbre;
- validez y expiración;
- fuentes correlacionadas;
- limitaciones y explicación determinística.

Un `Evidence` sin observaciones fuente válidas o producido por un adapter será rechazado.

### 8.4 FusionResult

`FusionResult` sólo puede ser emitido por un Fusion Engine registrado. Incluirá:

- `result_id` y engine/configuración versionados;
- evidencias de apoyo y contradicción;
- zona, ventana y cobertura;
- estado, confianza y conflict score;
- abstención y motivos;
- sensores/capacidades ausentes;
- explicación determinística;
- validez y expiración.

Silencio, pérdida de nodo o cobertura insuficiente incrementarán incertidumbre o forzarán abstención; nunca producirán una inferencia negativa de víctima.

### 8.5 Operación y auditoría

- `OperatorAnnotation`: anotación humana, actor/rol, motivo, alcance y firma/referencia de autenticación.
- `AuditEvent`: acción, actor, objeto, resultado, política y referencias; append-only.
- `ValidationFailure`: errores de validación, destino de tratamiento y hashes.
- `PreservationRecord`: material sellado, propósito life-safety, custodia, TTL y acceso.

## 9. Versionado y compatibilidad

Los `$id` canónicos tendrán forma:

```text
https://openbrec.org/schemas/core/<schema-name>/<semver>
```

Reglas:

- Un `$id` aceptado es inmutable byte por byte. Cambiar su SHA-256 falla el gate.
- Patch sólo modifica documentación fuera del schema publicado o crea un `$id` nuevo sin cambiar instancias válidas.
- Minor crea un `$id` nuevo y el consumidor actualizado debe seguir aceptando el `$id` anterior y proyectar sus payloads sin pérdida a la interfaz común.
- Major permite cambios incompatibles, exige coexistencia y una declaración de migración.
- Agregar enum values no se presume compatible con consumidores exhaustivos.
- Un producer no emite una versión nueva hasta que los consumidores del deployment la declaren.
- Cada evento conserva `schema_ref` exacto. Los rangos se resuelven a IDs exactos en el preflight.
- Schemas retirados siguen disponibles para replay mientras existan bundles bajo retención.

La compatibilidad minor no significa sustituir el `schema_ref` de un evento histórico. El catálogo conserva ambos schemas exactos; los fixtures del payload anterior también deben validar contra el payload minor nuevo cuando se excluye el dispatch del envelope.

La compatibilidad minor se demuestra con:

1. diff estructural dentro de una allowlist conservadora;
2. todos los fixtures válidos históricos contra el schema nuevo;
3. fixtures negativos de las restricciones preservadas;
4. generación Pydantic/TypeScript sin pérdida de discriminadores;
5. declaración humana de dirección de compatibilidad.

Si una herramienta no puede demostrar compatibilidad, el cambio se trata como major.

## 10. Generación de modelos

JSON Schema será la única fuente. Se usarán como herramientas iniciales, fijadas en lockfiles:

- `datamodel-code-generator` para Pydantic v2 dirigido a Python 3.12;
- `json-schema-to-typescript` para declaraciones TypeScript.

La selección podrá cambiar mediante ADR si otra herramienta conserva mejor Draft 2020-12, pero el output no podrá cambiar sin revisión contractual.

Reglas de generación:

- sólo `$ref` locales; acceso de red deshabilitado;
- versiones, opciones, locale y formatter fijados;
- sin timestamps ni rutas absolutas en archivos generados;
- Pydantic con coerción deshabilitada para ingress contractual;
- TypeScript sin `any` implícito y con unions discriminadas;
- archivos generados commiteados y marcados “do not edit”;
- `contracts-gen --check` genera en un directorio temporal y exige diff vacío.

Pydantic y TypeScript no expresan todos los constraints de JSON Schema. La validación normativa siempre ejecutará Draft 2020-12 y formatos custom antes de construir modelos. Los fixtures válidos deberán validar por schema, construir el modelo Pydantic y satisfacer los tipos TypeScript. Los fixtures inválidos deben ser rechazados por el schema fuente antes de llegar a cualquier modelo; no se exigirá que TypeScript actúe como validador runtime.

## 11. Canonicalización numérica y temporal

La canonicalización usará RFC 8785 JCS sobre I-JSON y UTF-8. SHA-256 se expresará en hexadecimal minúsculo.

El parser normativo preservará números decimales antes del cálculo. El engine usará `Decimal`, escala declarada por métrica y redondeo half-even. Antes de serializar, todo resultado deberá:

- respetar rango y `multipleOf` del schema;
- ser representable dentro de las restricciones I-JSON;
- pasar vectores de conformidad JCS;
- rechazar NaN, Infinity, overflow y pérdida de escala no autorizada.

TypeScript no será engine autoritativo de replay. Los timestamps se comparan como instantes UTC ya validados, no como strings de locale.

## 12. Replay de adapter

El replay de adapter demuestra:

```text
fixture crudo o sanitizado
  + adapter/version/configuración
  + catálogo contractual
  → DomainEvents normalizados
  + AdapterReplayReceipt
```

El bundle incluirá:

- manifest versionado;
- fixture y SHA-256 de bytes;
- clasificación/retención del fixture;
- adapter, commit/digest y configuración;
- schema IDs exactos permitidos;
- reloj lógico y timezone/locale neutrales;
- outputs esperados o hash esperado;
- capacidades ausentes y limitaciones.

El adapter no puede emitir Evidence/FusionResult. Un fixture que contiene material sensible debe ser sintético, sanitizado o estar sellado bajo `life_safety_preservation`; nunca se incorpora accidentalmente al repositorio.

`AdapterReplayReceipt` registrará input hash, adapter hash, contract set, eventos producidos, errores, política aplicada y `normalized_events_sha256`.

## 13. Replay del core

El replay del core demuestra:

```text
DomainEvents válidos
  + Evidence/Fusion Engine versionados
  + configuración
  → Evidence + FusionResult
  + CoreReplayReceipt
```

Antes de procesar:

1. validar catálogo, envelope y payload;
2. verificar hashes del bundle;
3. rechazar schemas no registrados;
4. deduplicar eventos idénticos por `idempotency_id`;
5. fallar si un mismo `idempotency_id` tiene contenido diferente;
6. ordenar inputs por `(captured_at, source_node_id, boot_id, sequence, event_id)`.

Los outputs, que también son `DomainEvent`, se ordenarán por `(captured_at, event_type, event_id)`.

En eventos derivados, `captured_at` será el fin de ventana lógico declarado por la regla y `received_at` será el máximo `received_at` de sus causas. Ninguno puede usar el reloj del runner. El tiempo real de procesamiento vive sólo en `AuditEvent` y en metadata no determinística del receipt.

El material determinístico hasheado será:

```json
{
  "replay_material_schema_ref": "https://openbrec.org/schemas/core/core-replay-material/1.0.0",
  "contract_set_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "upstream_receipt_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "engine": {
    "name": "openbrec-core-replay",
    "version": "1.0.0",
    "artifact_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
    "configuration_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "input_events": [],
  "outputs": []
}
```

`result_sha256` será SHA-256 del JCS de ese objeto. Explicaciones, limitaciones, abstenciones y sensores ausentes forman parte de `outputs` y del hash.

`receipt_generated_at`, duración, hostname, rutas y metadata del runner quedan fuera del material determinístico y sólo viven en el receipt operacional.

El engine M0 no consulta red, reloj del host ni aleatoriedad. Una capacidad futura aleatoria deberá fijar seed y algoritmo en el bundle.

## 14. Fallos, revisión y preservación

Nada se descarta, corrige o reintenta silenciosamente. Cada unidad de ingreso, identificada por hash e índice/offset, recibe exactamente una disposición primaria. Un artefacto crudo preservado y el `DomainEvent` normalizado que deriva de él son unidades vinculadas pero distintas.

### 14.1 AcceptedEventLog

Eventos válidos. Append-only, orden lógico, hash y política de retención.

### 14.2 ReviewQuarantine

Objetos inválidos cuya retención está permitida. Conserva bytes originales, representación parseada si existe, errores completos, schema esperado, hashes, fuente, política, responsable y estado de revisión. Se cifra localmente y todo acceso genera `AuditEvent`.

### 14.3 EvidenceVault

`routine_minimized` será el default de laboratorio y contextos no operacionales. En un deployment BREC de campo, `life_safety_preservation` será el default y deberá quedar confirmado explícitamente al abrir el incidente. Si una restricción aplicable obliga a iniciar con `routine_minimized`, el sistema permitirá activar preservación mediante break-glass autorizado.

Si existe duda razonable de que un objeto puede ayudar a localizar, contactar o asistir a una persona, se preserva sellado en vez de destruirse. El registro exige:

- propósito y motivo de relevancia life-safety;
- incidente, fuente y ventana;
- hash, tamaño y clasificación;
- cifrado con clave del incidente;
- actor o regla que activó preservación;
- cadena de custodia y accesos;
- `retention_until` obligatorio;
- borrado verificable y receipt al vencer.

El TTL se fija al abrir el incidente. El default será cierre del incidente más siete días; una extensión exige autorización firmada y motivo. El vault no habilita vigilancia general ni acceso irrestricto.

Esta especificación fija el contrato y los gates del vault, no el algoritmo de cifrado at-rest ni la custodia de su clave. Esas decisiones pertenecen al threat model transversal y a `openbrec-radio-security-regulation-design`. Hasta aprobarlas, una implementación de vault sólo podrá declararse `unverified` y ningún perfil de campo podrá pasar el gate.

### 14.4 RejectionLedger

Para credenciales, secretos o contenido claramente ajeno al rescate cuya persistencia en claro no es necesaria, se conserva sólo:

- hash, tamaño y timestamp;
- fuente efímera;
- regla y motivo;
- clasificación;
- destino/destrucción;
- receipt y auditoría.

La prioridad es:

```text
protección de vida > preservación de evidencia operacional > privacidad y minimización
```

La prioridad no elimina necesidad, proporcionalidad, control de acceso ni revisión posterior.

## 15. Semántica de fallo en replay y operación

En replay:

- cualquier input inválido aborta outputs derivados;
- no se publica resultado parcial como válido;
- el bundle permitido y los errores quedan revisables;
- se genera un receipt fallido hasheado;
- un fallo nunca se convierte en abstención silenciosa.

En operación:

- el evento inválido no ingresa al `AcceptedEventLog`;
- se enruta a quarantine, vault o ledger según política;
- se emite `ValidationFailure` y `AuditEvent`;
- los engines continúan sólo con eventos válidos y declaran la fuente ausente;
- la pérdida de una fuente degrada cobertura/confianza sin afirmar ausencia.

## 16. Gates y comandos contractuales

La interfaz objetivo será un verificador único:

```text
python -m openbrec.verify <gate> [opciones]
```

Gates:

| Gate | Responsabilidad | Evidencia mínima |
|---|---|---|
| `bundle-structure` | estructura histórica | receipt que aclara alcance estructural |
| `schema` | metaschema, formatos, refs, catálogo | catálogo y reporte por schema |
| `fixtures` | casos positivos/negativos | matriz schema-fixture |
| `schema-compat` | inmutabilidad y SemVer | diff, fixtures históricos y decisión |
| `contracts-gen` | outputs reproducibles | hashes y diff vacío |
| `adapter-replay` | fixture a eventos | AdapterReplayReceipt |
| `core-replay` | eventos a resultados | CoreReplayReceipt |
| `determinism` | estabilidad de hash | matriz de corridas |
| `review-quarantine` | cero descarte silencioso | reconciliación de conteos/destinos |
| `life-safety-preservation` | vault y break-glass | acceso, TTL, auditoría y borrado |
| `privacy` | minimización fuera de emergencia | reporte de contenido/identificadores |
| `security` | tamper/fail-closed | fixtures manipulados y resultados |

Cada ejecución producirá un receipt con:

- gate y versión;
- git SHA y estado dirty;
- runtime y lockfile hashes;
- comando/argumentos normalizados;
- inputs y artefactos con hashes;
- resultado, errores y warnings;
- inicio/fin operacional;
- responsable lógico del gate.

Los receipts de CI se publican como artefactos; no se inventan ni se reemplazan con texto manual.

## 17. Responsables y aprobaciones

Los roles, aunque una persona pueda cubrir más de uno, serán:

- `contract-maintainer`: catálogo, schemas, fixtures y generación.
- `core-replay-maintainer`: engine, canonicalización y receipts.
- `privacy-safety-reviewer`: handling profiles, vault y rejection ledger.
- `release-reviewer`: compatibilidad y aceptación de versiones.

Requieren revisión `privacy-safety-reviewer`:

- nuevos campos sensibles;
- cambios de retención;
- activación automática de preservación;
- material crudo nuevo;
- cambios en criterios de relevancia life-safety.

Requieren revisión `release-reviewer` los nuevos minor/major y cualquier excepción al gate de compatibilidad.

## 18. Matriz mínima de pruebas

Cada schema tendrá al menos:

- instancia mínima válida;
- instancia completa válida;
- required ausente;
- campo desconocido;
- tipo/formato/rango inválido;
- enum desconocido;
- `null` no permitido;
- timestamp no canónico;
- referencia o versión desconocida.

Replay cubrirá:

- inputs ya ordenados y deliberadamente desordenados;
- duplicado idéntico;
- colisión de idempotencia con contenido diferente;
- secuencia repetida o regresiva;
- reloj incierto y eventos tardíos;
- sensor/capacidad ausente;
- pérdida de fuente;
- fixture corrupto y hash manipulado;
- configuración distinta;
- explicación/limitación diferente;
- locale, timezone y orden de archivos distintos;
- quarantine, vault, ledger y borrado con receipt.

## 19. Criterios de aceptación

La especificación se considera implementada sólo cuando:

1. La familia `/schemas/core/<schema-name>/<semver>` valida íntegramente y todos sus `$id` son únicos.
2. Los schemas legacy mantienen exactamente sus hashes iniciales.
3. Cada schema canónico tiene fixtures positivos y negativos.
4. Los modelos Pydantic y TypeScript commiteados se regeneran sin diff.
5. Fixtures válidos pasan el schema y ambos consumidores generados; fixtures inválidos fallan en el schema antes de construir modelos.
6. Diez ejecuciones limpias del mismo bundle producen el mismo `result_sha256`.
7. Cambiar orden de archivos, locale o timezone no cambia el hash.
8. Duplicados, reloj incierto, eventos tardíos y fuentes ausentes son determinísticos.
9. Colisión de idempotencia, schema desconocido, hash corrupto o input inválido no produce evidencia parcial.
10. Todo input se reconcilia exactamente con accepted log, quarantine, vault o ledger.
11. `life_safety_preservation` demuestra sellado, acceso auditado, TTL, extensión autorizada y borrado con receipt.
12. Fuera de preservación autorizada no se persisten credenciales, secretos, payloads crudos de paquetes/sensores o identificadores directos en claro.
13. Pérdida o silencio de fuente sólo degrada cobertura/confianza o produce abstención.
14. Cada gate produce un receipt verificable con el git SHA real.

Pasar `python3 scripts/validate_bundle.py` no satisface estos criterios; sólo acredita estructura histórica.

## 20. Riesgos residuales

- Generadores pueden perder constraints que sí expresa JSON Schema; por eso no son autoridad.
- Compatibilidad semántica completa no puede inferirse sólo por diff; se mantiene revisión humana conservadora.
- JCS estabiliza serialización, no algoritmos numéricos; se exigen Decimal, escala y vectores.
- Preservar información potencialmente vital aumenta impacto de acceso indebido; el vault requiere cifrado y custodia.
- Clasificar relevancia life-safety puede producir sobre-retención; se exige revisión y borrado post-incidente.
- Los schemas legacy pueden haber sido consumidos externamente; no se afirmará compatibilidad sin evidencia.
- Esta especificación no hace ejecutable M0 por sí sola.

## 21. Fuentes primarias

- JSON Schema Draft 2020-12 Core: https://json-schema.org/draft/2020-12/json-schema-core
- JSON Schema Draft 2020-12 Validation: https://json-schema.org/draft/2020-12/json-schema-validation
- RFC 8785, JSON Canonicalization Scheme: https://www.rfc-editor.org/rfc/rfc8785
- RFC 3339, timestamps: https://www.rfc-editor.org/rfc/rfc3339
- RFC 9562, UUIDs: https://www.rfc-editor.org/rfc/rfc9562
- UCUM: https://ucum.org/ucum
- Semantic Versioning: https://semver.org/
- datamodel-code-generator: https://github.com/koxudaxi/datamodel-code-generator
- json-schema-to-typescript: https://github.com/bcherny/json-schema-to-typescript

## 22. Siguiente gate documental

Tras aprobar este documento no se escribirá todavía el plan conjunto. Se continuará con `openbrec-radio-security-regulation-design`, manteniendo esta especificación como autoridad para envelopes, catálogo, receipts y replay.
