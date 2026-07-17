# Matriz de decisión: energía, comunicaciones off-grid y beacons

- Estado: análisis inicial y revisión multi-bearer completas; pendiente de aprobación
- Fecha: 2026-07-17
- Alcance: decisión y orden de experimentos M0/P0/P1/P2
- Autoridad de entrada: cuatro especificaciones hijas aprobadas
- Condición: no autoriza implementación, compra, TX ni despliegue

## 1. Veredicto ejecutivo

OpenBREC debe seguir una estrategia core-first e híbrida:

1. Completar M0 ejecutable antes de implementar addons.
2. En P0 simular contratos, energía, radio, federación, beacons y UX sobre el mismo `DomainEvent` y replay.
3. En P1a validar hardware sin radiación exterior: radio conducted, beacons controlados, terminal offline y caracterización de cargas.
4. Ejecutar al final de P1a el ensayo storage-only de 72 horas con las cargas ya medidas.
5. En P1b abrir TX radiado, solar/generador y entrenamiento de campo únicamente con perfiles y safety reviews aprobados.
6. Usar P2 para campañas multi-equipo y claims acotados; no como sustituto de certificación o evidencia operacional real.

Recomendaciones principales:

- `BUILD`: contratos/replay, preservación, overlay de seguridad, federación y UX semántica.
- `ADAPT`: ChirpStack/LoRaWAN, Meshtastic, MeshCore, Reticulum/RNode, hardware existente, estaciones portátiles y sensores commodity según perfil.
- `EVALUATE`: LoRaWAN Relay, mallas IP, Thread/802.15.4, LMR/backhaul oportunista y BPv7/file bundles en su contexto propio.
- `DEFER`: mesh propio, LoRa federation-relay, bridging raw, audio raw amplio, mmWave, cámara y otras modalidades hasta que el core y las métricas justifiquen su costo/riesgo.
- `PROHIBIT`: jamming, TX continuo, identidad biométrica, ausencia por silencio, streaming acústico permanente y PSK común del incidente.

## 2. Estado real del repositorio

Las cuatro especificaciones hijas están aprobadas, pero M0 no está implementado. `scripts/validate_bundle.py` sólo valida estructura. `docker-compose.yml` referencia servicios todavía inexistentes y `services/README.md` los declara placeholders.

Por lo tanto:

- la madurez OpenBREC máxima actual de estas capacidades es `M1 design-approved`;
- ninguna integración tiene evidencia `M2 simulated` dentro del repo;
- esta matriz ordena decisiones, no es todavía un implementation plan;
- `DELIVERY_BOARD.md` sigue siendo la autoridad de ejecución hasta aprobar esta matriz y completar M0.

## 3. Escalas y códigos

### 3.1 Valor BREC

- `V5`: life-safety o continuidad crítica.
- `V4`: alto impacto operativo.
- `V3`: mejora importante, no crítica.
- `V2`: complemento situacional.
- `V1`: periférico o prematuro.

### 3.2 Evidencia disponible

- `A`: estándar/fuente primaria y precedentes maduros; falta aún prueba OpenBREC.
- `B`: referencia creíble y hardware/software disponible; evidencia de campo limitada.
- `C`: proyecto emergente, vendor/community evidence o hipótesis parcial.
- `D`: idea sin evidencia suficiente para inversión.

La letra evalúa la funcionalidad/alternativa general, no certifica un producto ni compatibilidad OpenBREC.

### 3.3 Madurez

- `M0`: idea.
- `M1`: diseño aprobado.
- `M2`: simulación/replay reproducible.
- `M3`: banco controlado.
- `M4`: entrenamiento/campo controlado.
- `M5`: evidencia operacional repetida.

Se expresa `externa/OpenBREC`, por ejemplo `M4/M1`.

### 3.4 Esfuerzo relativo

- `S`: adaptación o contrato acotado.
- `M`: subsistema con tests y documentación.
- `L`: integración hardware/software multidisciplinaria.
- `XL`: escala multi-equipo, regulación o campaña extensa.

No son estimaciones de calendario.

### 3.5 Gates

- `C`: contratos, fixtures y replay.
- `SEC`: identidad, criptografía, supply chain y access control.
- `PRV`: minimización, vault, review y retención.
- `RF`: coexistencia, airtime, perfil regulatorio y kill switch.
- `EN`: energía, brownout, eléctrico/térmico y 72 horas.
- `SCI`: protocolo, ground truth, incertidumbre, OOD y resultados negativos.
- `UX`: semántica, accesibilidad y comprensión humana.
- `OPS`: SOP, mando, training site y responsables.

## 4. Regla de decisión y conservación

No se usa un score agregado. Una opción avanza cuando:

1. aporta valor BREC suficiente;
2. su dependencia anterior está cerrada;
3. existe una alternativa desacoplada o una justificación explícita de build;
4. sus gates de riesgo tienen owner y criterio reproducible;
5. el siguiente experimento es el más pequeño capaz de cambiar la decisión.

Estados:

- `NOW-M0`: precondición inmediata.
- `GO-P0`: implementar sólo después de M0 exit.
- `GO-P1a`: hardware en banco/conducted.
- `GO-P1b`: campo controlado o TX radiado.
- `P2-CANDIDATE`: requiere evidencia P1 completa.
- `WATCH`: conservar y reevaluar por trigger.
- `DEFER`: no invertir ahora; evidencia y resultados permanecen.
- `PROHIBITED`: contradice red lines; sólo una decisión explícita de gobernanza podría revisar el límite.

