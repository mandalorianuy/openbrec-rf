# Addons de energía off-grid, comunicaciones LoRa y beacons para OpenBREC RF

- Estado: diseño aprobado
- Fecha: 2026-07-16
- Perfil regulatorio inicial: Uruguay
- Alcance: contratos y simulación P0, referencias físicas P1 y validación controlada P2

## 1. Contexto

OpenBREC RF es un marco offline-first, capability-driven y evidence-first para sensing defensivo y fusión explicable de evidencia en operaciones BREC/USAR. El repositorio actual sigue siendo un bundle de diseño cuyo primer incremento ejecutable es `lab-sim`.

Este diseño extiende el marco con tres áreas relacionadas pero desplegables de forma independiente:

1. Energía híbrida solar y portátil.
2. Comunicaciones LoRa off-grid para componentes OpenBREC y personas.
3. Beacons modulares para sensing acústico, movimiento, calor y sensores futuros.

Las tres áreas son addons. No pueden retrasar ni convertirse en dependencias obligatorias del núcleo `lab-sim`.

## 2. Objetivos

- Mantener un núcleo pequeño e independiente del hardware.
- Soportar operación solar potencialmente indefinida, condicionada por límites energéticos y ambientales medidos.
- Mantener 72 horas de reserva sin aporte solar para gateway y servicios críticos.
- Usar LoRaWAN privado para telemetría de componentes.
- Usar un plano LoRa P2P/mesh separado para mensajes humanos, estado, SOS y ubicación.
- Adoptar Meshtastic como referencia opcional, version-pinned y reemplazable para el plano humano.
- Definir un `BeaconNode` genérico capaz de sensar, retransmitir o cumplir ambos roles.
- Ofrecer diseños abiertos construibles y permitir reutilizar hardware comercial o comunitario compatible.
- Fallar de forma cerrada ante regulación incompleta, privacidad, riesgos de seguridad o capacidades no verificadas.

## 3. Fuera de alcance

- Voz o transferencia general de archivos por LoRa.
- Escucha remota continua.
- Reconocimiento de identidad por voz, rostro u otra biometría.
- Presentar un SOS como equivalente a un servicio de emergencia certificado.
- Permitir que usuarios de la red humana escriban directamente observaciones o hechos OpenBREC.
- Exigir Meshtastic, un chipset de radio o un fabricante específico.
- Declarar autonomía perpetua sin balance energético medido.
- Habilitar transmisión RF antes de cerrar el gate regulatorio de Uruguay.
- Modificar las prohibiciones existentes sobre Wi-Fi ofensivo, jamming, interferencia, emulación celular o control autónomo de UAS.

## 4. Arquitectura y dependencias

El repositorio usará un núcleo estable, addons de referencia y adapters reemplazables.

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

Las rutas finales podrán ajustarse al scaffold ejecutable, pero la dependencia será siempre unidireccional:

```text
contratos del core <- addons <- adapters y hardware de referencia
```

El core no importará addons, SDK de fabricantes ni protocolos externos. Los adapters traducirán protocolos externos a contratos internos versionados. El hardware de referencia implementará capacidades declaradas sin cambiar los contratos.

Un addon podrá extraerse a otro repositorio cuando tenga contrato estable y necesidad de release independiente. Esa extracción no podrá alterar la semántica que consumen el core o terceros.

## 5. Planos de red

### 5.1 Telemetría de componentes

El plano máquina usará LoRaWAN privado con network server alojado localmente en el gateway OpenBREC. Transportará telemetría compacta, salud, energía, observaciones de beacons y recibos de store-and-forward.

No requerirá nube. La caída de LoRaWAN no detendrá el sensing local ni la red humana.

### 5.2 Comunicación humana

El plano humano usará LoRa P2P/mesh para:

- texto breve;
- estados predefinidos;
- SOS;
- ubicación.

Meshtastic será la implementación de referencia P1. El adapter se conectará mediante interfaces locales documentadas como BLE, USB/serial o TCP. Podrá usarse un bridge MQTT privado y local; el broker público de Meshtastic no forma parte del diseño operacional.

