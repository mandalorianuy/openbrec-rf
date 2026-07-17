# Estado del arte y selección contextual de comunicaciones off-grid

- Estado: revisión multi-bearer aprobada; implementación no autorizada
- Fecha de corte: 2026-07-17
- Alcance: transportes humanos, máquina, federación y fallback para OpenBREC
- Condición: no autoriza implementación, compra, TX ni selección final de hardware
- Autoridad relacionada: especificación de radio y matriz conjunta de addons

## 1. Veredicto

OpenBREC no debe adoptar Meshtastic, MeshCore, Reticulum ni ningún otro stack como "la red". Debe definir un plano lógico OpenBREC común y seleccionar un portafolio de bearers por misión, entorno, movilidad, densidad, energía, hardware disponible y regulación.

La recomendación revisada es:

- Meshtastic como perfil de referencia para grupos móviles, despliegue rápido y topología poco conocida.
- MeshCore como candidato de igual prioridad experimental para celdas planificadas con repeaters estratégicos y tráfico directo predominante.
- Reticulum/RNode como candidato de igual prioridad experimental para gateways multi-bearer, DTN, enlaces heterogéneos y transferencias que exceden el texto LoRa mínimo.
- LoRaWAN privado, con relay estándar sólo cuando corresponda, para telemetría y componentes; no como mensajería humana general.
- Ethernet, Wi-Fi y mallas IP para backhaul local o cargas de mayor ancho de banda.
- Thread/IEEE 802.15.4 como alternativa local de bajo consumo para clusters de sensores, no como reemplazo de LoRa de área amplia.
- bundles firmados, BPv7 o transporte físico como fallback de partición prolongada.
- voz LMR/VHF/UHF y backhaul celular/satelital como planos separados e integrables por gateway, sin convertirlos en dependencia del core.

Ningún perfil hereda autenticidad, prioridad SOS, aceptación operacional ni semántica de entrega del transporte. Todo eso permanece en OpenBREC.

## 2. Correcciones a la comparación inicial

### 2.1 Meshtastic

La caracterización como mesh de flooding móvil es útil, pero incompleta:

- Los broadcasts usan managed flooding: los nodos escuchan antes de repetir y pueden suprimir su retransmisión si otro ya lo hizo.
- Desde la versión 2.6, los mensajes directos aprenden next-hop por salto y vuelven a flooding cuando el camino deja de funcionar.
- No todos los dispositivos deben repetir: existen roles `CLIENT_MUTE`, `CLIENT_HIDDEN`, `REPEATER`, `ROUTER` y otros, además de modos de rebroadcast.
- El máximo configurable es 7 hops y el valor por defecto es 3.
- El firmware adapta intervalos de telemetría/posición para meshes con más de 40 nodos vistos, pero esto reduce tráfico auxiliar; no demuestra capacidad para carga humana densa.
- Los DMs entre versiones modernas incorporan PKC, firma e integridad. Los mensajes de canal siguen sin integridad/autenticación fuerte y la PSK inicial conocida debe cambiarse.

Conclusión: Meshtastic sigue siendo un buen candidato para movilidad y despliegue espontáneo, pero no debe considerarse flooding puro ni solución demostrada para alta densidad. El overlay OpenBREC sigue siendo obligatorio, especialmente para canales, compatibilidad legacy, revocación y semántica SOS.

### 2.2 MeshCore

La separación `Companion`/`Repeater` y el aprendizaje de caminos reducen retransmisiones para tráfico directo después del descubrimiento inicial. Esto lo hace especialmente relevante para infraestructura planificada.

Pero `64 hops` no significa que una red de 64 saltos sea operacionalmente usable:

- Es el máximo interno con paths de un byte; la propia documentación advierte que será difícil alcanzarlo en condiciones reales.
- Paths de dos y tres bytes reducen el máximo a 32 y 21 hops.
- Los identificadores de path de un byte pueden colisionar y degradar observabilidad de rutas.
- Repeaters anteriores a 1.14 pueden descartar silenciosamente paths de dos o tres bytes.
- El primer mensaje directo descubre camino por flood; los canales grupales siempre usan flood.
- Movilidad alta rompe paths y provoca retries más fallback a flooding.
- La documentación oficial considera que un workload móvil y chatty como ATAK no es actualmente un buen fit sin infraestructura de repeaters.
- El proyecto publica credenciales administrativas/guest predeterminadas que deben reemplazarse y aplica fixes de seguridad sólo a la última línea soportada.
- ACLs de repeater/room server, bridge estandarizado y una especificación criptográfica V2 siguen figurando en el roadmap.

Conclusión: MeshCore se promueve de watchlist a candidato P0/P1a para una `planned_repeater_cell`, pero los 64 hops son un límite de encoding, no un claim aceptable de escala, resiliencia o latencia.

