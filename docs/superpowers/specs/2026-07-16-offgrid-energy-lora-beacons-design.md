# Addons de energía off-grid, comunicaciones LoRa y beacons para OpenBREC RF

- Estado: cuatro especificaciones hijas aprobadas; matriz de decisión en revisión; planificación bloqueada por M0
- Fecha inicial: 2026-07-16
- Revisión incorporada: 2026-07-17
- Perfil regulatorio inicial: Uruguay
- Alcance: visión padre para contratos P0, banco P1 y validación controlada P2

## 1. Estado y condición de avance

OpenBREC RF es hoy un bundle de diseño TRL 2–3, no una plataforma operacional ejecutable. El comando `python3 scripts/validate_bundle.py` demuestra únicamente que el bundle es estructuralmente válido. No prueba contratos, runtime, replay, privacidad operacional ni hardware.

Esta especificación define una dirección arquitectónica. No autoriza todavía un plan de implementación P0 off-grid.

Enmienda 2026-07-17: `2026-07-17-openbrec-radio-security-regulation-design.md` reemplaza la política `blocked_unverified` de esta visión por los modos `receive_only`, `conducted_only`, `jurisdiction_validated` y `emergency_assumed_risk`. También agrega federación multi-equipo con autonomía recursiva. Esa especificación hija es la autoridad en radio, regulación, seguridad y federación; el texto histórico incompatible de esta visión no debe implementarse.

Revisión multi-bearer 2026-07-17: `docs/research/2026-07-17-offgrid-communications-state-of-art.md` corrige y amplía la comparación de transportes. Meshtastic, MeshCore y Reticulum/RNode se evalúan por perfiles distintos; ninguno constituye por sí solo la red OpenBREC.

Enmienda energética 2026-07-17: `2026-07-17-openbrec-energy-design.md` es la autoridad para cargas, fronteras de medición, dimensionamiento, FSM, brownout, solar y ensayos. La reserva de 72 horas se demuestra sobre la cadena completa de servicios críticos, sin contar generación externa; cada componente aporta autonomía propia o una ruta de recarga/reemplazo ensayada.

Enmienda beacons/UX 2026-07-17: `2026-07-17-openbrec-beacons-human-ux-design.md` es la autoridad para sensores acústicos/PIR/térmicos, captura controlada, revisión, terminales, privacidad y accesibilidad. Prioridad y confianza son dimensiones separadas; ningún sensor o silencio produce confirmación o ausencia.

Antes de planificar o implementar estos addons deben cumplirse dos condiciones:

1. Terminar M0 real: servicios mínimos, Compose construible, startup offline, contratos generados, simulador y replay determinístico.
2. Aprobar cuatro especificaciones hijas: contratos/replay, radio/seguridad/regulación, energía y beacons/UX.

El trabajo documental de esas especificaciones puede avanzar mientras se completa M0. Su implementación no.

## 2. Autoridad y gobernanza

La precedencia dentro del repositorio será:

1. `AGENTS.md` para safety, privacidad y red lines.
2. ADRs aceptados para decisiones irreversibles o transversales.
3. Especificaciones aprobadas para comportamiento y criterios de aceptación.
4. JSON Schema Draft 2020-12 para contratos de datos normativos.
5. `DELIVERY_BOARD.md` para secuencia y estado.
6. Diseño técnico y roadmap como contexto no normativo cuando exista conflicto con una autoridad superior.

ADR-0001 deberá formalizar esta precedencia, el alcance del core y las red lines. Cada gate tendrá responsable, comando reproducible y artefacto de evidencia asociado.

## 3. Objetivos