El contrato interno `HumanMessage` será independiente de protobufs Meshtastic. Otras mallas LoRa o futuros transportes podrán implementar el mismo contrato.

Firmware y protobufs Meshtastic deberán fijarse a versiones revisadas. Su licencia GPL-3.0 exige una revisión explícita de distribución y compatibilidad antes de publicar un artefacto integrado. La frontera de adapter aporta aislamiento arquitectónico, pero no reemplaza esa revisión.

### 5.3 Aislamiento

Los planos podrán compartir gabinete, energía, sitio de antena o gateway cuando exista validación, pero mantendrán separados:

- claves y enrolamiento;
- colas y prioridades;
- métricas y auditoría;
- dominios de fallo;
- autorización;
- payloads de protocolo.

La red humana no publicará observaciones, evidencias ni hechos. Un servicio revisado podrá convertir un mensaje permitido en una anotación de operador.

## 6. Usuarios y terminales

Se validarán dos caminos:

1. Rescatistas y operadores entrenados con teléfono o tablet conectado a un equipo LoRa por BLE o USB.
2. Personas no preparadas con terminal entregable o estación física: controles simples de SOS/estado, pantalla pequeña, ubicación y mensajes predefinidos.

También se documentará, sin validación inicial, una red humana separada para personas que ya posean dispositivos compatibles. Esa red no tendrá acceso al plano operativo OpenBREC.

## 7. Beacon genérico

`BeaconNode` será un rol lógico, no un producto fijo. Un dispositivo podrá implementar una o más capacidades de sensing, un relay LoRa o ambos. Los roles serán configurables y degradables por separado.

El beacon P1 de referencia será modular e incluirá:

- sensing de eventos acústicos;
- movimiento PIR de bajo consumo;
- matriz térmica de baja resolución.

Los beacons con un único sensor serán válidos. Cada capacidad declarará `supported`, `experimental`, `unverified` o `unavailable`.

Cada beacon reportará calibración, versiones de hardware y firmware, salud, modo energético, calidad de reloj, sensores ausentes, limitaciones y confianza. El fallo de una capacidad no invalidará observaciones de las demás.

### 7.1 Audio

El modo predeterminado hará extracción o clasificación local y emitirá sólo eventos compactos. No transmitirá ni persistirá audio crudo.

Un modo futuro de fragmento solicitado por operador requerirá autorización explícita, cifrado, auditoría, duración limitada, expiración de retención y señalización visible. La escucha continua remota está prohibida.

Los modelos acústicos requerirán clase `unknown`, abstención, dataset card, model card y validación por entorno. Un sonido compatible con humano o mascota seguirá siendo un indicio que requiere verificación independiente.

### 7.2 Movimiento y calor

PIR y térmica producirán indicios, no hechos de presencia. La referencia térmica no generará imágenes identificables. El silencio o ausencia de cualquier sensor nunca respaldará una inferencia negativa de víctima.

## 8. Addon de energía

La arquitectura será híbrida:

- generación solar y almacenamiento LiFePO4 central para gateway, red, PoE y carga;
- solar individual sólo en relays o beacons remotos que necesiten operación extendida;
- generadores y estaciones portátiles como fuentes de soporte intercambiables;
- operación sólo con baterías válida cuando el addon no esté disponible.

El objetivo será 72 horas sin aporte solar para gateway y comunicaciones críticas. La operación potencialmente indefinida será siempre condicional a generación, almacenamiento, consumo, clima, temperatura, mantenimiento y degradación medidos.

El addon declarará fuentes, almacenamiento, carga, consumo, reserva, calidad de medición y modos soportados.

Estados de degradación:

```text
NORMAL -> CONSERVE -> CRITICAL -> SURVIVAL -> SAFE_SHUTDOWN
```

La degradación reducirá primero muestreo, inferencia, pantalla y transmisiones no críticas. Un presupuesto reservado protegerá SOS, salud crítica y apagado seguro mientras sea físicamente posible.

Los diseños eléctricos de referencia incluirán BMS, fusibles, protección térmica, envolvente apropiada, conectores seguros, puesta a tierra documentada y separación entre cargas críticas y degradables.

## 9. Contratos internos

### 9.1 Energía