La notación `A→B` exige dos decisiones separadas: primero se satisface el exit de `A` y luego se solicita autorización para `B`. `WATCH-P0` o `WATCH-P1` indica el gate más temprano en que corresponde reevaluar; no autoriza implementación.

Nada se elimina de la matriz. Un cambio produce una entrada append-only con fecha, evidencia, actor, decisión anterior, decisión nueva y razón. Resultados negativos quedan vinculados al row ID.

Cada funcionalidad se lee como un registro unido por su ID entre la tabla de decisión y la tabla de gates. `Reuso o build` cubre hardware reutilizable y frontera de construcción; `Decisión` es la recomendación vigente. Así se conservan, para cada ID, todos los campos exigidos sin comprimir criterios de aceptación o safety dentro de una única celda.

## 5. Fundación y M0

### 5.1 Decisión

| ID | Funcionalidad | Valor/evidencia | Alternativa desacoplada | Reuso o build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| F-01 | Schemas core/addon, modelos generados y compatibilidad | V5/A | Avro/Protobuf; no elegidos por autoridad actual | Build pequeño sobre JSON Schema | L | M5/M1 | NOW-M0 |
| F-02 | Runtime `lab-sim` offline, bus, API, worker y PWA mínima | V5/A | Binario monolítico; posible después | Build servicios mínimos, reutilizar Compose/Mosquitto/Postgres | L | M5/M0 | NOW-M0 |
| F-03 | Replay determinístico adapter/core y receipts | V5/A | Reprocesamiento ad hoc; rechazado | Build core; reutilizar fixtures/JSONL | L | M4/M1 | NOW-M0 |
| F-04 | EvidenceVault, ReviewQuarantine y RejectionLedger | V5/B | Filesystem cifrado/manual; sólo fallback | Build boundary y política, backend sustituible | L | M4/M1 | NOW-M0 |
| F-05 | Simulador/fault injection y campañas versionadas | V5/A | Test harness por addon; fragmentaría evidencia | Build simulador común | M | M5/M0 | NOW-M0 |
| F-06 | Gates CI separados y receipts de evidencia | V5/A | Checklist manual; sólo complemento | Build scripts/CI reproducibles | M | M5/M0 | NOW-M0 |

### 5.2 Gates y aceptación

| ID | Energía | Privacidad | Safety/regulación | Dependencias | Criterio de aceptación | Próximo experimento |
|---|---|---|---|---|---|---|
| F-01 | N/A | Handling policy cerrado | C+SEC | ADR-0001 | Metaschema+fixtures; Pydantic/TS sin diff; compatibilidad SemVer | Implementar catálogo core mínimo y un payload addon dummy |
| F-02 | Perfil de load simulado | Bus local sin Internet | SEC | F-01 | Compose build/start offline; healthchecks; demo sintética sin cloud | Crear servicios vacíos funcionales y smoke offline |
| F-03 | Brownout fixture | No raw leakage en receipts | C+SEC | F-01/F-02 | Mismo input/config produce mismo hash; cero pérdida silenciosa | Replay de 6 nodos/3 zonas dos veces |
| F-04 | Storage capacity declarada | PRV life-safety-first | SEC+PRV | F-01/F-02 | Inválido vital preservado; prohibido recibe receipt; review/disposición auditada | 12 fixtures inválidos con cuatro handling classes |
| F-05 | Traza de energía inyectable | Datos sintéticos por defecto | C+SCI | F-01/F-03 | Clock, pérdida, duplicado, partición, brownout y malicious peer reproducibles | Campaña P0 integrada mínima |
| F-06 | Gate EN separado | Gate PRV separado | Todos; sin afirmar producción | F-01–F-05 | `bundle-structure`, schema, compose, offline, replay, privacy, security, SBOM independientes | CI local que falle por fixture inválido y secret dummy |

## 6. Energía

### 6.1 Decisión

| ID | Funcionalidad | Valor/evidencia | Alternativa desacoplada | Reuso o build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| E-01 | Energy contracts, medición, budget y FSM | V5/A | Medición manual; insuficiente para gates | Build controller/projection; medidores sustituibles | L | M5/M1 | GO-P0 |
| E-02 | Almacenamiento central LiFePO4+BMS | V5/A | Otras químicas/UPS certificadas | Adapt pack comercial; no pack DIY de campo | L | M5/M1 | GO-P1a |
| E-03 | Estaciones portátiles y baterías reemplazables | V4/A | Bus DC construido | Adapt y caracterizar unidad exacta | M | M5/M1 | GO-P1a |
| E-04 | Solar central + MPPT | V4/A | Red/generador/recarga logística | Adapt componentes; diseño abierto de interconexión | L | M5/M1 | GO-P1b |
| E-05 | Solar individual para relay/beacon | V3/B | Batería reemplazable o recarga programada | Adapt por node profile | M | M4/M1 | GO-P1b |
| E-06 | Generador como soporte | V3/A | Solar+storage, red o estaciones | Adapt equipo existente; OpenBREC sólo monitorea | L | M5/M1 | GO-P1b |
| E-07 | Claim `sustainable_under_profile` | V3/B | Reserva fija/fuel logistics | Build cálculo/receipt, no claim “indefinido” | L | M4/M1 | P2-CANDIDATE |