- Mantener un core pequeño e independiente del hardware.
- Soportar energía híbrida con 72 horas de reserva reproducible.
- Usar LoRaWAN privado para telemetría de componentes.
- Usar LoRa P2P/mesh separado para texto breve, estado, SOS y ubicación.
- Adoptar un portafolio opcional, version-pinned y reemplazable; Meshtastic prioriza movilidad espontánea, MeshCore infraestructura planificada y Reticulum gateways heterogéneos.
- Definir `BeaconNode` como sensor, relay o ambos.
- Permitir construir diseños abiertos o reutilizar hardware compatible.
- Fallar cerrado para elevar confianza, roles, aceptación SOS o publicación sensible; preservar y mostrar posible distress aunque no pueda autenticarse.

## 4. Fuera de alcance

- Voz o archivos generales por LoRa.
- Escucha remota continua o reconocimiento de identidad.
- Presentar SOS como servicio certificado o con entrega garantizada.
- Permitir que la red humana escriba hechos OpenBREC.
- Exigir Meshtastic, un chipset o un fabricante.
- Declarar autonomía perpetua sin balance medido.
- Habilitar TX radiado sin un perfil explícito, acotado, auditable y con kill switch.
- Modificar prohibiciones sobre radio ofensiva, jamming, interferencia, emulación celular o control UAS.

## 5. Arquitectura y dependencias

```text
packages/
  contracts/
addons/
  solar-power/
  lora-telemetry/
  human-mesh/
  beacon-node/
adapters/
  meshtastic/
  lorawan/
hardware/
  reference-designs/
fixtures/
  replay/
```

La dependencia será unidireccional:

```text
contratos del core <- addons <- adapters y hardware
```

El core no importará addons, SDK de fabricante ni protocolos externos. Un addon podrá extraerse a otro repositorio sólo cuando tenga contrato estable y release independiente.

## 6. Planos de red

### 6.1 Plano máquina

LoRaWAN privado con network server local transportará telemetría compacta, salud, energía, observaciones y recibos de store-and-forward. No dependerá de nube. La caída de LoRaWAN no detendrá sensing local ni comunicación humana.

### 6.2 Plano humano

LoRa P2P/mesh transportará texto breve, estados, SOS y ubicación. Meshtastic será referencia P1 a través de BLE, USB/serial, TCP o un bridge MQTT privado.

Meshtastic será tratado como transporte no confiable para autenticidad de aplicación. Sus Node IDs, campos `from`, acuses y estados no serán identidad ni evidencia suficiente. El adapter sólo aceptará como `HumanMessage` válido un payload OpenBREC cuya firma, identidad por incidente, TTL y secuencia hayan sido verificadas.

El broker público de Meshtastic, claves predeterminadas y root topics compartidos están prohibidos en perfiles operativos.

### 6.3 Aislamiento

Los planos podrán compartir gabinete, energía o gateway sólo después de validar coexistencia. Mantendrán claves, enrolamiento, colas, prioridades, métricas, auditoría, autorización y payloads separados.

La red humana no publicará observaciones, evidencias ni hechos. Un servicio revisado podrá convertir un mensaje autorizado en anotación de operador.

## 7. Usuarios y terminales

Se validarán:

1. Rescatistas y operadores con teléfono/tablet y módulo LoRa por BLE o USB.
2. Personas no preparadas con terminal entregable o estación simple con SOS/estado, display, ubicación y mensajes predefinidos.

Se documentará, sin validación inicial, una red separada para personas con dispositivos compatibles propios.

## 8. Beacon genérico y cadena de evidencia

`BeaconNode` será un rol lógico. Podrá implementar sensores, relay LoRa o ambos. El beacon P1 de referencia incluirá acústica, PIR y matriz térmica de baja resolución; los beacons de sensor único seguirán siendo válidos.

`BeaconObservation` no creará una cadena paralela. Será una especialización de `Observation` mediante schemas discriminados:

- `sensor_type: acoustic`;
- `sensor_type: pir`;
- `sensor_type: thermal`.

El flujo seguirá siendo `Observation → Evidence → FusionResult`. `EnergyStatus` y `HumanMessage` serán eventos operativos separados, no observaciones. Energía podrá modular calidad o disponibilidad mediante una regla explícita y auditable; mensajería sólo podrá convertirse en `OperatorAnnotation` mediante acción autorizada.

