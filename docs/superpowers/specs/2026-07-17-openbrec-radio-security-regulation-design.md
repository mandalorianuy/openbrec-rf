# Radio, seguridad, regulación y federación de OpenBREC RF

- Estado: especificación aprobada; revisión multi-bearer pendiente de aprobación; implementación no autorizada
- Fecha: 2026-07-17
- Especificación padre: `2026-07-16-offgrid-energy-lora-beacons-design.md`
- Dependencia contractual: `2026-07-16-openbrec-core-contracts-replay-design.md`
- Alcance: planos LoRa, identidad, mensajería humana, SOS, coexistencia, regulación y federación autónoma
- Fuera de alcance: implementación, selección final de hardware, dimensionamiento energético y UX de beacons
- Revisión de estado del arte: `docs/research/2026-07-17-offgrid-communications-state-of-art.md`

## 1. Propósito y condición de avance

Esta especificación convierte la visión de comunicaciones off-grid en límites, contratos y gates verificables. Incorpora además el escenario de incidentes masivos con múltiples organizaciones, decenas de equipos y conectividad intermitente.

La jerarquía facilita coordinación, pero nunca se ubica en el camino crítico local. Cada nivel conserva capacidad de operar aislado, registrar evidencia, comunicar SOS, administrar confianza y reconciliarse después.

Este documento no autoriza TX radiado, despliegue de campo ni implementación. Las cuatro especificaciones hijas ya fueron aprobadas, pero la revisión multi-bearer y la matriz conjunta permanecen en revisión. Cualquier plan addon sigue condicionado por M0 ejecutable.

## 2. Autoridad y corrección de la especificación padre

La autoridad aplicable será, en orden:

1. `AGENTS.md` para safety, evidencia, offline-first y red lines.
2. ADR-0001 aceptado para alcance y precedencia documental.
3. Esta especificación para radio, seguridad, regulación y federación.
4. La especificación de contratos core para `DomainEvent`, preservación y replay.
5. Los JSON Schemas aceptados para forma de datos.
6. `DELIVERY_BOARD.md` para secuencia y estado.

Esta especificación reemplaza, únicamente en su dominio, las afirmaciones de la especificación padre que exigen `blocked_unverified` y bloquean todo TX radiado hasta validar Uruguay. El modelo normativo aprobado usa cuatro modos:

- `receive_only`;
- `conducted_only`;
- `jurisdiction_validated`;
- `emergency_assumed_risk`.

`emergency_assumed_risk` permite una decisión operacional explícita y acotada cuando la necesidad de proteger vida no permite esperar una validación jurisdiccional. No equivale a autorización legal, no presume una excepción regulatoria y no elimina los límites absolutos de safety.

## 3. Decisiones aprobadas

1. Se separan un plano máquina LoRaWAN privado y un plano humano multi-bearer; ningún protocolo es "la red" OpenBREC.
2. Meshtastic, MeshCore y Reticulum/RNode son adapters opcionales, version-pinned, reemplazables y no confiables para semántica o autenticidad de aplicación.
3. La autenticidad, confidencialidad y semántica SOS pertenecen a OpenBREC, no al transporte.
4. La jerarquía es `IncidentFederation → OperationalArea → ResponseCell → Deployment → Site`.
5. Cada nivel funciona sin conectividad, autorización ni quorum de su superior.
6. La federación usa al menos dos hubs redundantes y backhaul distinto de la malla LoRa local.
7. Los hubs nunca reciben las claves raíz o de contenido de una celda y nunca controlan su TX.
8. Toda información de posible peligro vital se preserva para revisión, aunque no pueda autenticarse.
9. Un SOS inválido o sin firma se presenta como `unverified_distress`; nunca se descarta ni se promueve automáticamente a SOS autenticado.
10. La vida precede a privacidad y minimización en un perfil BREC declarado, con acceso, retención y auditoría proporcionales.
11. La operación RF puede usar riesgo de emergencia explícito, con alcance, TTL, responsables, monitoreo y kill switch.
12. Jamming deliberado, TX continuo, suplantación de servicios y radio ofensiva permanecen prohibidos sin excepción.
13. Cada `ResponseCell` selecciona primary, fallbacks y carry bearer mediante un `TransportProfile` reproducible; puede operar con uno, varios o ninguno disponible.

## 4. Objetivos y no objetivos

### 4.1 Objetivos