### 6.2 Gates y aceptación

| ID | Impacto/boundary energético | Privacidad | Safety | Regulación | Dependencias | Criterio de aceptación | Próximo experimento |
|---|---|---|---|---|---|---|---|
| E-01 | Autoridad de medición y degradación; no crea energía | Telemetría/inventario mínimo | EN+C; SOC unknown permitido | Eléctrica local posterior | F-01/F-03 | Conservación de energía, hysteresis, runtime lower bound y brownout replay | Simular tres EnergyDomains y pérdida central |
| E-02 | Reserva storage-only de la cadena L0/L1 | Inventario sensible local | BMS, fuse, disconnect, IEC/UN evidence | Transporte/disposal aplicable | E-01 | Capacidad descargable medida; límites térmicos; cadena crítica 72h con 1.25× | Caracterizar una unidad candidata, sin compra en escala |
| E-03 | Autonomía local, swap y recarga; no reemplaza reserva central | IDs de packs restringidos | PD/rangos/pass-through/swap probados | Transporte aplicable | E-01 | No reboot no declarado; capacidad/puertos/corte low-load medidos | Banco con una estación y dos cargas reales |
| E-04 | Repone energía; nunca descuenta el requisito storage-only | Ubicación/inventario resumidos | MPPT, Voc/Isc, cable, viento, desconexión | Instalación local | E-01/E-02 | Siete días posteriores; no cuenta para storage-only; stop seguro | Emulador PV→MPPT→pack antes de panel de campo |
| E-05 | Extiende nodo bajo irradiancia declarada; batería sigue siendo necesaria | Placement sensible | Enclosure, panel, batería y mounting | Perfil local | E-01 + beacon load | Nodo sobrevive pérdida solar y reporta gap sin perder log | Un relay con irradiance/load replay y luego banco |
| E-06 | Fuente externa supervisada; no forma parte de autonomía storage-only | Fuel location restringida | CO, exterior, fuel, stop, no autostart inicial | Combustible/ruido/local | E-01/E-03 | Cero operación en recinto; alarm/stop drill; transición registrada | Simular source adapter; bench eléctrico sin combustión primero |
| E-07 | Claim por perfil y ventana, nunca “indefinido” sin límites | Resúmenes solamente | EN+SCI+OPS | Claims acotados | E-02–E-06 | Net lower bound no negativo por ventana; 24h sin generación; claim limitado | Campaña mixta de 7 días después de P1a 72h |

## 7. Comunicación, radio y federación

### 7.1 Decisión

| ID | Funcionalidad | Valor/evidencia | Alternativa desacoplada | Reuso o build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| C-01 | LoRaWAN privado para componentes | V5/A | MQTT/IP, 802.15.4 o enlace cableado | ADAPT ChirpStack/otro NS y gateways existentes | L | M5/M1 | GO-P0→P1a |
| C-02 | Meshtastic para equipo móvil/espontáneo: texto/estado/SOS/ubicación | V5/B | MeshCore planificado, Reticulum gateway o P2P directo | ADAPT firmware/hardware compatible y pin | L | M4/M1 | GO-P0→P1a |
| C-03 | Overlay OpenBREC de identidad, firma y AEAD | V5/A | Seguridad de transporte sola; insuficiente | BUILD transport-agnostic | L | M5/M1 | GO-P0 |
| C-04 | Dos hubs y FederationGateway outbound-only | V5/A | Hub único o cloud; rechazados como dependencia | BUILD eventos/gateway; ADAPT HTTPS/mTLS | XL | M5/M1 | GO-P0→P1b |
| C-05 | Red civil separada | V4/B | Terminal entregable en red controlada | ADAPT compatible hardware, claves/gateway propios | L | M4/M1 | P2-CANDIDATE |
| C-06 | Bundles físicos/DTN para store-and-forward | V4/A | HTTPS batch/poll o archivos firmados simples | EVALUATE BPv7; BUILD formato OpenBREC mínimo | M | M5/M1 | GO-P0 |
| C-07 | Backhaul IP de mayor ancho de banda | V4/A | USB/medios físicos o satélite/microondas addon | ADAPT Ethernet/Wi-Fi táctico | M | M5/M1 | GO-P1a |
| C-08 | LoRa `federation-relay` de resúmenes | V3/C | Backhaul IP/DTN | BUILD/ADAPT canal separado | L | M3/M1 | DEFER |
| C-09 | Selección por `TransportProfile`, multi-bearer, dedup y anti-loop | V5/A | Selección manual por SOP; fallback inicial | BUILD controller y contratos; adapters sustituibles | L | M5/M1 | GO-P0 |

### 7.2 Bearers alternativos y perfiles especializados

Los IDs `A-*` de esta sección son alternativas de bearer, no una categoría de menor prioridad. Su decisión depende del perfil operacional.