Cada capacidad declarará `supported`, `experimental`, `unverified` o `unavailable` y reportará versiones, calibración, salud, energía, reloj, sensores ausentes, limitaciones y confianza.

### 8.1 Audio

El modo predeterminado procesará ventanas continuamente en local y emitirá features compactas sin transmitir ni persistir audio crudo. El modo experimental de snippet requerirá autorización explícita, cifrado, auditoría, duración limitada, expiración y señalización cuando sea segura. La escucha o transmisión remota continua está prohibida; el procesamiento local `features_only` está permitido.

Los modelos usarán `unknown`, abstención, dataset card, model card y validación por entorno. Un sonido compatible con humano o mascota será un indicio, no un hecho.

### 8.2 PIR y térmica

PIR y térmica producirán indicios. La referencia térmica no generará imagen identificable. El silencio de cualquier sensor nunca respaldará ausencia de víctima.

## 9. Contratos normativos

JSON Schema Draft 2020-12 será la única fuente para generar Pydantic v2 y TypeScript. `additionalProperties` será `false` por defecto; extensiones permitidas vivirán bajo un objeto namespaced `extensions`.

Todos los eventos de dominio incluirán:

- `schema_version` semver;
- `event_id` e `idempotency_id`;
- `source_event_id`;
- `incident_id` y `deployment_id` cuando correspondan;
- `source_node_id` efímero;
- `boot_id` y `session_id`; `boot_id` será un valor aleatorio de 128 bits nuevo por arranque, persistido antes del primer TX;
- `sequence` entero no negativo y monotónico dentro de `boot_id`;
- `captured_at` y `received_at`;
- `clock_uncertainty_ms` no negativo;
- provenance con adapter, firmware, hardware y modelo;
- `retention_policy_id`;
- privacy flags;
- limitaciones y capacidades ausentes.

Los timestamps usarán UTC RFC 3339 con seis dígitos fraccionarios y sufijo `Z`. Ausencia significa “no medido”; `null` sólo se permitirá cuando el schema declare explícitamente “medido pero desconocido/no disponible”.

Las mediciones usarán objetos cerrados con `metric`, `value`, `unit`, `uncertainty`, `quality` y `method`. Las unidades usarán UCUM; magnitudes adimensionales usarán `1`. La incertidumbre tendrá la misma unidad que el valor.

Los schemas P0 nuevos serán:

- `energy-capability.schema.json`;
- `energy-status.schema.json`;
- `energy-budget.schema.json`;
- `human-message.schema.json`;
- `human-message-event.schema.json`;
- `beacon-capability.schema.json`;
- `beacon-observation.schema.json`;
- `transport-envelope.schema.json`;
- `replay-receipt.schema.json`.

`observation.schema.json` deberá dejar de aceptar un `measurements` arbitrario y referenciar mediciones discriminadas por sensor.

## 10. Canonicalización y replay

La canonicalización usará RFC 8785 JCS sobre I-JSON y UTF-8. El hash será SHA-256 en hexadecimal minúsculo.

Antes del hash, los eventos válidos se deduplicarán por `idempotency_id` y se ordenarán por:

```text
(captured_at, source_node_id, boot_id, sequence, event_id)
```

Los outputs se ordenarán por:

```text
(timestamp, result_type, result_id)
```

El objeto hasheado será:

```json
{
  "contract_set_sha256": "hash JCS del array de schemas ordenados por $id",
  "engine_version": "versión semver",
  "outputs": []
}
```

`receipt_generated_at`, hostname, duración, rutas y metadata del runner quedarán fuera del objeto hasheado y sólo aparecerán en `ReplayReceipt`. NaN, Infinity, claves duplicadas, Unicode inválido, timestamps no canónicos o outputs que no validen schema harán fallar el replay.

## 11. Autenticidad y ciclo de vida de mensajería