- Texto breve, estado, SOS y ubicación sin dependencia cloud.
- Telemetría compacta y salud de componentes por LoRaWAN privado.
- Autonomía local durante particiones de al menos 24 horas y pérdida total de hubs.
- Federación eventual de resúmenes, solicitudes, handoffs y evidencia firmada.
- Reutilización de hardware compatible mediante adapters y capability manifests.
- Identidad por incidente, revocación offline y recuperación ante terminal perdido.
- Operación reproducible en simulación, banco conducted y campo bajo perfiles explícitos.
- Coexistencia medible entre radios, planos, canales y equipos próximos.
- Selección contextual entre movilidad espontánea, infraestructura planificada, backbone heterogéneo, telemetría, malla IP, sensor local y DTN.

### 4.2 No objetivos

- Garantizar entrega o rescate a partir de un SOS.
- Usar radio silence como evidencia de ausencia de personas o animales.
- Crear una PSK común para todo el desastre.
- Federar MQTT local, frames LoRaWAN o protobufs Meshtastic crudos.
- Requerir un fabricante, chipset, network server o firmware específico.
- Declarar un ganador global de mesh a partir de hops máximos, popularidad o claims del proyecto.
- Controlar vuelos, interferir señales, emular redes públicas o responder ofensivamente a jamming.
- Usar una autoridad central online, OCSP, DNS o nube en el camino crítico.
- Resolver voz, video o archivos de gran tamaño por LoRa; otros transportes podrán registrarse como addons.

## 5. Modelo jerárquico y autonomía recursiva

```text
IncidentFederation
  └─ OperationalArea
       └─ ResponseCell
            └─ Deployment
                 └─ Site
```

- `IncidentFederation` corresponde al `incident_id` canónico del core.
- `OperationalArea` agrupa coordinación geográfica u operativa.
- `ResponseCell` es la unidad mínima federable con identidad, políticas, claves, mapas y log propios.
- `Deployment` corresponde al `deployment_id` del core.
- `Site` identifica el lugar de trabajo; puede mapearse a `zone_id` o a una entidad addon si requiere más semántica.

La jerarquía se expresa mediante payloads addon registrados. No agrega campos al envelope `DomainEvent` aprobado.

### 5.1 Invariante de autonomía

Cada nivel debe poder, sin su superior:

- recibir, preservar, mostrar y retransmitir distress;
- operar sensing y fusión local;
- emitir IDs sin coordinador central;
- usar claves y bindings ya enrolados;
- enrolar un peer local bajo aprobación humana;
- consultar mapas, políticas y revocaciones cacheadas;
- aplicar kill switch y políticas locales de RF;
- registrar eventos append-only y exportar bundles firmados;
- continuar solo o establecer peering con otro nivel compatible.

Una orden superior es intención firmada, no ejecución imperativa. El receptor puede rechazarla por unsafe, incompatible, expirada o inaplicable y debe emitir la razón. La expiración, partición o caída del superior nunca deshabilita capacidades críticas locales.

## 6. Arquitectura de planos

### 6.1 Plano máquina

LoRaWAN privado transporta salud, energía, observaciones compactas y receipts de store-and-forward. El network server es local a la `ResponseCell`. La caída de LoRaWAN no detiene sensing local ni mensajería humana.

La línea base de interoperabilidad será LoRaWAN L2 TS001 1.0.4 y Regional Parameters RP002 1.0.5. La selección no constituye validación regulatoria para una jurisdicción.

### 6.2 Plano humano

El plano humano transporta texto breve, estado, SOS y ubicación mediante el bearer apropiado al perfil:

- Meshtastic para equipos móviles, topología desconocida y commissioning rápido;
- MeshCore para celdas planificadas con repeaters estratégicos y tráfico directo predominante;
- Reticulum/RNode para gateways heterogéneos, DTN o enlaces que combinan LoRa, packet radio e IP;
- Ethernet/Wi-Fi mesh, LMR u otros adapters cuando el entorno, payload o equipo disponible lo justifique.

Los tres primeros son candidatos P0/P1a de igual jerarquía experimental, no equivalentes funcionalmente. Ningún adapter puede filtrar frames, protobufs, path hashes, Node IDs o identities del transporte al core. Los perfiles y comparaciones normativas están en la revisión de estado del arte.

Un incidente masivo usa muchas redes locales por `ResponseCell`; no construye una malla LoRa única encadenando el máximo de hops del protocolo. La escala superior proviene de federar eventos con autonomía recursiva.