`EnergyCapability`, `EnergyStatus` y `EnergyBudget` incluirán fuentes, almacenamiento nominal y utilizable, estado de carga e incertidumbre, consumo, reserva estimada y supuestos, modo de degradación, salud, timestamp, calidad de reloj, limitaciones y mediciones ausentes.

### 9.2 Mensajería humana

`HumanMessage` incluirá versión, idempotency id, incidente y red, emisor efímero, destino o grupo, clase de mensaje, prioridad, timestamps, calidad de reloj, TTL, expiración, ubicación y política de precisión, requisito de acuse, estado de entrega, privacidad, cifrado, adapter y transporte.

Estados observables de SOS:

```text
queued -> transmitted -> relayed -> delivered -> acknowledged
                         |             |
                         +-> expired <-+
                         +-> failed
```

No se inferirá ningún estado posterior a `acknowledged`. La falta de acuse permanecerá visible como pendiente, expirada o fallida.

### 9.3 Beacons

`BeaconCapability` y `BeaconObservation` incluirán tipo y soporte, versiones, calibración, features compactas, calidad, confianza, incertidumbre, abstención, política de privacidad, flag de retención de media —`false` por defecto—, modo energético, costo estimado, sensores ausentes, limitaciones y referencias a eventos locales.

### 9.4 Transporte

`TransportEnvelope` incluirá transporte, versión del adapter, idempotency id, origen, destino, timestamps, calidad de reloj, saltos, calidad de enlace, reintentos, cola e integridad. El payload de dominio no dependerá de su implementación.

## 10. Flujo y fallos

```text
hardware o simulador
  -> adapter validado
  -> contrato interno versionado
  -> cola priorizada y store-and-forward local
  -> LoRaWAN o human mesh
  -> gateway local
  -> frontera MQTT/API
  -> persistencia y UI
```

Comportamiento obligatorio:

- Eventos idempotentes y deduplicables.
- Pérdida de enlace activa store-and-forward acotado.
- Cada nodo declara capacidad de cola y retención.
- La presión elimina primero telemetría de baja prioridad.
- Todo mensaje prioritario descartado o expirado genera transición auditable.
- La incertidumbre del reloj se conserva.
- El replay posterior no duplica hechos.
- La pérdida de un plano o sensor no derriba los demás.
- Silencio de radio, sensor o red nunca implica ausencia de persona.

## 11. Gates de seguridad, privacidad y regulación

### 11.1 Uruguay

Uruguay será el perfil inicial con configuración multirregión. Como Uruguay no figura actualmente en la tabla oficial de regiones Meshtastic, no se aceptará por presunción ningún preset.

TX permanecerá deshabilitado hasta registrar evidencia de:

- frecuencias permitidas;
- potencia conducida y radiada;
- restricciones de antena y EIRP;
- duty cycle o uso de canales;
- homologación e importación;
- necesidad de autorización URSEC para el despliegue.

Los perfiles de campo prohibirán overrides de frecuencia, potencia y duty cycle. Toda transmisión será trazable a región, canal/slot, potencia, antena y firmware.

### 11.2 Acceso y claves

- Planos humano y máquina con claves y rotación independientes.
- Brokers operativos privados y locales.
- Prohibición de claves públicas o predeterminadas para datos operativos.
- Administración con RBAC local y auditoría append-only.
- Un terminal humano comprometido no accede a sensores ni evidencia.

### 11.3 Privacidad y safety

- Identificadores por incidente y rotativos.
- Precisión de ubicación según rol y mensaje.
- Retención limitada y borrado verificable.
- SOS no certificado y sin garantía de entrega.
- Nuevas radios con threat model y safety review.
- Beacons publican observaciones, nunca hechos.
- Fallos energéticos preservan estado crítico y apagado seguro mientras sea posible.

## 12. Marco abierto y reutilización

Cada addon ofrecerá dos caminos:

1. Construir desde un diseño de referencia abierto.
2. Reutilizar hardware existente mediante adapter.

Documentación mínima:

- propósito, alcance y red lines;
- contratos y flujo;
- esquema, BoM, firmware, enclosure y montaje cuando exista hardware;
- alternativas compatibles y nivel de evidencia;
- consumo y balance energético medidos;
- calibración y mantenimiento;
- privacidad, threat model y safety review;
- regulación;
- fixtures de replay;
- protocolo de aceptación;
- matriz `supported`, `experimental`, `unverified`, `unavailable`.

Ningún claim de fabricante será `supported` sin evidencia propia.

## 13. Fases y aceptación

### 13.1 P0 — Contratos, simulación y replay

P0 agregará contratos y simuladores sin hardware y sin retrasar `lab-sim`.

- Schemas válidos con JSON Schema Draft 2020-12.
- Modelos consumidores generables desde una fuente.
- Replay idéntico produce el mismo hash y explicación.
- Energía simula generación normal/baja, 72 horas sin generación, reserva y apagado.
- Red simula particiones, duplicados, desorden, TTL, presión y recuperación.
- SOS recorre todos sus estados.
- Beacons cubren positivo, negativo, ambiguo, sensor ausente y `unknown`.
- Gates demuestran que no se persisten audio crudo ni identificadores directos.
- Checks concilian manifests, perfiles, Compose, servicios y rutas.

### 13.2 P1 — Banco físico

P1 agregará beacon multisensor, configuraciones de sensor único, gateway y network server LoRaWAN locales, adapter Meshtastic, dispositivos reutilizados, terminal de rescatista, banco energético central y un nodo solar remoto.

- Consumo medido por modo.
- Capacidad y degradación verificadas bajo carga.
- Hardware reutilizado y propio emiten los mismos contratos.
- Un sensor, red o adapter ausente no detiene lo restante.
- No hay TX de campo antes del gate Uruguay.

### 13.3 P2 — Campo controlado

P2 validará 72 horas continuas, operadores, terminales entregables, particiones, sensores, energía e interoperabilidad.

- Cargas críticas disponibles durante 72 horas.
- Al menos 95% de mensajes y telemetría entregados dentro del escenario, topología y carga documentados.
- Todo SOS no entregado queda pendiente, expirado o fallido; nunca confirmado.
- Al menos 99% de eventos retenidos dentro de capacidad se recuperan al restaurar enlace.
- Cada sensor sigue `experimental` hasta validar precisión, falsos positivos, abstención y generalización.
- Ningún silencio genera evidencia negativa de presencia.

## 14. Matriz posterior

La matriz de integración tendrá una fila por capacidad o alternativa y columnas de funcionalidad, valor BREC, evidencia, alternativa desacoplada, hardware reutilizable, diseño construible, energía, privacidad, safety, regulación, esfuerzo, dependencias, madurez, aceptación, recomendación y siguiente experimento.

Candidatos iniciales: solar, generadores, almacenamiento, LoRaWAN, Meshtastic, otras mallas LoRa, terminales, beacons acústicos/PIR/térmicos, relays y transportes alternativos de mayor ancho de banda.

## 15. Riesgos residuales

- Frecuencia, potencia y autorización en Uruguay siguen bloqueando claims de TX.
- Hardware, chipsets e importación pueden cambiar.
- Capacidad mesh depende de terreno, carga, antena y regulación.
- Autonomía solar depende de clima, sombra, envejecimiento y mantenimiento.
- Audio y térmica pueden generar privacidad y falsa confianza.
- Meshtastic y su licencia deben revisarse contra la versión P1 fijada.
- Los porcentajes P2 son gates acotados al escenario, no garantías universales.

## 16. Fuentes primarias

- URSEC, sistemas de radiocomunicaciones de uso propio: https://www.gub.uy/tramites/sistemas-radiocomunicaciones-uso-propio-autorizaciones-modificaciones-bajas
- LoRa Alliance, especificaciones y parámetros regionales: https://resources.lora-alliance.org/technical-specifications
- Meshtastic, hardware: https://meshtastic.org/docs/hardware/devices/
- Meshtastic, regiones: https://meshtastic.org/docs/configuration/region-by-country/
- Meshtastic, Client API: https://meshtastic.org/docs/development/device/client-api/
- Meshtastic, MQTT: https://meshtastic.org/docs/software/integrations/mqtt/
- Meshtastic, firmware y licencia: https://github.com/meshtastic/firmware