Todo `HumanMessage` y todo evento de acuse usarán firma Ed25519 según RFC 8032. La firma cubrirá:

```text
"OpenBREC-SignedEvent-v1\0" || UTF8(schema_id) || "\0" || UTF8(JCS(evento sin signature))
```

La firma se codificará base64url sin padding e incluirá `signing_key_id`. `actor_id` y `device_id` serán identidades por incidente, separadas del Node ID Meshtastic. El puesto de mando emitirá bindings firmados actor-dispositivo-clave con vigencia y rol.

El contenido humano protegido se cifrará además en la capa OpenBREC con `AEAD_AES_256_GCM` según RFC 5116. El cifrado del transporte Meshtastic será defensa en profundidad, no la frontera de confidencialidad ni autenticidad. Cada incidente y canal tendrá una clave de contenido única; canales directos y grupales no compartirán clave.

El nonce GCM de 96 bits se derivará como:

```text
first_12_bytes(SHA-256(UTF8(JCS([encryption_key_id, device_id, boot_id, sequence]))))
```

La unicidad de `boot_id` y la monotonía de `sequence` serán gates fail-closed: si el nodo no puede persistir un `boot_id` nuevo, detecta reutilización de nonce o pierde el contador, no transmitirá con esa clave. Los headers visibles autenticados como associated data serán un objeto cerrado JCS que incluirá al menos `schema_version`, `event_id`, `incident_id`, `actor_id`, `device_id`, destino o grupo, `message_type`, prioridad, `created_at`, `expires_at`, `boot_id`, `sequence`, `signing_key_id` y `encryption_key_id`. Todo header no cifrado que influya en routing, autorización o estado deberá formar parte de ese objeto.

El orden será encrypt-then-sign: primero se cifra el contenido y luego Ed25519 firma el envelope protegido completo sin `signature`, incluyendo nonce, ciphertext, tag y associated data. Fallos de descifrado, tag, firma o coherencia entre associated data y envelope se rechazarán y auditarán. Rotación, revocación y cierre de incidente eliminarán la capacidad futura de cifrar con la clave anterior, sin reescribir el log histórico.

El commissioning incluirá enrolamiento presencial, verificación del binding, entrega separada de claves de firma y contenido, y pruebas de cifrado/firma. Existirán revocación, terminal perdido/robado, lista local de claves revocadas, rekey y cierre de incidente. Un mensaje con firma inválida, clave revocada, secuencia repetida, TTL vencido o binding ausente será rechazado y auditado.

El MQTT humano usará root topic:

```text
openbrec/{incident_id}/human-mesh/{direction}/{device_id}
```

Mosquitto aplicará ACL por incidente y dispositivo, `retain=false`, autenticación local y topics allowlisted. El adapter no replicará NodeInfo crudo; transformará Node IDs a HMAC por incidente y no persistirá el identificador de fabricante.

## 12. SOS como log append-only

No se recibirá ni persistirá un campo de “estado SOS” confiando en el transporte. El estado se derivará determinísticamente de eventos append-only firmados:

- `sos.created` — terminal originador;
- `sos.queued` — cola local;
- `transport.transmitted` — adapter local, evidencia de intento;
- `transport.relay_observed` — evidencia de relay, no de entrega;
- `gateway.received` — recibo firmado por gateway;
- `operator.seen` — actor humano firmado;
- `operator.accepted` — actor humano asume gestión, firmado;
- `sos.cancel_requested` — originador o actor autorizado;
- `sos.expired` — TTL agotado;
- `sos.failed` — política de reintentos agotada o error terminal.

`gateway.received` es recepción técnica; `operator.seen` es lectura; `operator.accepted` es aceptación operativa. Ninguno implica rescate ni resolución.

`operator.accepted` sólo será derivable cuando exista, para el mismo `HumanMessage`, un `gateway.received` válido, un `operator.seen` válido y una firma de un actor enrolado con rol autorizado. Cualquier `operator.accepted` que no cumpla esas precondiciones será una confirmación falsa y hará fallar el gate de seguridad.