P1 valida este plano con rescatistas/operadores y valida el plano máquina con componentes. Queda documentada, pero fuera de la aceptación P1 inicial, la posibilidad de levantar una red separada para personas con dispositivos propios compatibles. Esa red civil tendrá canal, claves, enrolamiento, cuotas, gateway y trust policy propios; no comparte una PSK ni obtiene acceso implícito a la red operativa. Un gateway revisado podrá intercambiar únicamente los tipos mínimos autorizados, en especial distress preservable.

### 6.3 Plano de federación

El backhaul entre celdas y hubs es distinto de las redes LoRa locales. Puede usar IP terrestre, satélite, microondas, fibra/Wi-Fi táctico, enlace gateway-to-gateway o bundles físicos.

Un `federation-relay` LoRa es opcional y sólo admite resúmenes críticos bajo canal, clave, airtime y hops separados. No comparte la malla humana ni el plano máquina.

Los gateways inician túneles autenticados salientes. No exponen MQTT, network server ni administración local hacia el hub. El transporte de referencia es HTTPS batch/poll sobre TLS 1.3 con autenticación mutua; el fallback son bundles firmados y cifrados intercambiados físicamente.

Al menos dos hubs replican eventos. Un hub puede ayudar a descubrir, enrutar y visualizar, pero no es autoridad de verdad, firma de celda ni controlador de TX.

## 7. Componentes lógicos

- `LoRaWANAdapter`: valida sesión, contador, provenance y capability antes de publicar observaciones.
- `HumanMeshAdapter`: convierte payloads protegidos y verificados en eventos humanos.
- `MeshtasticAdapter`, `MeshCoreAdapter` y `ReticulumAdapter`: implementaciones sustituibles de la misma frontera humana.
- `TransportPolicyController`: selecciona primary/fallback/carry bearer con decisión reproducible y anti-loop.
- `BearerCapabilityRegistry`: registra límites medidos, energía, movilidad, regulación y support status por perfil exacto.
- `RawTransportBoundary`: contiene protobufs, Node IDs y errores del transporte fuera del core.
- `IdentityAuthority`: emite bindings por incidente y funciona offline.
- `TrustStore`: raíces, bindings, revocaciones y estado de frescura local.
- `DistressLedger`: registra eventos SOS y `unverified_distress` append-only.
- `RegulatoryController`: aplica perfil, autorizaciones, TTL y kill switch.
- `CoexistenceController`: aplica canal, airtime, prioridad y límites locales.
- `FederationGateway`: produce y consume sólo eventos federables autorizados.
- `FederationHub`: almacena, replica y distribuye eventos firmados sin claves de celda.
- `ReconciliationEngine`: une logs y emite conflictos explícitos sin sobreescribir hechos.

## 8. Familia contractual addon

Los schemas serán objetos cerrados Draft 2020-12, registrados en el catálogo addon y acompañados por fixtures válidos e inválidos:

```text
schemas/addons/radio/1.0.0/
  protected-human-message.schema.json
  distress-event.schema.json
  identity-binding.schema.json
  trust-bundle.schema.json
  revocation-list.schema.json
  federation-topology-event.schema.json
  federation-event.schema.json
  reconciliation-event.schema.json
  regulatory-profile.schema.json
  radio-override-event.schema.json
  rf-coexistence-profile.schema.json
  transport-profile.schema.json
  bearer-capability.schema.json
  transport-policy-decision.schema.json
  transport-receipt.schema.json
```

Cada payload viaja en el `DomainEvent` del core. Comparte `incident_id`, `deployment_id`, provenance, handling policy, idempotencia, canonicalización y replay; no crea una cadena de evidencia paralela.

### 8.1 `FederationTopologyEvent`

Campos normativos:

- `topology_version` y `effective_at`;
- `entity_id`, `entity_type` y `parent_entity_id` opcional;
- `cell_id`, obligatorio desde `ResponseCell` hacia abajo;
- `public_identity_ref` y `capability_refs`;
- `status`: `active`, `isolated`, `degraded`, `closed` o `unknown`;
- `valid_from`, `valid_until` y firma del actor autorizado;
- `previous_topology_event_id` cuando reemplaza una relación propia.

Un evento de topología no borra la historia. Relaciones concurrentes incompatibles quedan visibles hasta reconciliación.

### 8.2 `FederationEvent`

Campos normativos:

- `federation_event_type`: `distress_summary`, `cell_status`, `capability_offer`, `resource_request`, `resource_assignment`, `handoff_offer`, `handoff_acceptance`, `policy_intent` o `revocation_update`;
- `origin_cell_id` y `target_entity_ids`;
- `source_event_ids` ordenados y sin duplicados;
- `priority`, `created_at`, `expires_at` y `sequence`;
- `summary`, cerrado y mínimo para el tipo;
- `handling_policy_ref` y `disclosure_basis`;
- `signing_binding_id` y `signature`.

Por defecto no contiene mensajes humanos completos, audio, posiciones históricas finas, protobufs, frames ni telemetría cruda. Una excepción life-safety requiere handling policy explícita, razón, alcance, destinatario y retención.

### 8.3 Reconciliación

La convergencia usa unión append-only por `event_id`, no last-write-wins. Duplicados idénticos son idempotentes. Mismo ID con bytes distintos es incidente de integridad.

Conflictos de topología, handoff o asignación generan `ReconciliationEvent` firmado con ambos conjuntos causales. Estados de seguridad son monotónicos: una aceptación, revocación, cancelación o cierre no desaparece por recibir un evento anterior. Los conflictos permanecen visibles hasta resolución autorizada y reproducible.

## 9. Identidad, confianza y criptografía

### 9.1 Jerarquía de identidad

- Una organización puede aportar una raíz persistente, pero no es obligatoria.
- Cada `ResponseCell` crea una raíz efímera por incidente.
- Cada dispositivo crea una clave Ed25519 local; la clave privada no es exportable cuando el hardware lo permite.
- El puesto local firma un binding entre incidente, actor, dispositivo, rol, clave pública y vigencia.
- Una raíz organizacional puede certificar la raíz de celda, sin dependencia online.
- Un peer desconocido se enrola por fingerprint/QR y aprobación humana como `unverified_peer`, con derechos mínimos.

Node ID Meshtastic, DevEUI, MAC u otro identificador del fabricante nunca son identidad humana. Los IDs persistidos fuera del boundary se derivan por incidente con HMAC o se generan efímeramente.

### 9.2 Primitivas y separación de claves

- Ed25519 para firmas de aplicación.
- AES-256-GCM para contenido de grupo.
- X25519 + HKDF-SHA-256 para claves de mensajes directos.
- Una clave de grupo SOS separada más firma individual del emisor.
- mTLS y claves de sesión distintas para federación.
- Raíces LoRaWAN únicas por dispositivo.

No se promete forward secrecy para el mesh P1. Se reduce exposición mediante claves efímeras por incidente, vigencias cortas, rekey y borrado verificable.

Ningún hub conoce claves raíz LoRaWAN, claves del mesh humano, claves de contenido ni material privado de una celda. No existe PSK común del incidente.

### 9.3 Custodia y pérdida

Niveles de soporte:

- `supported`: secure element o almacenamiento hardware validado;
- `experimental`: keystore cifrado del sistema, credenciales breves y wipe probado;
- `emergency_assumed_risk`: almacenamiento software mínimo en terminal reutilizado, TTL y rekey más estrictos, riesgo visible.

La pérdida o robo revoca el binding y rota todas las claves grupales afectadas. Las revocaciones se cachean localmente. Si la caché está vencida, la celda sigue operando, marca `trust_stale` y restringe enrolamiento remoto, cambio de política y operaciones federadas sensibles; no bloquea recepción de distress.

## 10. Protección de `HumanMessage`

El contenido protegido incluye versión, incidente, celda, message ID, tipo, actor, dispositivo, destinatario/canal, timestamp, TTL, secuencia, ubicación opcional, ciphertext, algoritmo, key ID y firma.

La firma cubre el JCS de todos los campos semánticos salvo la firma. El AEAD usa un nonce único por clave y associated data que liga incidente, celda, emisor, destinatario, tipo, secuencia y TTL. Una reutilización de nonce o rollback de secuencia falla autenticación y genera evento de seguridad.

El adapter verifica, en orden:

1. límites de tamaño y versión;
2. binding y estado de revocación;
3. firma, AEAD y nonce;
4. incidente, celda, destinatario, TTL y secuencia;
5. autorización del tipo de mensaje;
6. deduplicación e idempotencia.

Sólo después publica un `HumanMessage` autenticado. El material que pueda representar peligro vital sigue la ruta de preservación descrita en la sección 12.