### 2.3 Reticulum

La descripción como stack multi-bearer, cifrado y capaz de transferir archivos es correcta. Dos afirmaciones necesitan corrección:

- El proyecto declara implementadas las funciones core y considera estable su API y wire format; no corresponde llamarlo genéricamente "inestable".
- No hay evidencia primaria de que tenga menor alcance RF por sus handshakes. A igual hardware, frecuencia, ancho de banda, spreading factor, coding rate, potencia y antena, el protocolo puede consumir más airtime o reducir goodput, pero eso no prueba menor link budget o alcance físico.

Sí existen límites relevantes:

- Reticulum se declara software relativamente joven y no auditado externamente.
- El establecimiento de un Link cuesta tres paquetes y 297 bytes; en un bearer LoRa lento ese costo debe medirse.
- El forwarding general es priority-agnostic y no puede discriminar tráfico por fuente o contenido; OpenBREC debe priorizar SOS antes de entregarlo al interface y limitar announce/transfer traffic.
- Un gateway mal configurado puede verter announces de un enlace rápido a LoRa y desperdiciar airtime.
- La referencia principal corre en Python/RNode, lo que aumenta capacidad y complejidad del nodo respecto de un terminal MCU autónomo.

Conclusión: Reticulum se promueve a candidato P0/P1a para gateway/backbone heterogéneo y DTN. No reemplaza automáticamente a Meshtastic o MeshCore en terminales simples.

## 3. La unidad de decisión es el perfil, no el protocolo

Cada `ResponseCell` selecciona un `TransportProfile` usando al menos:

- `plane`: humano, máquina, federación o media;
- `mission`: chat, status, SOS, location, telemetry, artifact o voice;
- `mobility`: fixed, nomadic, mobile o mixed;
- `topology`: unknown, partially_planned o planned;
- `node_count`, `message_rate`, `payload_bytes` y `latency_class`;
- `coverage_shape`, obstáculos, altura y links posibles;
- energía disponible y autonomía requerida;
- hardware, firmware y operadores disponibles;
- espectro/regulación y coexistencia;
- amenaza, privacidad, identidad y custodia;
- backhaul disponible y duración de partición esperada.

La salida es un conjunto, no un único valor:

- `primary_bearer`;
- `fallback_bearers[]` ordenados;
- `carry_bearer` para bundle físico/DTN;
- `prohibited_bridges[]`;
- `airtime_budget` y prioridad;
- `activation_conditions`, `expiry` y `kill_switch`;
- `evidence_refs` y `decision_actor`.

La selección inicial ocurre en commissioning. El cambio dinámico automático entre radios queda deshabilitado hasta probar estabilidad, anti-loop, consumo y coexistencia. Un operador puede cambiar de perfil con receipt; un gateway puede hacer failover sólo entre bearers ya autorizados.

## 4. Perfiles operativos de referencia

| Perfil | Situación | Primario candidato | Fallback | Riesgo dominante |
|---|---|---|---|---|
| `mobile_spontaneous_team` | 2–20 personas, todos móviles, topología desconocida | Meshtastic | LoRa directo, LMR/voz, bundle físico | Flooding, congestión y pérdida de terminal |
| `planned_urban_response_cell` | repeaters altos/fijos, companions móviles, rutas relativamente estables | MeshCore | Meshtastic en canal separado, IP local | Mala colocación, path churn, flood grupal |
| `heterogeneous_gateway_backbone` | LoRa + Wi-Fi/Ethernet + packet radio + enlaces intermitentes | Reticulum/RNode o IP+DTN | BPv7/file bundle | Airtime leak, complejidad, prioridad agnóstica |
| `machine_telemetry_cell` | sensores/energía/health, uplink pequeño | LoRaWAN privado | TS011 relay, enlace local, almacenamiento | counters, downlink, gateway loss |
| `dense_local_command` | edificio/base con energía y mayor volumen | Ethernet/Wi-Fi mesh | Reticulum sobre IP, medios físicos | consumo, interferencia 2.4/5 GHz, loops |
| `local_low_power_sensor_cluster` | sensores cercanos dentro de sitio | Thread/802.15.4 | cable, LoRaWAN | alcance corto, border router, coexistencia |
| `hard_partition_carry` | no existe camino de radio útil | bundle firmado/BPv7/USB | mensajero físico redundante | custodia, demora, pérdida del medio |
| `opportunistic_backhaul` | aparece IP celular/satelital/microondas | HTTPS/mTLS o Reticulum boundary | carry bearer | proveedor, costo, metadata, dependencia |
| `voice_coordination` | voz humana crítica | LMR/VHF/UHF autorizado | sat/celular/PTT local | regulación, claves, interoperabilidad |

