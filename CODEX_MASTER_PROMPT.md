# Codex Master Prompt — construir OpenBREC RF

Actúa como arquitecto principal, ingeniero de radio defensiva, desarrollador de sistemas distribuidos y especialista en software para operaciones de emergencia. Construye un repositorio production-minded pero claramente marcado como plataforma experimental de apoyo BREC/USAR.

## 1. Misión
Crear una plataforma modular que despliegue nodos económicos alrededor de una estructura colapsada y fusione evidencias de:
- metadatos Wi-Fi pasivos;
- anuncios BLE;
- Wi-Fi CSI de enlaces controlados;
- BFI cuando exista infraestructura compatible;
- energía y eventos de espectro mediante SDR en recepción;
- 802.15.4/Thread/Zigbee;
- UWB, mmWave, acústica, sísmica y sensores de puerta/void como plugins opcionales.

El producto debe presentar un mapa de sectores y vacíos con indicios, confianza, fuentes y evolución temporal. Nunca debe declarar por sí solo que hay una víctima viva.

## 2. Innovación central
No construir otro radar comercial. Construir una plataforma abierta de **radio-tomografía oportunista y fusión adaptativa**:
- reutilizar herramientas de observación de ciberseguridad en modo pasivo;
- formar múltiples enlaces controlados Tx/Rx alrededor de escombros;
- comparar cambios de canal y patrones temporales entre enlaces;
- usar antenas omni y direccionales intercambiables con perfiles calibrados;
- combinar emisiones de dispositivos, perturbación física del canal y geometría del colapso;
- degradar capacidades de forma honesta cuando faltan sensores.

## 3. Límites de seguridad
PROHIBIDO:
- deauth/disassociation;
- jamming o interferencia intencional;
- evil twin/rogue AP que suplante redes existentes;
- captura de contraseñas, handshakes con objetivo de cracking, portales engañosos;
- inspección de payloads de usuarios;
- IMSI catcher o suplantación celular;
- transmisión SDR fuera de bancos controlados y autorizados.

PERMITIDO:
- monitor mode pasivo;
- inventario de metadatos y potencia recibida;
- AP/STA propios y claramente identificados para CSI/BFI experimental;
- red abierta de rescate no suplantadora, con consentimiento y portal informativo;
- SDR receive-only;
- pruebas en entornos propios/autorizados.

## 4. Arquitectura requerida
Monorepo:
```
apps/
  api/
  web/
  fusion-worker/
collectors/
  kismet/
  ble-bluez/
  esp-csi/
  bfi-wibfi/
  sdr-soapysdr/
  ieee802154/
firmware/
  esp32-csi-node/
  esp32-drop-node/
packages/
  contracts/
  geometry/
  confidence/
  privacy/
infra/
  compose/
  migrations/
  dashboards/
fixtures/
  synthetic/
  replay/
docs/
```

### Servicios mínimos
- `mqtt`: Mosquitto con autenticación local.
- `api`: FastAPI, REST + WebSocket.
- `fusion-worker`: ventanas temporales, asociación, tracks, mapas de confianza.
- `postgres`: eventos normalizados, despliegues, sensores, pistas y auditoría.
- `web`: PWA offline con mapa/plano, timeline y salud de nodos.
- `collector-kismet`: transforma Kismet a `RadioObservation`.
- `collector-ble`: BlueZ/nRF ingest.
- `collector-csi`: recibe ESP-NOW/UDP/serial y normaliza CSI.

### Plugins posteriores
- `collector-bfi`: integra Wi-BFI sin acoplar el core.
- `collector-sdr`: SoapySDR/rtl_power, inicialmente energía por banda y eventos.
- `collector-uwb`, `collector-mmwave`, `collector-acoustic`.

## 5. Modelo de dominio
Implementar entidades:
- Incident
- Deployment
- Zone
- VoidHypothesis
- SensorNode
- SensorCapability
- AntennaProfile
- Observation
- Evidence
- Track
- FusionResult
- OperatorAnnotation
- CalibrationRun
- Dataset
- ModelVersion
- AuditEvent

Separar:
1. Observation: medición cruda normalizada.
2. Evidence: interpretación acotada de una o más observaciones.
3. FusionResult: estado consolidado, siempre reversible y explicable.

## 6. Contratos
Usar los JSON Schema provistos en `schemas/`. Generar modelos Pydantic y TypeScript desde una única fuente. Versionar los eventos con semver.