## 11. Portafolio de transportes, MQTT y LoRaWAN

### 11.1 Selección contextual y multi-bearer

`TransportProfile` declara misión, plano, movilidad, topología, nodos, carga, payload, latencia, energía, hardware, regulación, amenaza y backhaul. Su decisión contiene `primary_bearer`, fallbacks, carry bearer, bridges prohibidos, airtime, activation/expiry, evidencia y actor.

La selección ocurre inicialmente en commissioning. Failover automático sólo puede usar bearers previamente autorizados y debe conservar el mismo `message_id`, firma, TTL y prioridad. El receptor deduplica y conserva receipts por camino. Se prohíbe bridgear floods o frames crudos: un adapter termina su transporte y sólo un `DomainEvent` válido puede ser emitido por otro.

### 11.2 Meshtastic como transporte no confiable

Meshtastic usa managed flooding para broadcasts y, desde firmware 2.6, next-hop por salto para mensajes directos con fallback a flooding. Admite roles que no repiten y roles de infraestructura. El máximo configurable es 7 hops y el default 3; ninguna de esas cifras prueba capacidad bajo la carga OpenBREC.

La documentación oficial indica que DMs modernos incluyen PKC/firma, pero que los mensajes de canal no ofrecen integridad/autenticación fuerte del emisor y publica una clave de canal predeterminada conocida. Por ello:

- la PSK predeterminada está prohibida en operación;
- el broker público está prohibido;
- `from`, Node ID, ACK y estado de canal no prueban identidad ni entrega semántica;
- las protecciones direct-message de una versión concreta son defensa adicional, no contrato OpenBREC;
- firmware, protobuf y adapter quedan version-pinned y con SBOM/licencias.

### 11.3 MeshCore como transporte no confiable

MeshCore separa companions y repeaters. El primer mensaje directo descubre camino por flood y los siguientes usan un path explícito; los canales grupales siguen usando flood. El máximo interno de 64 hops aplica a paths de un byte y no es un claim operacional: paths mayores reducen el máximo, pueden existir colisiones de hashes y versiones antiguas pueden descartar formatos nuevos silenciosamente.

El perfil OpenBREC exige versión soportada, credenciales default reemplazadas, claves enroladas, tests de path churn/flood/legacy y overlay OpenBREC. MeshCore se evalúa para repeaters planificados; no se presume apto para todos los nodos móviles ni para escala por su hop limit.

### 11.4 Reticulum/RNode como transporte no confiable

Reticulum aporta routing cifrado sobre bearers heterogéneos, DTN/LXMF, transferencia de recursos e initiator anonymity. Su API y wire format son declarados estables, pero el proyecto se considera joven y no auditado externamente.

El forwarding general es priority-agnostic y un Link cuesta tres paquetes/297 bytes. Por ello OpenBREC prioriza y limita tráfico antes del interface, controla announces por boundary y mide overhead/goodput. No se afirma menor alcance RF por handshake: alcance y airtime se ensayan por separado con PHY/hardware equivalentes.

### 11.5 Boundary MQTT

El bridge crudo usa broker/listener y credenciales distintos del bus core. El topic local es:

```text
openbrec/{incident_id}/{cell_id}/{plane}/{direction}/{device_id}
```

El perfil de campo exige autenticación, ACL por celda/plano/dirección, TLS o aislamiento físico local documentado, `retain=false`, límites de paquete, cuotas, rate limit y dead-letter revisable. No admite acceso anónimo ni credenciales de ejemplo.

MQTT local no cruza la frontera federada. `FederationGateway` publica eventos autorizados mediante su protocolo separado; nunca reexpone topics o brokers.

### 11.6 LoRaWAN

El campo usa OTAA y claves raíz únicas por dispositivo. ABP queda restringido a simulación, dummy load o banco conducted marcado `unverified`. Deben persistirse de forma segura nonces, frame counters y estado de join para impedir rollback o reutilización después de brownout.

Uplinks normales son unconfirmed por defecto. Confirmed downlinks se presupuestan. Una degradación del network server no elimina captura o almacenamiento local.

LoRaWAN Relay TS011 puede evaluarse para extender cobertura del plano máquina entre end-device y gateway/network server. No crea mensajería humana mesh ni elimina la dependencia lógica del network server local.

## 12. SOS y distress sin descarte

El estado SOS se deriva sólo de eventos append-only:

- `sos.created`;
- `sos.queued`;
- `transport.transmitted`;
- `transport.relay_observed`;
- `gateway.received`;
- `operator.seen`;
- `operator.accepted`;
- `sos.cancelled`, `sos.expired` o `sos.failed`.

`gateway.received` es recepción técnica, `operator.seen` es lectura humana y `operator.accepted` es toma de responsabilidad operativa; ninguna garantiza rescate. `operator.accepted` requiere los dos eventos previos y firma de actor autorizado. El transporte jamás aporta directamente el estado derivado.

Federación agrega `sos.federation_escalated`, oferta de handoff y aceptación firmada por la celda destino. El handoff no reemplaza el log original y un hub no puede producir `operator.accepted` por una celda.

Un mensaje inválido, expirado, no descifrable o sin firma que parezca distress se preserva como `unverified_distress` en `EvidenceVault` o `ReviewQuarantine`, se muestra separado y requiere verificación humana. No se descarta, no se oculta y no se convierte automáticamente en mensaje autenticado. El perfil BREC `life_safety_preservation` puede preservar más datos que el perfil normal, pero exige razón, control de acceso, auditoría, revisión y cierre de retención.

## 13. Regulación y operación RF bajo riesgo

`regulatory-profile.schema.json` representa evidencia y decisiones, no asesoramiento legal. El perfil por defecto para una jurisdicción no revisada es:

```yaml
mode: receive_only
jurisdiction_status: unreviewed
tx_policy: explicit_operator_action
```

Uruguay no figura en la tabla de regiones por país publicada por Meshtastic al redactar esta especificación. URSEC mantiene procedimientos y normativa para sistemas de radiocomunicaciones y radioaficionados. No se encontró en esas fuentes una autorización general que permita asumir cualquier frecuencia durante un desastre. Esa incertidumbre debe quedar visible.

### 13.1 Modos

- `receive_only`: no TX; captura y simulación permitidas.
- `conducted_only`: TX confinado en dummy load, cable o recinto medido; no radiación exterior intencional.
- `jurisdiction_validated`: TX conforme a perfil revisado, evidencia, límites y vigencia definidos.
- `emergency_assumed_risk`: TX extraordinario por necesidad life-safety, sin afirmar validación legal.

### 13.2 Perfil de emergencia

No existe un wildcard “usar cualquier rango”. Cada activación debe fijar:

- frecuencia o rango exacto, modulación y ancho de banda;
- potencia conducida, EIRP, antena y orientación;
- airtime/duty cycle, canales y prioridad;
- geografía y equipos afectados;
- actor responsable, razón y evidencia disponible;
- inicio, expiración y condiciones de renovación;
- stop conditions, scan y monitoreo de interferencia.

La activación normal requiere firmas de `incident_commander` y `communications_lead`. Si sólo hay un actor disponible, break-glass permite una firma, razón obligatoria y TTL inicial máximo de 30 minutos. Cada renovación es explícita y mantiene alerta y auditoría persistentes.

El kill switch es local, visible y de un solo actor; nunca requiere quorum. Interferencia perjudicial observada obliga a ceder o detener. La pérdida del nivel superior no impide detener TX.

Límites no reemplazables, incluso en emergencia:

- jamming deliberado;
- TX continuo o diseñado para ocupar el canal;
- suplantación de servicios o identidades de terceros;
- control o interferencia ofensiva mediante SDR;
- anulación del kill switch o del registro de activación.

## 14. Coexistencia RF y capacidad

Separar claves y payloads no evita saturación, near-far o desensibilización co-site. Cada `OperationalArea` puede publicar un plan recomendado; una celda aislada conserva selección y scan locales y puede usar el override de emergencia.

`rf-coexistence-profile.yaml` fija:

- radios, canales, frecuencias y data rates;
- antenas, orientación, separación, filtros e aislamiento medido;
- airtime por plano y reserva SOS;
- nodos, hops, payload y mensajes máximos;
- presupuesto de confirmed downlinks y fragmentación;
- reacción ante congestión, near-far, co-site, relay loss y jamming detectado;
- firmware, hardware, escenario, fecha, evidencia y responsable.
- bearers primario/fallback, reglas anti-loop y condiciones de failover.

La referencia P1 usa radios y antenas separados. Un transceiver compartido es `unsupported` hasta validación. SOS desplaza telemetría no crítica, pero nunca habilita TX continuo. Cada SOS debe caber en un único frame para todo data rate habilitado; el perfil deshabilita data rates que no lo permitan.