Estos perfiles pueden coexistir en un mismo incidente, área o celda. No deben compartir automáticamente frecuencia, claves, identidad o failure domain.

### 4.1 Escala de incidente

Un incidente con decenas de equipos o decenas de miles de sitios no se convierte en una malla LoRa única. Se divide en muchas `ResponseCell` que pueden elegir perfiles distintos y seguir operando aisladas. La coordinación superior intercambia `DomainEvent` firmados mediante federation gateways, backhaul IP, Reticulum boundary o carry bundles; nunca floods crudos.

Los hop limits sólo describen caminos dentro de una red local. No se aceptará una cadena urbana de 7, 21, 32 o 64 saltos como estrategia de escala sin evidencia específica de latencia, airtime, disponibilidad y recuperación. El límite de failure domain se fija por celda y puede ser menor que el máximo técnico del protocolo.

## 5. Tecnologías adicionales relevantes

### 5.1 LoRaWAN Relay

La especificación LoRaWAN TS011 define relay bidireccional entre end-device y gateway/network server. Puede extender telemetría donde falta cobertura directa, pero conserva la dependencia lógica del network server y no crea una malla humana general. Se evalúa sólo para el plano máquina.

### 5.2 Mallas IP

- Babel (RFC 8966) está diseñado para redes cableadas o inalámbricas, estables o dinámicas, y limita loops/black holes durante reconvergencia.
- `batman-adv` opera en Layer 2 sobre interfaces Ethernet-like y permite transportar IPv4/IPv6 u otros protocolos encima.

Ambos son candidatos para Wi-Fi/Ethernet local con más energía y ancho de banda que LoRa. Requieren security overlay, segmentación y pruebas de movilidad/coexistencia; no se transportan sobre LoRa MCU como reemplazo directo.

### 5.3 Thread/OpenThread

OpenThread implementa IPv6/6LoWPAN sobre IEEE 802.15.4, seguridad MAC, mesh routing y border routers. Es útil para sensores de baja energía dentro de una zona acotada, especialmente cuando ya existe hardware 802.15.4. Su banda 2.4 GHz, alcance y dependencia de commissioning/border routing lo dejan como bearer local, no de área amplia.

### 5.4 DTN y transporte físico

BPv7 y el bundle mínimo OpenBREC cubren particiones donde ningún mesh puede crear conectividad. Un bundle conserva identidad, firma, expiry, custodia e idempotencia al cruzar USB, disco, vehículo o enlace oportunista. Esta capacidad no es un último recurso informal: es parte obligatoria de la arquitectura.

### 5.5 Voz y enlaces de mayor capacidad

LMR/VHF/UHF, Wi-Fi direccional, microondas, satélite y celular pueden resolver voz o backhaul que LoRa no debe intentar. OpenBREC registra disponibilidad, salud y handoffs; no controla ni reimplementa esos sistemas en la fase inicial.

## 6. Contrato de adaptación común

Todo adapter implementa la misma frontera lógica:

- `capabilities()`: payload máximo, broadcast/direct, ack técnico, mobility, relay, store-forward, energía y regulación;
- `health()`: disponibilidad, queue depth, airtime, channel use, path freshness y clock uncertainty;
- `encode(OpenBRECEnvelope)` y `decode(raw_transport)`;
- `send()` con receipt técnico y nunca con aceptación operacional implícita;
- `cancel()` sólo cuando el bearer lo soporte, sin borrar el evento original;
- fixtures raw válidos, inválidos, legacy, corruptos y hostiles;
- replay determinístico y provenance completo;
- pin de versión, hash/SBOM/licencia y capability manifest.

El `TransportPolicyController` decide qué adapter puede recibir cada mensaje. La decisión queda registrada como `TransportPolicyDecision` y es reproducible en replay.

Un mismo `message_id` puede enviarse por varios bearers. El receptor deduplica por ID/firma y conserva receipts por camino. Está prohibido convertir un ACK de relay, next-hop, LoRaWAN o broker en `operator.seen` u `operator.accepted`.

## 7. Reglas de bridging

- No se puentean frames o floods crudos entre Meshtastic, MeshCore, Reticulum, LoRaWAN o IP.
- Cada adapter termina el transporte, valida el envelope OpenBREC y publica un `DomainEvent`.
- Sólo eventos autorizados pueden volver a emitirse por otro bearer.
- `hop_count` de un transporte nunca se copia al otro; cada camino conserva provenance propio.
- Rate limit, TTL, loop-prevention y deduplicación se aplican antes de reemitir.
- Un fallo o compromiso de un bearer no habilita claves ni administración de otro.
- La federación entre celdas intercambia eventos, no topologías internas ni brokers.

## 8. Comparación P0 obligatoria