| ID | Funcionalidad | Valor/evidencia | Alternativa | Reuso/build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| A-01 | Reticulum/RNode + LXMF para gateway/backbone heterogéneo | V5/B | IP+BPv7 o LoRa P2P dedicado | ADAPT stack/hardware abierto; review criptográfico propio | L | M4/M0 | GO-P0→P1a |
| A-02 | MeshCore para celda con repeaters planificados | V5/B | Meshtastic/Reticulum | ADAPT firmware MIT y hardware LoRa reutilizable | L | M4/M0 | GO-P0→P1a |
| A-03 | Mesh LoRa OpenBREC propio | V3/D | C-02/A-01/A-02 | BUILD completo | XL | M0/M0 | DEFER |
| A-09 | Wi-Fi/Ethernet mesh con Babel o `batman-adv` | V4/A | Ethernet simple/Reticulum sobre IP | ADAPT routers/OpenWrt/Linux | L | M5/M0 | GO-P0→P1a |
| A-10 | Thread/OpenThread para cluster local de sensores | V3/A | LoRaWAN/cable | ADAPT 802.15.4 y border router | L | M5/M0 | WATCH-P0 |
| A-11 | LoRaWAN Relay TS011 para cobertura máquina | V3/A | Gateway adicional/store-forward | ADAPT relay/end-device/NS compatibles | L | M4/M0 | WATCH-P1 |
| A-12 | LMR/VHF/UHF para voz humana | V5/A | sat/celular/PTT IP | ADAPT equipos existentes; OpenBREC sólo boundary/health | XL | M5/M0 | WATCH-P1 |
| A-13 | Backhaul celular/satelital/microondas oportunista | V4/A | IP terrestre/carry bundle | ADAPT modem/terminal autorizado | L | M5/M0 | WATCH-P1 |

### 7.3 Gates y aceptación

| ID | Energía | Privacidad | Safety | Regulación | Dependencias | Criterio de aceptación | Próximo experimento |
|---|---|---|---|---|---|---|---|
| C-01 | Airtime/load en E-01 | DevEUI/metadata boundary | SEC+C; OTAA/counters | RF profile | F-01/F-03/E-01 | 12 nodos simulados; OTAA único; brownout no rollback; MQTT ACL | ChirpStack offline con dos dispositivos simulados |
| C-02 | Terminal/relay load | IDs HMAC; no broker público | SEC+UX; transporte no confiable | RF profile | F-01/F-03/C-03/C-09 | Default PSK prohibida; forged sender no valida; SOS en un frame | Adapter contra fixtures protobuf pinneados |
| C-03 | Crypto airtime medido | Contenido/roles por incidente | SEC absoluto | N/A lógico | F-01/F-03 | Vectores authentic/forged/replay/revoked; cero false acceptance | Implementar sólo vectores y schema en P0 |
| C-04 | Hubs fuera de cadena local | Resúmenes mínimos | SEC+OPS; malicious hub | Backhaul aplicable | F-03/F-04/C-03/C-06 | 50k sites/60 cells/5 areas/2 hubs; 24h partition; cero overwrite | Simulador masivo antes de hubs reales |
| C-05 | Carga separada | Alta; unverified distress | SEC+PRV+UX | RF/network local | C-02/C-03/C-09 | Sin clave compartida; allowlist; mensaje civil no escribe facts | Simular 10 clientes civiles y gateway hostil |
| C-06 | Bajo; storage dimensionado | Bundle minimizado/cifrado | SEC+C; custody | Transporte físico local | F-03/F-04/C-03 | Duplicado/tardío/conflictivo idempotente; firma y expiry | Comparar file bundle mínimo vs BPv7 POC |
| C-07 | Mayor consumo | Raw sólo autorizado | SEC+RF coexistence | Banda/infra local | C-04/C-09 | Failover sin exponer MQTT; throughput suficiente para artefacto aprobado | Ethernet/Wi-Fi local con gateway outbound-only |
| C-08 | Airtime crítico | Sólo resúmenes | RF+SEC+OPS | Perfil separado | C-03/C-04/C-09 | No degrada SOS/telemetría; hops/airtime y kill switch | Mantener simulado hasta demostrar necesidad sin backhaul |
| C-09 | Duplication/failover presupuestados | Selección minimiza disclosure | SEC+RF+OPS; dedup/anti-loop | Cada bearer conserva perfil | F-01/F-03/C-03 | Mismo ID por dos bearers produce un mensaje lógico y receipts separados; fallback no cicla | Replay Meshtastic+MeshCore+carry con partición y duplicados |
| A-01 | Medir Link/announce/transfer | Source-address privacy no basta | No audit externo; forwarding sin prioridad | Perfil RF/IP por interface | C-03/C-09 | Mismo envelope; SOS priorizado antes del interface; no airtime leak entre boundaries | Adapter/replay y luego RNode conducted contra workload común |
| A-02 | Repeater fijo y companion medidos | Path/keys/location sensibles | Defaults eliminados; legacy/path churn/flood | Perfil RF propio | C-03/C-09 | Direct, group y movilidad medidos; cero silent drop no declarado; 64 hops no es acceptance | Adapter/replay y luego hardware reutilizable conducted |
| A-03 | Desconocida | Diseñable | Todo SEC/RF desde cero | Completa | C-03/C-09 + comparative failure | Sólo reabrir si ninguna alternativa cumple un requisito medido | Documentar requisito imposible y comparative failure |
| A-09 | Alto frente a LoRa | IP/MAC/topología sensibles | SEC+RF; segmentación y updates | 2.4/5/6 GHz/local | C-03/C-09 | Reconverge sin loop; throughput/energía superan bearer LoRa para artefacto aprobado | Babel vs batman-adv en namespace/emulación, luego routers |
| A-10 | Bajo por nodo; border router aparte | IPv6/topología sensibles | SEC+SCI; commissioning | 2.4 GHz/local | F-01/F-03/C-09 | Cluster opera sin cloud; pérdida de border router no pierde sensing; coexistencia medida | OpenThread simulado con 12 sensores y dos border routers |
| A-11 | Relay consume y agrega failure domain | DevEUI/metadata | LoRaWAN SEC completo | TS011+perfil RF | C-01/C-09 | Extiende coverage máquina sin rollback/counter loss; no se usa para mensajes humanos | Revisar compatibilidad NS/end-device antes de hardware |
| A-12 | Radio/terminal según equipo | Voz/identidad muy sensibles | OPS+SEC; no recording default | Licencia/servicio aplicable | C-09 + SOP operacional | Voice plane funciona separado; OpenBREC no controla PTT ni interpreta contenido | Capability inventory y SOP, sin integración inicial |
| A-13 | Alto/variable | Proveedor/location metadata | SEC+OPS+cost; no dependencia | Operador/banda aplicable | C-04/C-06/C-09 | Desconexión no afecta cell; gateway outbound-only y carry fallback | Emular link intermitente/costoso antes de contratar |