Jamming sólo se detecta, registra y mitiga mediante canal, data rate, ubicación, relay o backhaul alternativo. No se responde con interferencia.

## 15. Threat model y gates de seguridad

El threat model normativo vive en `docs/security/OpenBREC-RF-threat-model.md`. Todo cambio de radio debe actualizarlo y producir safety review antes de campo.

Gates separados:

- `contract`: metaschema, schemas, fixtures y modelos generados sin diff;
- `crypto`: vectores válidos/forjados, nonce, rollback, revocación y rekey;
- `mesh-boundary`: ningún protobuf, ID persistente o ACK no confiable entra como hecho;
- `transport-policy`: profiles, capability manifests, deduplicación, anti-loop, failover y receipts por bearer;
- `mqtt-field`: auth, ACL, no-default-secret, retención, cuota y exposición;
- `lorawan`: OTAA, claves únicas, contadores y recuperación tras brownout;
- `federation`: partición, hub hostil, peering, handoff y reconciliación;
- `regulatory`: perfil, evidencia, autorizaciones, TTL, kill switch y recibo;
- `coexistence`: airtime, near-far, co-site, congestion y relay loss;
- `privacy`: disclosure mínimo normal y preservación life-safety auditada;
- `security`: threat model, SBOM, secret scan, firmware pinning y SOPs.

Fallan cerrado los cambios de confianza, elevación de rol, `operator.accepted`, publicación federada sensible y activación RF sin los requisitos de su modo. No falla cerrado la recepción o preservación de posible distress.

## 16. Validación P0, P1 y escala federada

### 16.1 P0 simulado

- schemas y fixtures válidos/inválidos;
- adapters/modelos comparables de Meshtastic, MeshCore y Reticulum sobre el mismo `OpenBRECEnvelope`;
- perfiles mobile-spontaneous, planned-repeater y heterogeneous-backbone con workloads idénticos donde corresponda;
- 12, 40 y 100 nodos, path churn, flood, relay loss, duplicación multi-bearer y carry bundle;
- vectores criptográficos reproducibles;
- replay determinístico de eventos auténticos, duplicados, tardíos, forjados y sin firma;
- partición de 24 horas, reloj degradado, reinicio y rollback;
- hubs malicioso e indisponible;
- revocación y rekey con una celda desconectada;
- double authorization, break-glass, expiración y kill switch simulados;
- cero `operator.accepted` falso y cero pérdida silenciosa.

### 16.2 P1a conducted

Incluye hardware LoRaWAN y al menos Meshtastic, MeshCore y RNode mediante dummy load, interfaces cableadas o recinto de atenuación medido. Verifica potencia, airtime, goodput, overhead, un frame SOS, brownout de contadores, co-site, near-far, path churn y downgrade legacy sin radiación exterior intencional. El resultado asigna support status por `TransportProfile`; no declara ganador global.

### 16.3 P1b radiado

Requiere perfil `jurisdiction_validated` o activación `emergency_assumed_risk`, safety review vigente, coexistence profile y responsable presente. Cada sesión produce evidencia de configuración, scan, potencia, tiempo, autorizaciones, stop conditions y cierre.

### 16.4 Escenario de federación masiva

La simulación de aceptación contiene:

- 50.000 sitios registrados;
- 60 `ResponseCell`;
- 5 `OperationalArea`;
- 2 hubs redundantes;
- pérdida simultánea de ambos hubs y particiones de 24 horas;
- IDs concurrentes, handoffs y asignaciones conflictivas;
- robo de nodo, rekey y revocación offline;
- distress auténtico, duplicado, tardío, forjado y sin firma;
- peer y hub maliciosos;
- congestión, jamming detectado y pérdida de relay.

Aceptación:

- cada celda conserva SOS, sensing, mensajería y decisiones RF localmente;
- cero `operator.accepted` falsos;
- cero eventos silenciosamente perdidos o sobreescritos;
- reconciliación determinística con conflictos visibles;
- un hub comprometido no puede falsificar firmas, desencriptar contenido de celda ni ordenar TX;
- la federación comparte resúmenes mínimos por defecto;
- un override expira y detiene TX sin depender del hub;
- el resultado se reproduce desde fixtures y receipts.

## 17. SOPs y artefactos de evidencia

Antes de campo deben existir:

- commissioning y preflight de radio;
- enrolamiento presencial y remoto limitado;
- pérdida/robo, revocación y rekey;
- break-glass RF, renovación y kill switch;
- interferencia, congestión y cambio de canal;
- peering, partición, handoff y reconciliación;
- safe shutdown y recuperación tras brownout;
- cierre de incidente, exportación, retención y borrado;
- registro de resultados negativos y excepciones.

Cada corrida conserva configuración versionada, capability manifests, hashes de firmware, schemas, fixtures, logs append-only, receipts, actores, reloj/incertidumbre y conclusión pass/fail.

## 18. Riesgos residuales

- Un jammer puede impedir comunicación local; OpenBREC sólo detecta y ofrece rutas alternativas.
- Un dispositivo robado puede exponer mensajes anteriores si su almacenamiento no es hardware-backed.
- Meshtastic puede cambiar propiedades de seguridad entre versiones; el pin y los tests son obligatorios.
- MeshCore puede cambiar path encoding, ACLs, bridge y criptografía; defaults, compatibilidad legacy y pin son gates.
- Reticulum aporta seguridad y heterogeneidad útiles, pero carece de auditoría externa y no prioriza SOS dentro de su forwarding general.
- Un selector multi-bearer mal configurado puede duplicar floods, crear loops o agotar energía/espectro.
- Una decisión `emergency_assumed_risk` puede producir consecuencias regulatorias o interferencia aun cumpliendo este proceso.
- Particiones pueden producir asignaciones incompatibles que requieren resolución humana.
- Los metadatos de tráfico y ubicación siguen siendo sensibles aun con contenido cifrado.
- Un hub malicioso puede retrasar u omitir eventos, aunque no pueda falsificar firmas de celda.

## 19. Fuentes primarias y evidencia contextual

- Meshtastic Encryption: https://meshtastic.org/docs/overview/encryption/
- Meshtastic mesh algorithm: https://meshtastic.org/docs/overview/mesh-algo/
- Meshtastic LoRa/max hops: https://meshtastic.org/docs/configuration/radio/lora/
- Meshtastic device roles: https://meshtastic.org/docs/configuration/radio/device/
- Meshtastic MQTT: https://meshtastic.org/docs/software/integrations/mqtt/
- Meshtastic regiones por país: https://meshtastic.org/docs/configuration/region-by-country/
- MeshCore repository/roadmap: https://github.com/meshcore-dev/MeshCore
- MeshCore FAQ: https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md
- MeshCore security policy: https://github.com/meshcore-dev/MeshCore/blob/main/SECURITY.md
- Reticulum manual: https://reticulum.network/manual/
- Reticulum status/security caveat: https://github.com/markqvist/Reticulum
- LoRa Alliance Technical Specifications: https://resources.lora-alliance.org/technical-specifications
- LoRaWAN Relay TS011: https://resources.lora-alliance.org/technical-specifications/ts011-1-0-0-relay
- LoRaWAN security implementation: https://lora-alliance.org/resource_hub/lorawan-is-secure-but-implementation-matters/
- Babel RFC 8966: https://www.rfc-editor.org/rfc/rfc8966.html
- Linux batman-adv: https://www.kernel.org/doc/html/latest/networking/batman-adv.html
- OpenThread: https://openthread.io/
- Bundle Protocol v7: https://www.rfc-editor.org/rfc/rfc9171.html
- URSEC, sistemas de radiocomunicaciones de uso propio: https://www.gub.uy/tramites/sistemas-radiocomunicaciones-uso-propio-autorizaciones-modificaciones-bajas
- URSEC, Reglamento del Servicio de Radioaficionados: https://www.gub.uy/unidad-reguladora-servicios-comunicaciones/institucional/normativa/resolucion-n-321022-apruebase-reglamento-del-servicio-radioaficionados
- URSEC, normativa de radiocomunicaciones: https://www.gub.uy/unidad-reguladora-servicios-comunicaciones/normativa-radiocomunicaciones

Las versiones y condiciones externas se vuelven a verificar al crear cada perfil de campo; esta lista no congela su vigencia.

## 20. Siguiente gate

La revisión multi-bearer debe aprobarse junto con su actualización de la matriz conjunta. No habilita implementación ni TX. Después de aprobarla, el siguiente trabajo ejecutable sigue siendo M0 core; la comparación P0 de transportes sólo se planifica después de demostrar M0 exit.