Duplicados se absorben por idempotencia. Un mensaje tardío se registra sin retroceder un estado terminal. Reinicios recuperan el log persistido, generan un `boot_id` nuevo, reinician su secuencia y no recrean eventos ya confirmados. Cancelar no borra: agrega un evento.

## 13. Seguridad LoRaWAN

Perfiles P1b/P2 usarán OTAA con claves raíz únicas por dispositivo. ABP quedará restringido a simulación o banco conducted explícitamente marcado `unverified` y no podrá habilitar un perfil de campo.

Claves raíz se almacenarán en secure element cuando el hardware lo soporte o en almacenamiento cifrado con capacidad declarada `unverified` hasta validación. JoinNonce/DevNonce y frame counters serán monotónicos y persistidos; su reutilización bloqueará TX y generará auditoría.

El ciclo de vida incluirá alta, join, rotación, revocación, dispositivo perdido, rejoin y cierre de incidente. Telemetría será unconfirmed por defecto. Confirmed downlinks se reservarán para operaciones justificadas y tendrán presupuesto de airtime explícito.

## 14. Regulación Uruguay y fases P1

Uruguay no figura actualmente en la tabla oficial de regiones Meshtastic; no se aceptará ningún preset por presunción. El artefacto `regulatory-profile-uy.yaml` comenzará con:

```yaml
mode: receive_only
jurisdiction_status: unreviewed
tx_policy: explicit_operator_action
```

Los modos normativos son `receive_only`, `conducted_only`, `jurisdiction_validated` y `emergency_assumed_risk`. El último no declara cumplimiento: registra una decisión BREC extraordinaria con frecuencia/rango exacto, potencia, EIRP, antena, airtime, geografía, evidencia, actores, TTL, monitoreo, stop conditions y kill switch. La especificación hija define double authorization y break-glass acotado.

P1 se divide:

- `P1a`: simulación RF, replay, interfaces cableadas, dummy load, conducted testing o recinto de atenuación medido; sin radiación exterior.
- `P1b`: TX radiado sólo con `jurisdiction_validated` o una activación `emergency_assumed_risk`, además de safety review y perfil de coexistencia.

Jamming deliberado, TX continuo, suplantación de servicios y SDR ofensivo siguen prohibidos sin excepción. Interferencia perjudicial observada obliga a ceder o detener.

## 15. Coexistencia RF

El aislamiento criptográfico no implica coexistencia RF. Antes de P1b se aprobará `rf-coexistence-profile.yaml` con:

- plan de canales/frecuencias por plano;
- radios y antenas utilizados;
- separación física, filtrado y aislamiento medido;
- airtime budget por plano y prioridad;
- máximo de nodos, payload, hops y mensajes/minuto;
- presupuesto de downlinks confirmados;
- política de fragmentación;
- comportamiento ante congestión;
- ensayos near-far, co-site y pérdida de relay.

La referencia usará radios y antenas separados. Compartir un transceiver será `unsupported` hasta validación. Telemetría normal no fragmentará. Un SOS deberá caber en un único frame para cada data rate habilitado; si no cabe, ese perfil/data rate permanecerá deshabilitado. Mensajes humanos no críticos podrán fragmentarse sólo con límite de tamaño, TTL y cuota documentados.

## 16. Energía reproducible

La arquitectura será híbrida: LiFePO4 y generación central para gateway/red/PoE/carga; solar individual sólo para relays o beacons remotos; generadores y estaciones portátiles como soporte; batería-only sigue siendo válida.

Cada ensayo usará un `energy-load-profile.yaml` versionado con cargas críticas/degradables, potencia por estado, duty cycle, capacidad descargable medida, DoD, rutas/eficiencias, derating por temperatura, envejecimiento, margen, reserva SOS y energía de apagado.