## 8. Beacons, sensores y terminales

### 8.1 Decisión

| ID | Funcionalidad | Valor/evidencia | Alternativa desacoplada | Reuso o build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| B-01 | Terminal de rescatista/operador | V5/A | Radio dedicada/papel + gateway | BUILD PWA; ADAPT teléfono/tablet | L | M5/M1 | GO-P0→P1a |
| B-02 | Terminal entregable no preparado | V5/B | Botón físico/radio simple | BUILD UX; ADAPT terminal+LoRa | L | M4/M1 | GO-P0→P1a |
| B-03 | Beacon acústico `features_only` | V5/B | Escucha humana/dispositivo USAR comercial | ADAPT mic/MCU; BUILD features/contract | L | M4/M1 | GO-P0→P1a |
| B-04 | Snippet acústico activado | V4/B | Revisión física/local | BUILD vault/control; ADAPT storage | L | M4/M1 | GO-P1a |
| B-05 | PIR/movimiento | V3/B | IMU/sísmica/mmWave | ADAPT sensor commodity | M | M5/M1 | GO-P0→P1a |
| B-06 | Térmica baja resolución | V4/B | Cámara térmica/visual o mmWave | ADAPT matriz; BUILD features | L | M4/M1 | GO-P0→P1a |
| B-07 | Beacon tri-modal, tres unidades | V5/C | Beacons single-modality coordinados | BUILD integración abierta; sensores sustituibles | XL | M3/M1 | GO-P1a→P1b |
| B-08 | Beacon como relay+sensing | V4/B | Relay y sensor separados | ADAPT mismo gabinete sólo con failure isolation | L | M4/M1 | GO-P1a |

### 8.2 Modalidades futuras

| ID | Funcionalidad | Valor/evidencia | Alternativa | Reuso/build | Esfuerzo | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|---|
| A-04 | Vibración/sísmica | V4/B | Acústica/PIR | ADAPT sensor; schema propio | L | M4/M0 | WATCH-P1 |
| A-05 | CO2/calidad de aire | V2/C | Térmica/acústica | ADAPT sensor calibrado | M | M4/M0 | DEFER |
| A-06 | UWB para nodos/rescatistas conocidos | V3/A | GNSS/fiducials | ADAPT anchors/tags | L | M5/M0 | WATCH-P1 |
| A-07 | mmWave presence cross-check | V3/B | PIR/térmica | ADAPT eval kit | L | M4/M0 | DEFER |
| A-08 | Cámara/óptica y media de alto ancho de banda | V4/A | Search camera comercial/inspección humana | ADAPT; no LoRa raw | XL | M5/M0 | DEFER |

### 8.3 Gates y aceptación

