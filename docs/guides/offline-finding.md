# Detección pasiva de redes de localización crowdsourced (Find My / Find Hub / SmartThings Find)

## Objetivo

Observar, sólo por recepción pasiva BLE, los anuncios de las redes de localización crowdsourced (Apple Find My, Google Find Hub, Samsung SmartThings Find) como **indicio débil** de presencia de un dispositivo — y potencialmente de una persona — en un sector de búsqueda.

## Audiencia

Integradores de sensores BLE, operadores de consola y responsables de privacidad/safety.

## Prerrequisitos

Nodo con receptor BLE en modo observación, handling policy aceptada, roster del propio despliegue para exclusión de falsos positivos y ventana de correlación local definida.

## Capacidades necesarias

`OfflineFindingObservation`, seudonimización `incident_rotating_hmac` y fusión que respete `fusion_weight: low` y `alert_trigger_allowed: false`.

## Alternativas permitidas

Cualquier receptor BLE capaz de registrar manufacturer/service data sin conectar (ejemplos reemplazables: ESP32 en modo sniffer, dongle BLE en Linux, Kismet con fuente BTLE). Ningún fabricante es obligatorio.

## Componentes e interfaces

Qué puede ver un nodo pasivo, sin conexión GATT:

- **Apple Find My** (`apple_find_my`): BLE manufacturer data con company ID `0x004C` y payload type `0x12`; la clave pública P-224 rota (~15 min en iPhone; AirTag rota ~1 vez/día). Un iPhone 11+ apagado sigue emitiendo durante horas por reserva de batería. Un AirTag en estado *Connected* (cerca de su dueño) **no emite**.
- **Google Find Hub** (`google_find_hub`): BLE Service Data UUID `0xFEAA`, frame types `0x40`/`0x41`, EID SECP160R1 rotativo (~1024 s), spec pública FMDN v1.3. La agregación está activada por defecto: un dispositivo aislado puede no ser reportado por la red, pero su anuncio BLE sigue siendo observable localmente.
- **Samsung SmartThings Find** (`samsung_smartthings_find`): observable, pero con spec cerrada; la clasificación es más heurística (USENIX Security 2023) → `frame_pattern: undocumented`.

El `frame_pattern` registra sólo el patrón de cabecera (p.ej. `0x004C/0x12`), nunca el identificador. El `subject_ref` es un HMAC rotativo por incidente computado en el borde; el EID/clave cruda se descarta tras la ventana de correlación local (`raw_identifier_retained: false`).

## Pasos

1. Configurar el nodo en recepción pasiva pura; prohibir cualquier conexión GATT (`passive_only: true`, `gatt_connection_attempted: false`).
2. Cargar el roster del propio despliegue (rescatistas llevan estos dispositivos) y aplicar la exclusión (`own_fleet_exclusion_applied: true`).
3. Registrar patrón de frame, RSSI con incertidumbre y ventana; seudonimizar en el borde.
4. Toda lectura de ritmo ("ritmo compatible con AirTag separado") va en `classification_hypothesis` con `statement_kind: hypothesis` y `confidence`, nunca como hecho.
5. Fusionar con peso bajo: este indicio jamás dispara una alerta por sí solo.

## Resultado esperado

Un flujo de indicios débiles, seudonimizados y explicables que puede priorizar la revisión humana de un sector, sin identificar personas ni elevar claims.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; los fixtures inválidos demuestran el rechazo de `gatt_connection_attempted`, `identification_attempted`, `raw_identifier_retained`, `alert_trigger_allowed` y `silence_means_absence` en `true`.

Replay determinístico del dominio (frames Apple/Google, ventana silenciosa con abstención, exclusión de flota propia, hipótesis de ritmo y rechazo visible de registros activos o con identificador crudo):

```bash
uv run --offline python -m openbrec.verify rf-sensing-offline-finding
```

## Fallos comunes y recuperación

Falso positivo del propio equipo: revisar cobertura del roster y registrar la omisión como limitación. Ráfagas de un solo dispositivo en movimiento (un rescatista, un vehículo): correlacionar con tracks antes de asignar cualquier hipótesis. Patrón no reconocido: clasificar `unknown`/`unknown_pattern` y abstenerse.

## Safety, privacidad y preservación

La recepción pasiva de broadcasts BLE es el lado de bajo riesgo de la línea metadata-vs-contenido (ver [marco regulatorio](regulatory.md)). El trabajo anti-stalking (IETF DULT) obliga a que estos trackers sean detectables; las leyes anti-stalking criminalizan **colocar** trackers para seguir personas, no detectarlos pasivamente. Los identificadores (EID/clave P-224) son unlinkable por diseño de las redes; OpenBREC refuerza eso con HMAC rotativo por incidente y prohibición de retener el identificador crudo. **Uso inverso legítimo:** emitir beacons propios (p.ej. OpenHaystack en ESP32) para marcar la posición de equipos o zonas propias es emisión propia documentada con consentimiento del equipo, no suplantación — declararla en el perfil del incidente.

## Estado de evidencia

El dominio sigue `specified`: no existe literatura SAR publicada de detección pasiva de estas redes y `max_declared_evidence: bench-validated` es el tope declarable del contrato. El addon `offline-finding-observation` (contrato + replay determinístico con peso `low` verificado, exclusión de flota y abstención) queda en `simulated` (gate `rf-sensing-offline-finding`, receipt en `evidence/rf-sensing/`). Para subir el dominio: medir rango de detección bajo escombros, prevalencia regional de cada red, tasa de falsos positivos (incluido el equipo propio) y duración de emisión post-apagado por modelo.

## Qué no demuestra

Un anuncio observado no demuestra presencia de una persona (el dispositivo puede estar perdido, descartado o en un vehículo). El silencio no demuestra ausencia — aún más fuerte que en otros dominios: teléfono apagado sin reserva, Bluetooth deshabilitado, Find My/Find Hub deshabilitado, AirTag en estado *Connected*, agregación de Google o atenuación por escombros silencian el indicio.

## Contratos normativos relacionados

[OfflineFindingObservation](../../schemas/addons/1.0.0/offline-finding-observation.schema.json), [catálogo de addons](../../schemas/addons/catalog.json), [PassiveRfObservation](../../schemas/addons/1.0.0/passive-rf-observation.schema.json) y [RFC-0002](../open-spec/rfc/0002-offline-finding-addon.md).

## Fuentes

- OpenHaystack (PoPETs 2021): https://github.com/seemoo-lab/openhaystack
- macless-haystack: https://github.com/dchristl/macless-haystack
- FindMy.py: https://github.com/malmeloo/FindMy.py
- AirTag reverse engineering (Adam Catley): https://adamcatley.com/AirTag.html
- Google Find Hub (FMDN) spec: https://developers.google.com/nearby/fast-pair/specifications/extensions/fmdn
- GoogleFindMyTools: https://github.com/leonboe1/GoogleFindMyTools
- Samsung SmartThings Find (USENIX Security 2023): https://www.usenix.org/conference/usenixsecurity23/presentation/yu
- IETF DULT (Detecting Unwanted Location Trackers): https://datatracker.ietf.org/doc/draft-ietf-dult-finding/
- Agregación por defecto en Find Hub (9to5google, jul 2024): https://9to5google.com/2024/07/29/google-find-my-device-aggregation/
- Find My tras apagado (MacRumors, iOS 15): https://www.macrumors.com/guide/find-my/