```text
usable_Wh = measured_discharge_capacity_Wh * allowed_DoD * temperature_derating * aging_derating
required_Wh = integral_0_72h(storage_output_power_W, dt) + sos_reserve_Wh + transition_reserve_Wh + shutdown_Wh
```

El banco storage-only pasa si `usable_Wh >= required_Wh * 1.25` y las trazas demuestran continuidad de la cadena crítica durante 72 horas. Solar, red y generador se validan como extensiones separadas y no reducen esta reserva.

Umbrales iniciales con hysteresis:

- `NORMAL`: SOC ≥ 50%;
- `CONSERVE`: entra ≤ 50%, sale ≥ 55%;
- `CRITICAL`: entra ≤ 30%, sale ≥ 35%;
- `SURVIVAL`: entra ≤ 15%, sale ≥ 20%;
- `SAFE_SHUTDOWN`: inicia ≤ 8%.

El último 8% se divide en 5% reservado al terminal SOS/estado crítico y 3% al controlador de apagado. Un perfil de hardware sólo podrá cambiar umbrales mediante evidencia y manteniendo reservas equivalentes o superiores.

Tras brownout, el nodo iniciará en `SURVIVAL`, verificará almacenamiento, recuperará colas append-only, emitirá `boot.recovered` y no duplicará eventos.

## 17. Gates verificables

El job actual se renombrará conceptualmente `bundle-structure`. Cada gate será independiente:

- `schema`: metaschema completo y formatos;
- `fixtures`: instancias positivas y negativas contra schemas;
- `schema-compat`: semver y breaking changes;
- `contracts-gen`: Pydantic/TypeScript reproducibles sin diff;
- `compose-build`: todos los contextos y Dockerfiles existen y construyen;
- `offline-startup`: servicios healthy sin Internet;
- `replay`: receipt y hash determinístico;
- `privacy`: ningún audio crudo fuera de capture authorization/EvidenceVault; sin payloads o identificadores directos no autorizados;
- `security`: firmas, revocación, replay attacks, claves default y ACL;
- `secret-scan`;
- `sbom-license`;
- `container-policy`: non-root y configuración segura.

Cada ejecución producirá un receipt con git SHA, runtime, comando, resultado, artefactos y hashes. El README distinguirá explícitamente bundle estructural, M0 ejecutable y perfiles experimentales.

## 18. Validación P2 y SLOs

El escenario de referencia tendrá una versión inmutable por campaña:

- 1 gateway;
- 12 nodos LoRaWAN de componentes;
- 8 terminales humanos;
- 3 relays/beacons mesh;
- máximo 3 hops;
- telemetría: 1 frame por nodo cada 60 segundos;
- mensajería normal: 2 mensajes por minuto agregados;
- 100 SOS inyectados en 5 corridas, separados al menos 30 segundos;
- fallos: partición de backhaul de 30 minutos, pérdida de un relay y brownout de un nodo.

SLOs separados:

- SOS: al menos 99/100 con `gateway.received` válido dentro de 120 segundos; cero `operator.accepted` falsos.
- Mensajes humanos no SOS: al menos 95% recibidos dentro de 300 segundos.
- Telemetría: al menos 95% recibida dentro de 600 segundos.
- Store-and-forward: al menos 99% de eventos dentro de capacidad recuperados en 15 minutos tras restaurar enlace.

El denominador de mensajes será todo evento válido aceptado por la cola de origen antes de su TTL y dentro de la capacidad declarada. El denominador de telemetría será todo frame válido generado durante la ventana. El denominador de recuperación será todo evento confirmado como persistido antes de la partición. “Recibido” exigirá receipt válido del destino previsto; un intento de TX o relay no contará como entrega.

El reporte incluirá denominador por clase, omitidos completos, p50/p95/p99, intervalo Wilson 95%, topología, configuración RF, carga, fallos y resultados negativos. Los porcentajes serán gates del escenario, no garantías universales.

La prueba energética de 72 horas usará el mismo `energy-load-profile.yaml` y sus trazas, pero será un ensayo separado de los cinco runs de red.