| ID | Energía | Privacidad | Safety/ciencia | Regulación | Dependencias | Criterio de aceptación | Próximo experimento |
|---|---|---|---|---|---|---|---|
| B-01 | Load profile real | Ubicación/actor local | UX+SEC | Dispositivo/radio | F-02/F-03/C-03/C-09 | Offline; coverage/missing visibles; no absence; 8 operadores y ≥90% task completion | Prototipo lógico con fixtures, luego visual design |
| B-02 | Reserva SOS L0 | Location/estado sensible | UX+SEC absoluto | Red humana | B-01/C-03/C-09 | 8/8 comprende estados; cero SOS/cancel accidental; queue visible | Wireflow offline con estados append-only |
| B-03 | Duty cycle medido | Features-only default | SCI+PRV; no identidad | Captura local aplicable | F-01/F-03/E-01 | 100 trials/clase +20 beacon-hours/entorno; unknown/OOD; no raw | Fixture/audio consentido y feature baseline CPU |
| B-04 | Storage/radio no automático | Alta; vault/roles/hold | PRV+SEC+OPS | Audio/local | F-04/B-03 | ≤15s; dual auth o break-glass; nada sin review se borra | P0 retention fault test; P1 audio controlado |
| B-05 | Bajo/medido | Bajo-medio | SCI; no ocupación/inmovilidad | N/A | F-01/F-03/E-01 | Sólo motion window; masking/moved node; no absence | PIR bench con movimiento, inmovilidad y heat interference |
| B-06 | Medio/medido | Grid sensible | SCI+PRV; no body/medical | N/A | F-01/F-03/E-01 | Features/uncertainty; raw grid sólo autorizado; hot-source confounders | Matriz low-res contra fuentes calibradas |
| B-07 | Entra en 72h chain | Multiplica coverage data | SCI+UX+OPS | RF si transmite | B-03/B-05/B-06/E-01/C-09 | Cero confirmación/ausencia; corroboración no independiente; relay/node loss visible | 1 beacon primero, luego 3 en training site |
| B-08 | Relay desplaza sensing | Gaps/coverage visibles | RF+EN+SCI | Perfil RF | B-07/C-09 | SOS priority sin pérdida silenciosa; sensing local sigue con backhaul caído | Fault injection relay-off/sensor-on y viceversa |
| A-04 | Medir | Señal ambiental sensible | SCI; geometry/sync | N/A | B-03/B-05 | Reabrir si acústica no cubre una clase y sensor aporta evidencia independiente | Benchmark contra acoustic baseline |
| A-05 | Calibración/heat | Ambiente/ocupación | SCI fuerte; no presence claim | Sensor/local | F-05/B-06 | Reabrir sólo con protocolo de entorno y ground truth | Literature/protocol review, no hardware aún |
| A-06 | Anchors consumen energía | Tracking sensible | SEC+SCI; sólo tags conocidos | UWB local | F-03/C-09 | Error medido para nodos/rescatistas; nunca víctimas pasivas | 4 anchors/2 tags en banco después de M0 |
| A-07 | Alto | Potencial presencia sensible | SCI+PRV+model card | Banda/hardware | B-05/B-06 | Gana información sobre tri-modal en blind test | Mantener eval kit fuera de compra hasta baseline |
| A-08 | Alto/backhaul | Muy alta | PRV+OPS; consent/access | Captura/local | C-07/F-04 | Search workflow y red separada; no identidad automática | Evaluar integración de cámara USAR comercial, no construir primero |

## 9. Funcionalidades prohibidas o fuera de frontera

| ID | Funcionalidad | Estado | Razón | Revisión posible |
|---|---|---|---|---|
| X-01 | Jamming, interferencia deliberada o TX continuo | PROHIBITED | Daña comunicaciones y contradice safety | Sólo cambio explícito de misión/gobernanza; fuera de OpenBREC actual |
| X-02 | Emulación celular/servicios o suplantación | PROHIBITED | Ofensivo, legal y éticamente incompatible | No prevista |
| X-03 | Ausencia de víctima por silencio/sensor negativo | PROHIBITED | Falso negativo life-safety | No prevista |
| X-04 | Biometría, voiceprint, identidad o atributos sensibles | PROHIBITED | No requerida y alto riesgo | Nueva especificación y mandato externo, no addon implícito |
| X-05 | Audio remoto continuo | PROHIBITED | Vigilancia, ancho de banda y alert fatigue | Sólo cambio explícito; snippets siguen siendo alternativa |
| X-06 | Hub/cloud/CA central en camino crítico | PROHIBITED | Rompe autonomía recursiva | No; puede existir como mejora no crítica |
| X-07 | PSK común de desastre o credencial default | PROHIBITED | Compromiso e impersonation masivos | No prevista |

## 10. Secuencia de decisión — no implementation plan

### 10.1 M0 exit obligatorio

Orden:

1. `M0-01`: ADR-0001, catálogo core y legacy inventory.
2. `M0-02`: schemas/fixtures y generación Pydantic/TypeScript.
3. `M0-03`: servicios mínimos y Compose build/start offline.
4. `M0-04`: accepted log, vault/quarantine/ledger y replay determinístico.
5. `M0-05`: simulador 6 nodos/3 zonas y PWA mínima de mapa/timeline/explanation.
6. `M0-06`: gates CI separados y receipts.

Exit:

- todos los servicios existen y arrancan offline;
- contratos/fixtures pasan y modelos no difieren;
- replay adapter/core produce hashes estables;
- invalidez, preservación y rechazo no pierden datos silenciosamente;
- UI muestra incertidumbre, fuentes y capacidades ausentes;
- threat/privacy/security gates generan artefactos.

Si M0 no pasa, no comienza implementación addon. La documentación y fixtures pueden seguir refinándose.

### 10.2 P0 — completamente simulado

Orden:

1. `P0-01`: schemas addon y fixtures de energía, radio, `TransportProfile`, bearer capability, policy decision, federación, terminal y beacon.
2. `P0-02`: EnergyDomain/FSM/budget y brownout replay.
3. `P0-03`: HumanMessage protegido, SOS append-only, revocación, dedup/anti-loop multi-bearer y malicious transport.
4. `P0-04`: comparación Meshtastic/MeshCore/Reticulum por perfiles mobile, planned y heterogeneous con workloads comunes.
5. `P0-05`: federation/reconciliation a 50.000 sites, 60 cells, 5 areas y 2 hubs.
6. `P0-06`: terminal offline y copy safety sin ausencia/garantía.
7. `P0-07`: beacon observations, health, deterministic fusion, review y retention fault injection.
8. `P0-08`: campaña integrada con partición 24h, node loss, brownout, forged distress, spoofed sensor y hub hostil.
9. `P0-09`: matriz de receipts, support status por perfil y decisión de hardware piloto.

Exit:

- cero false `operator.accepted`;
- cero outputs de presencia confirmada/ausencia automáticos;
- cero overwrite o pérdida silenciosa;
- toda celda sigue operando aislada;
- energía/radio/sensing degradan con estado visible;
- cada hardware candidate conserva `unverified` hasta P1;
- ningún protocolo obtiene support global; la decisión queda por `TransportProfile`.

### 10.3 P1a — banco y conducted

Orden:

1. `P1a-01`: comprar/prestar una unidad por categoría candidata, priorizando hardware reutilizable; capability manifests exactos.
2. `P1a-02`: LoRaWAN, Meshtastic, MeshCore y RNode conducted/dummy load; seguridad, frame, airtime, goodput, path churn y legacy downgrade.
3. `P1a-03`: terminal offline con 8 operadores y 8 personas no preparadas.
4. `P1a-04`: un beacon tri-modal aislado; calibración y datasets controlados.
5. `P1a-05`: tres beacons; overlap, node movement, relay loss y false alerts.
6. `P1a-06`: caracterizar potencia, inrush, capacidad, paths y source transitions de la configuración ya elegida.
7. `P1a-07`: ensayo storage-only de 72 horas con cadena L0/L1 real y margen 1.25×.
8. `P1a-08`: integración de tres ResponseCells por cable/IP local, sin TX exterior.

Exit:

- todos los manifests coinciden con hardware exacto;
- radio/security/coexistence conducted pasan;
- support status de cada bearer queda limitado a perfiles y versiones ensayados;
- UX critical comprehension pasa;
- beacon reporta performance completa por entorno;
- 72 horas pasan con reservas y cero interrupción crítica;
- safety review habilita o rechaza P1b por perfil.

### 10.4 P1b — campo controlado y TX radiado

Orden:

1. `P1b-01`: regulatory/coexistence profile, double auth, break-glass, expiry y kill switch drill.
2. `P1b-02`: sesión radiada acotada; near-far, co-site, congestion y relay loss.
3. `P1b-03`: solar central y por nodo; MPPT, sombra, mounting y source loss.
4. `P1b-04`: estación/generador controlado con CO/fuel/stop y sin autostart inicial.
5. `P1b-05`: training site con tres beacons, actores consentidos y cinco corridas.
6. `P1b-06`: dos hubs, tres cells y backhaul perdido/restaurado.
7. `P1b-07`: campaña integrada con review/handoff y resultados negativos.

Exit:

- cada TX tiene modo, alcance, actores, TTL y receipt;
- ninguna interferencia perjudicial persiste;
- solar/generador no comprometen reserva ni safety;
- field claims quedan limitados al escenario;
- hub/node/source loss no detiene operación local;
- Product/Privacy/Safety/Operations firman el gate P2.

### 10.5 P2 — ejercicio multi-equipo

P2 no replica físicamente 50.000 sitios o 60 cells. Combina hardware-in-the-loop con simulación masiva:

1. `P2-01`: cinco OperationalAreas simuladas y varias cells físicas representativas.
2. `P2-02`: siete días de energía mixta con 24h sin generación.
3. `P2-03`: múltiples environment classes de beacons con thresholds pre-registrados.
4. `P2-04`: terminales, red civil separada opcional, distress y handoffs entre equipos.
5. `P2-05`: pérdida de ambos hubs, red, source, relay y terminal; reconciliación posterior.
6. `P2-06`: informe ciego de SLOs, false alerts, omissions, privacy, safety y costo operativo.

Exit:

- SLOs se cumplen sólo para el escenario versionado;
- cero false acceptance/confirmation/absence;
- 100% de pérdidas y gaps se reportan;
- operación local continúa bajo partición;
- resultados negativos y excepciones quedan publicados;
- la siguiente decisión separa `supported`, `experimental`, `unverified` y `unavailable` por perfil exacto.

## 11. Orden recomendado por valor inmediato

1. F-01–F-06: M0 real.
2. C-03 y F-04: autenticidad/preservación antes de transportar SOS.
3. E-01: energía como contrato y degradación, antes de comprar storage.
4. C-09/C-03: selector, envelope, dedup y seguridad antes de elegir bearer.
5. C-01/C-02/A-01/A-02: LoRaWAN y comparación Meshtastic/MeshCore/Reticulum por perfil, no mesh propio.
6. C-04/C-06: federation event y store-and-forward antes de hubs físicos.
7. B-01/B-02: semántica terminal offline antes de styling final.
8. B-03/B-05/B-06: modalidades individuales antes de B-07 tri-modal.
9. E-02/E-03: almacenamiento y cargas reales; luego 72 horas.
10. E-04/E-05/E-06: extensiones de generación en P1b.
11. C-05/C-08/A-04–A-13: sólo según el estado y gate específico de cada fila.

## 12. Reglas de procurement

- Una unidad por categoría antes de compra en escala.
- Verificar chipset, firmware, conectores, región, BMS, capacidad y drivers exactos.
- Ningún vendor claim sube de `unverified` sin receipt propio.
- Preferir hardware reutilizable entre Meshtastic, MeshCore, RNode, LoRaWAN o test fixtures cuando no mezcle failure domains ni invalide la comparación.
- Mantener repuestos de cables, conectores, antenas, sensores y baterías consumibles.
- No comprar solar/generador antes de medir loads.
- No comprar mmWave/cámara/mesh alternativo antes del baseline que justifique el experimento.

## 13. Review triggers de la watchlist

