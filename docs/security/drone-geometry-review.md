# Review de seguridad — drones como geometría de sensing (`drone-deployment-event`)

- Fecha: 2026-07-19
- Alcance: addon experimental `drone-deployment-event` (drop pods, relay, scan móvil; diseño contractual, sin runtime ni integración de vuelo)
- Autoridad: ADR-004, ADR-002 (sin autonomía de vuelo en OpenBREC), red lines de ADR-0001
- Base de evidencia: `docs/research/rf-sensing-state-of-the-art.md` §10
- Veredicto: aceptado como diseño `specified`/`simulated`; ninguna operación UAS queda habilitada

## Alcance

Revisión de diseño del contrato de eventos de despliegue con drones. El dron construye geometría de sensing (depositar sensores, relay, mover un punto de escucha); no es cámara ni taxi autónomo. OpenBREC registra telemetría y eventos; el autopiloto (PX4/ArduPilot como ejemplos reemplazables) conserva toda la autoridad de vuelo.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| DRN-T1 | Caída de payload sobre personas: un drop pod liberado en momento/lugar incorrecto hiere a víctimas o rescatistas. | Release automático o mal confirmado; estimación de posición errónea; viento. | Lesión física (life-safety inversa). |
| DRN-T2 | Autoridad de vuelo desplazada al core: un bug o comando de OpenBREC altera trayectoria. | Bridge con capacidad de comando; ausencia de separación contractual. | Pérdida de control de la aeronave, accidente. |
| DRN-T3 | Muestras contaminadas: datos del sensor tomados durante RELEASED/IMPACT/SETTLING entran a fusión como si fueran observaciones válidas. | FSM del drop pod no modelada; ingesta sin estados. | Candidatos falsos, confianza inflada. |
| DRN-T4 | EMI de motores: la interferencia del propio dron degrada los sensores RF que transporta sin que nadie lo registre. | Sin baseline EMI; perfiles de sensing sin corrección. | Observaciones degradadas invisibles. |
| DRN-T5 | Operación fuera de geofence/lost-link: pérdida de enlace con comportamiento no declarado. | Geofence/lost-link no documentados en el evento. | Aeronave fuera de control sobre el incidente. |
| DRN-T6 | Percepción de vigilancia: un dron sobre el incidente percibido como plataforma de monitoreo de personas. | Comunicación pública ausente; payload ambiguo. | Daño social/legal, obstrucción del operativo. |

## Controles

- **Contrato `drone-deployment-event`**: `flight_authority_in_core: false` como const (ADR-002: el autopiloto conserva el vuelo; OpenBREC sólo telemetría y payload); `drop_sample_states_excluded_from_fusion: [RELEASED, IMPACT, SETTLING]` fijado como consts del array (las muestras de caída nunca fusionan).
- **Release con confirmación humana**: `release_mode` con variantes de confirmación humana; la guía `drone-geometry.md` especifica handshake de doble confirmación para cualquier liberación de payload.
- **Eventos de geometría y EMI**: el enum incluye `node_position_estimate` y `drone_emi_baseline` (brecha doc-vs-schema resuelta en la migración): la posición estimada del nodo depositado y la baseline de interferencia de motores quedan registradas como eventos.
- **Geofence/lost-link**: documentados en la guía y en `hardware/drone-interface.md`; la telemetría normalizada no incluye comandos de vuelo.
- **Regulación**: FAA SGI / Public Safety Shielded Operations como ejemplo estadounidense; verificación local obligatoria por jurisdicción (`regulatory.md`).

## Riesgo residual

- La doble confirmación es contractual y procedimental; un integrador puede cablear un release automático fuera del contrato. Sin runtime no hay enforcement técnico.
- La separación de autoridad depende del bridge: un bridge mal implementado puede introducir comandos de vuelo; la revisión de ese bridge será un gate propio cuando exista.
- Payloads RF open-source en drones: `specified`/`simulated`, sin casos SAR documentados; la utilidad real es `unverified`.

## Declaración de madurez

Review de **diseño** sobre contrato `specified`. Drones USAR con cámara térmica son `field-validated` **externos** (capacidad ajena, fuera del core); los payloads RF open-source son `specified`/`simulated`. Nada de esta review habilita runtime, hardware, vuelo ni campo.