## 19. Marco abierto y reutilización

Cada addon ofrecerá:

1. Diseño de referencia abierto: esquema, BoM, firmware, enclosure, montaje, calibración y mantenimiento.
2. Reutilización: adapter, versiones compatibles, limitaciones y evidencia para hardware existente.

Toda compatibilidad usará `supported`, `experimental`, `unverified` o `unavailable`. Ningún claim de fabricante será `supported` sin evidencia propia.

## 20. Descomposición obligatoria antes del plan

Esta visión padre se dividirá y aprobará en orden:

1. `openbrec-core-contracts-replay-design`: schemas, provenance, canonicalización, generación, compatibilidad y gates.
2. `openbrec-radio-security-regulation-design`: Meshtastic, LoRaWAN, identidad, SOS, MQTT, Uruguay y coexistencia.
3. `openbrec-energy-design`: cargas, dimensionamiento, FSM, brownout y ensayo 72h.
4. `openbrec-beacons-human-ux-design`: sensores, privacidad, terminales, UI y validación humana.

No se escribirá un plan P0 off-grid hasta que las cuatro estén aprobadas y M0 sea ejecutable.

## 21. Matriz posterior

La matriz inicial está documentada en `docs/decision-matrices/2026-07-17-offgrid-addons-decision-matrix.md`. La revisión de transportes que evita privilegiar una única mesh está en `docs/research/2026-07-17-offgrid-communications-state-of-art.md`. Ambas permanecen pendientes de aprobación y no modifican todavía `DELIVERY_BOARD.md`.

La matriz tendrá funcionalidad, valor BREC, evidencia, alternativa desacoplada, hardware reutilizable, diseño construible, energía, privacidad, safety, regulación, esfuerzo, dependencias, madurez, aceptación, recomendación y siguiente experimento.

Incluirá solar, generadores, almacenamiento, LoRaWAN, Meshtastic, otras mallas, terminales, beacons acústicos/PIR/térmicos, relays y transportes de mayor ancho de banda.

## 22. Riesgos residuales

- Una activación `emergency_assumed_risk` puede generar consecuencias regulatorias o interferencia y nunca equivale a autorización legal.
- Hardware, chipsets e importación pueden cambiar.
- Capacidad mesh depende de terreno, carga, antena y regulación.
- Autonomía depende de clima, sombra, envejecimiento y mantenimiento.
- Audio y térmica pueden producir privacidad y falsa confianza.
- Meshtastic/licencia deben revisarse contra la versión fijada.
- Ed25519 agrega airtime; el gate de frame único puede reducir data rates habilitados.
- Los SLOs P2 no son garantías fuera del escenario.

## 23. Fuentes primarias

- URSEC, sistemas de radiocomunicaciones: https://www.gub.uy/tramites/sistemas-radiocomunicaciones-uso-propio-autorizaciones-modificaciones-bajas
- LoRa Alliance, especificaciones: https://resources.lora-alliance.org/technical-specifications
- LoRaWAN security: https://lora-alliance.org/resource_hub/lorawan-is-secure-but-implementation-matters/
- Meshtastic hardware: https://meshtastic.org/docs/hardware/devices/
- Meshtastic regiones: https://meshtastic.org/docs/configuration/region-by-country/
- Meshtastic Client API: https://meshtastic.org/docs/development/device/client-api/
- Meshtastic Encryption: https://meshtastic.org/docs/overview/encryption/
- Meshtastic MQTT: https://meshtastic.org/docs/software/integrations/mqtt/
- Meshtastic firmware/licencia: https://github.com/meshtastic/firmware
- RFC 8785 JCS: https://www.rfc-editor.org/rfc/rfc8785
- RFC 8032 Ed25519: https://www.rfc-editor.org/rfc/rfc8032
- RFC 5116 AEAD: https://www.rfc-editor.org/rfc/rfc5116
- RFC 3339 timestamps: https://www.rfc-editor.org/rfc/rfc3339