| Opción | Reabrir cuando |
|---|---|
| Meshtastic | Restringir o cambiar de perfil cuando flooding/airtime, 7 hops, group security o densidad no cumplan el workload medido. |
| MeshCore | Avanzar a hardware sólo si planned-repeater P0 supera path churn, group flood, legacy silent-drop y defaults/security gates. |
| Reticulum/RNode | Avanzar a hardware sólo si heterogeneous-backbone P0 controla announces, prioridad SOS, 297-byte Link setup y complejidad operacional. |
| Mesh propio | Dos alternativas abiertas fallen el mismo requisito obligatorio con evidencia. |
| LoRa federation-relay | Backhaul IP/físico no cubra un resumen crítico y el airtime SOS siga protegido. |
| Malla IP Babel/`batman-adv` | Exista energía y una carga local que exceda LoRa; comparar convergencia, throughput, privacidad y segmentación. |
| Thread/OpenThread | Un cluster de sensores cercano justifique 802.15.4 y pueda operar ante pérdida del border router. |
| LoRaWAN Relay | Falte cobertura de gateway para el plano máquina y exista compatibilidad TS011 end-to-end verificable. |
| LMR/VHF/UHF | La voz sea requisito operacional y exista perfil regulatorio/equipo autorizado; mantener plano separado. |
| Backhaul oportunista | Exista proveedor/enlace disponible y la caída total siga cubierta por operación local y carry bundle. |
| Sísmica/vibración | Acústica no cubra golpes/vibración y el nuevo sensor aporte evidencia independiente. |
| CO2/air quality | Exista protocolo BREC con ground truth que evite claims de presencia. |
| UWB | Se necesite localizar equipos/nodos conocidos y GNSS/fiducials no alcancen. |
| mmWave | El baseline tri-modal deje una clase de entorno relevante y el blind test muestre ganancia. |
| Cámara/óptica | Exista backhaul/storage/privacy capacity y no sea más eficiente integrar equipo USAR existente. |

## 14. Riesgos de la priorización

- M0 puede absorber más trabajo del previsto y retrasar evidencia física; no se lo saltea.
- El entusiasmo por hardware puede adelantar compras antes de definir loads/contracts.
- Un transporte popular puede crear lock-in si el overlay y adapters no permanecen separados.
- Una tasa de detección buena en laboratorio puede generar alert fatigue o false confidence en rubble.
- El modo `emergency_assumed_risk` puede normalizarse indebidamente; cada uso expira.
- P2 puede parecer validación operacional amplia cuando sólo cubre un escenario.
- La matriz puede quedar obsoleta por firmware, regulación o hardware; cada row requiere fecha de review.

## 15. Fuentes de evidencia

Autoridad interna:

- `2026-07-16-openbrec-core-contracts-replay-design.md`
- `2026-07-17-openbrec-radio-security-regulation-design.md`
- `2026-07-17-offgrid-communications-state-of-art.md`
- `2026-07-17-openbrec-energy-design.md`
- `2026-07-17-openbrec-beacons-human-ux-design.md`
- `OpenBREC-RF-threat-model.md`

Referencias externas:

- LoRaWAN specifications: https://resources.lora-alliance.org/technical-specifications
- ChirpStack architecture: https://www.chirpstack.io/docs/architecture.html
- Meshtastic encryption: https://meshtastic.org/docs/overview/encryption/
- Meshtastic mesh algorithm: https://meshtastic.org/docs/overview/mesh-algo/
- Meshtastic LoRa/max hops: https://meshtastic.org/docs/configuration/radio/lora/
- Meshtastic device roles: https://meshtastic.org/docs/configuration/radio/device/
- Meshtastic MQTT: https://meshtastic.org/docs/software/integrations/mqtt/
- Reticulum/RNode: https://reticulum.network/manual/ and https://github.com/markqvist/Reticulum
- MeshCore: https://github.com/meshcore-dev/MeshCore and https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md
- LoRaWAN Relay TS011: https://resources.lora-alliance.org/technical-specifications/ts011-1-0-0-relay
- Babel RFC 8966: https://www.rfc-editor.org/rfc/rfc8966.html
- Linux batman-adv: https://www.kernel.org/doc/html/latest/networking/batman-adv.html
- OpenThread: https://openthread.io/
- IETF Bundle Protocol v7: https://www.rfc-editor.org/rfc/rfc9171.html
- IEC 62619:2022: https://webstore.iec.ch/en/publication/64073
- UNECE Manual of Tests and Criteria Rev.8: https://unece.org/transport/standards/transport/dangerous-goods/un-manual-tests-and-criteria-rev8-2023
- U.S. DOE Solar and Resilience: https://www.energy.gov/cmei/systems/solar-and-resilience-basics
- OSHA generator/CO safety: https://www.osha.gov/news/newsreleases/osha-trade-release/20230207
- INSARAG Guidelines: https://insarag.org/methodology/insarag-guidelines/
- ICRC humanitarian data protection: https://www.icrc.org/en/data-protection-humanitarian-action-handbook
- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- NIST AI RMF: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10

## 16. Gate de aprobación

Si se aprueba esta matriz, el siguiente paso no es implementar addons. Es actualizar `DELIVERY_BOARD.md` y escribir un plan M0 ejecutable que cierre únicamente F-01–F-06, con tasks pequeñas, responsables, comandos y evidencias. P0 se planifica después de demostrar M0 exit.