P0 debe ejecutar el mismo workload OpenBREC al menos sobre modelos/adapters de Meshtastic, MeshCore y Reticulum:

1. Equipo móvil: 12 nodos, 3 zonas, movilidad y relay loss.
2. Celda planificada: 12 companions, 4 repeaters y dos caminos alternativos.
3. Densidad: 40 y 100 nodos con chat, estado, ubicación, health y SOS.
4. Partición: 24 horas, reencuentro, duplicados y mensajes expirados.
5. Heterogeneidad: LoRa lento + Ethernet/Wi-Fi + carry bundle.
6. Adversarial: forged sender, default credential, replay, malicious relay y flood.

Métricas mínimas:

- PDR por clase y denominador completo;
- latencia p50/p95/p99 y deadline misses de SOS;
- airtime total, por mensaje útil y por nodo;
- colisiones, retries, floods, path resets y duplicates;
- energía por delivered byte y autonomía proyectada;
- convergencia después de movimiento o relay loss;
- false technical ACK y cero false operational acceptance;
- metadata expuesta y datos retenidos;
- tiempo de commissioning, recuperación y carga cognitiva;
- capacidad de operar sin app, hub, Internet o servicio superior.

Los máximos de hops no sustituyen estas métricas. Un protocolo avanza por perfil sólo si supera el criterio del escenario, no por una cifra de marketing o encoding.

## 9. P1a comparativo

Después de M0 y P0:

- usar al menos dos familias de hardware reutilizable cuando sea posible;
- ejecutar TX sólo conducted/dummy load o recinto medido;
- fijar versiones exactas y eliminar credenciales/default channels;
- comparar Meshtastic, MeshCore y RNode con payload, PHY y potencia equivalentes cuando el hardware lo permita;
- medir overhead, goodput y alcance conducted/link budget por separado;
- probar coexistencia entre plano humano, LoRaWAN, Wi-Fi/802.15.4 y radios vecinas;
- repetir fallos de energía, pérdida de path, downgrade legacy y terminal robado;
- no declarar ganador global: producir support status por `TransportProfile`.

## 10. Cambios de decisión resultantes

1. Meshtastic deja de ser el único transporte humano de referencia; conserva prioridad para movilidad espontánea.
2. MeshCore sube de `WATCH` a `GO-P0→P1a` experimental para infraestructura planificada.
3. Reticulum/RNode sube de `WATCH-P0` a `GO-P0→P1a` experimental para gateway/backbone multi-bearer y DTN.
4. Se agrega `TransportPolicyController` y contratos de perfil/capacidad/decisión a P0.
5. Se agregan mallas IP y Thread como alternativas de bearer, con alcance acotado.
6. Se conserva el mesh OpenBREC propio en `DEFER`; sólo se reabre si alternativas abiertas fallan el mismo requisito obligatorio medido.
7. El procurement no compra una flota por protocolo: primero reutiliza/bench hardware que pueda probar más de un firmware o interface sin mezclar failure domains.

## 11. Evidencia primaria

- Meshtastic mesh algorithm: https://meshtastic.org/docs/overview/mesh-algo/
- Meshtastic LoRa/max hops: https://meshtastic.org/docs/configuration/radio/lora/
- Meshtastic device roles: https://meshtastic.org/docs/configuration/radio/device/
- Meshtastic encryption: https://meshtastic.org/docs/overview/encryption/
- MeshCore repository/roadmap: https://github.com/meshcore-dev/MeshCore
- MeshCore FAQ, routing y limits: https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md
- MeshCore security policy: https://github.com/meshcore-dev/MeshCore/blob/main/SECURITY.md
- Reticulum manual: https://reticulum.network/manual/
- Reticulum repository/status/security caveat: https://github.com/markqvist/Reticulum
- LoRaWAN Relay TS011-1.0.0: https://resources.lora-alliance.org/technical-specifications/ts011-1-0-0-relay
- Babel RFC 8966: https://www.rfc-editor.org/rfc/rfc8966.html
- Linux `batman-adv`: https://www.kernel.org/doc/html/latest/networking/batman-adv.html
- OpenThread: https://openthread.io/
- Bundle Protocol v7: https://www.rfc-editor.org/rfc/rfc9171.html

Las fuentes describen capacidades y límites del proyecto/estándar; no prueban compatibilidad, seguridad o performance OpenBREC. Versiones, defaults y roadmap deben reverificarse al fijar cada experimento.

## 12. Gate de aprobación

Si se aprueba esta revisión, la especificación de radio y la matriz conjunta deben reflejar el portafolio multi-bearer y los tres candidatos LoRa P2P en P0/P1a. Esto no modifica el bloqueo de implementación: M0 ejecutable sigue siendo la precondición.