## 7. Fusión v1 sin ML
- sincronización por ventanas;
- mediana/Hampel para outliers;
- EMA/Kalman configurable;
- asociación de identificadores efímeros;
- reglas de transición entre zonas;
- ponderación por calidad de sensor y geometría;
- combinación bayesiana simple o Dempster-Shafer solo si está bien testeada;
- abstención obligatoria ante conflicto o cobertura insuficiente.

## 8. ML posterior
- fingerprinting KNN/XGBoost como baseline;
- modelos temporales para CSI/BFI;
- clasificación con clase `unknown` y OOD;
- validación separada por día, configuración de escombros y ubicación de antena;
- no aceptar random split como única evaluación;
- model cards y dataset cards obligatorias.

## 9. Antenas como primera clase
Cada sensor declara:
- bandas;
- tipo omni/panel/yagi/biquad/log-periodic;
- ganancia nominal;
- beamwidth;
- polarización;
- pérdida de cable estimada;
- orientación y altura;
- fecha de calibración.

La UI debe permitir comparar barridos de sectores con distintas antenas. Implementar un `antenna_profile_id` en cada observación.

## 10. UI operativa
Pantallas:
- preparación del despliegue;
- inventario y salud de nodos;
- mapa/plano por sectores/voids;
- capa de calor por fuente;
- timeline de indicios;
- detalle explicable de una hipótesis;
- matriz de capacidades disponibles;
- modo silencio operacional;
- anotaciones del operador y marcación INSARAG/FEMA configurable;
- exportación de informe y paquete de evidencia.

No usar lenguaje absoluto. Estados: `sin evidencia`, `indicio débil`, `indicio`, `indicio convergente`, `requiere verificación`.

## 11. Seguridad y privacidad
- modo metadata-only por defecto;
- stripping de payloads antes de persistir;
- HMAC rotativo para identificadores MAC/BLE;
- claves por incidente;
- retención configurable;
- exportaciones firmadas y cifradas;
- RBAC local;
- audit log append-only;
- borrado verificable al cierre;
- threat model STRIDE y abuse cases.

## 12. Perfiles Docker
Implementar perfiles equivalentes a:
- `lab-sim`;
- `field-basic`;
- `field-csi`;
- `field-spectrum`;
- `lab-bfi`;
- `advanced-fusion`.

## 13. Gates CI
- lint/typecheck/tests;
- JSON Schema compatibility;
- no payload retention test;
- forbidden-feature scanner: falla si aparecen comandos o librerías de deauth/jamming/credential capture;
- deterministic replay test;
- offline startup smoke;
- migration round-trip;
- SBOM y secret scan;
- container non-root.

## 14. Primer incremento ejecutable
Entregar primero:
1. monorepo y compose `lab-sim`;
2. contratos y generadores;
3. simulador de 6 nodos y dos tracks;
4. API y UI con mapa de confianza;
5. collector Kismet replay desde fixture sanitizado;
6. collector BLE sintético;
7. fusión determinística;
8. documentación y scripts de instalación.

Después agregar hardware real ESP32.

## 15. Criterios de aceptación MVP
- arranca sin Internet;
- tolera pérdida de nodos;
- muestra capacidades reales;
- reproduce un escenario idénticamente;
- distingue dispositivo detectado de presencia humana inferida;
- cada resultado explica fuentes y limitaciones;
- ningún paquete conserva payloads;
- no contiene funciones ofensivas;
- soporta al menos 50 eventos/s por nodo y 12 nodos en una laptop común.

## 16. Forma de trabajo
- Crear ADRs para decisiones importantes.
- PRs pequeños y verticales.
- No introducir Kubernetes, Kafka, GPU ni microservicios extra antes de demostrar necesidad.
- Mantener un `delivery-board.md` con estado, riesgos y pruebas pendientes.
- Cuando falte hardware, implementar interfaces, simuladores y replay, no mocks engañosos.


## 18. RuView adapter

Implement `collectors/ruview-csi` behind an interface. Support ADR-018 UDP, WebSocket and file replay. Pin the reviewed upstream commit. Detect the JSONL-versus-binary-RVF mismatch and fail visibly; never emit silent null inference. Preserve raw frames and allow RuView-free operation.

## 19. Drone deployment

Implement domain contracts and simulator for `DroneDeploymentEvent`, Drop Pod FSM and MAVLink bridge. The OpenBREC service is not flight-critical and cannot arm/navigate the aircraft. Payload release requires two-step operator confirmation and a simulated safety policy. Add deterministic replay of a six-node drone deployment.

## 20. RF Quieting

Implement `IsolationProfile`, measurement runs and UI overlays. Never accept nominal fabric attenuation as enclosure performance. Compare open/curtain/enclosure baselines and annotate all observations with the active profile. Add a guard forbidding negative victim inference from quieted scans.
