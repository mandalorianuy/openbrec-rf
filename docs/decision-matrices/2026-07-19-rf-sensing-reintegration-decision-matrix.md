# Matriz de decisión: reintegración de dominios de RF sensing como addons experimentales

- Estado: matriz aprobada; reintegración ejecutada como Fase 6 del roadmap
- Fecha: 2026-07-19
- Alcance: dominios CSI/radio-tomografía, RF pasiva, SDR receive-only, drones como geometría, RF quieting y RuView
- Autoridad de entrada: [`docs/research/rf-sensing-state-of-the-art.md`](../research/rf-sensing-state-of-the-art.md) (tabla §14 como fuente de verdad editorial) y ADR-004
- Condición: autoriza contratos, fixtures, guías y reviews; no autoriza implementación de collectors, compra, TX ni despliegue

## 1. Veredicto ejecutivo

Los seis dominios de RF sensing de la encarnación previa se **reintegran como addons experimentales** (`schemas/addons/1.0.0/`, `status: experimental`), no al core ni como capacidades validadas. La alternativa "addons" ganó porque:

1. conserva la frontera core/addon de ADR-0001 (el core no conoce protocolos de radio ni modalidades concretas);
2. permite fijar invariantes de safety como consts de contrato verificables por fixtures;
3. mantiene los estados de evidencia honestos por dominio, sin contaminar los gates del core;
4. deja a Lifeseeker/Wi2SAR fuera del perímetro como referencias externas con boundary flag.

Recomendaciones principales:

- `BUILD` (contratos/guías): los seis addons con invariantes de safety como consts y fixtures válidos/inválidos.
- `ADAPT`: toolchains comunitarios (esp-csi, Nexmon, Kismet, SDR++, KrakenSDR, PX4/ArduPilot) como ejemplos reemplazables citados por guía, nunca como norma.
- `WATCH`: silicio 802.11bf para interop CSI real; evidencia de RF quieting en SAR; primer despliegue documentado de CSI/RTI/Kismet/SDR en ejercicio SAR.
- `PROHIBIT` (perímetro excluido): emulación celular (Lifeseeker), AP mimético (Wi2SAR), TX SDR en campo, detección/identificación automática de personas, ausencia por silencio.

## 2. Alternativas consideradas

| Alternativa | Resultado | Razón |
|---|---|---|
| No reintegrar (dejar todo en legacy `superseded`) | Descartada | Deja dominios con valor BREC real (406 MHz, probes pasivas, geometría con drones) sin representación contractual y congela claims no verificados como única fuente. |
| Reintegrar en el core | Descartada | Viola ADR-0001: el core no conoce protocolos de radio, fabricantes ni modalidades; además inyectaría dominios `specified`/`unverified` en la autoridad normativa central. |
| **Reintegrar como addons experimentales** | **Adoptada** | Mismo patrón de la Fase 3: archivos nuevos, catálogo con `accepted_at: null`, fixtures, invariantes como consts, reviews por dominio. |

Decisión posterior por dominio (R-09, 2026-07-19): para el AP de emergencia con auto-join se evaluó **no incluir** (descartada: el caso de vida — víctima que no puede elegir red — queda sin canal), **incluir por defecto** (descartada: técnica evil-twin-like y legalmente interceptación-adyacente; inaceptable sin gobernanza) e **incluir como excepción gobernada** bajo `emergency_assumed_risk` (adoptada, ADR-005).

## 3. Dominios reintegrados y estados de evidencia asignados

Escalas: valor BREC `V1`–`V5`, madurez `externa/OpenBREC` (M0 idea → M5 operacional repetida), decisión según la regla de la matriz vigente.

| ID | Dominio | Addon | Valor | Estado de evidencia asignado | Madurez ext/OB | Decisión |
|---|---|---|---|---|---|---|
| R-01 | CSI presencia/movimiento y respiración en condiciones ideales | `csi-link-observation` | V4 | `bench-validated` comunitario acotado (`max_declared_evidence` como const) | M3/M1 | GO (contrato) / WATCH-P1 (físico) |
| R-02 | CSI through-wall/escombros y multi-persona | `csi-link-observation` (limitaciones declaradas) | V4 si funcionara | `simulated` con evidencia negativa (39–56 % separación en commodity) | M2/M1 | WATCH-P1 |
| R-03 | Metadata pasiva (probes, BT, rtl_433, DroneID) | `passive-rf-observation` | V4 | `bench-validated` comunitario; Kismet en SAR `unverified` | M3/M1 | GO (contrato) / WATCH-P1 (físico) |
| R-04 | Recepción SDR 406 MHz y DF coherente | `sdr-receive-profile` | V5 (distress real) | `bench-validated` comunitario; SAR operacional `unverified` | M3/M1 | GO (contrato) / WATCH-P1 (físico) |
| R-05 | Drones como geometría de sensing | `drone-deployment-event` | V4 | `specified`/`simulated` (payloads RF); térmica USAR `field-validated` externa y ajena | M2–M4/M1 | GO (contrato) / WATCH-P1 (físico) |
| R-06 | RF quieting / aislamiento medido | `rf-isolation-profile` | V3 | `specified` — sin literatura SAR (resultado negativo declarado) | M1/M1 | WATCH-P1 (requiere experimento propio) |
| R-07 | RuView como proveedor CSI opcional | `ruview-observation` | V3 | `specified` (adapter pineado `90667d0…`); claims nunca elevados | M2/M1 | GO (contrato, ADR-001) |
| R-08 | Detección pasiva de redes crowdsourced (Find My / Find Hub / SmartThings Find) | `offline-finding-observation` | V3 | `specified` — sin literatura SAR (RFC-0002, 2026-07-19; extensión posterior a esta matriz) | M3/M1 | GO (contrato) / WATCH-P1 (físico) |
| R-09 | AP de emergencia con auto-join (Karma gobernado + portal de emergencia) | `emergency-autojoin-profile` | V4 si funcionara | `specified` (contrato/gobernanza); eficacia `unverified` y cayendo por OS modernos (ADR-005, RFC-0003) | M2/M1 | GO (contrato, sólo excepción gobernada) / WATCH-P1 (experimento de eficacia) |

## 4. Boundaries fijados

| ID | Boundary | Mecanismo |
|---|---|---|
| RB-01 | Silencio nunca es ausencia; sin detección automática de personas | Consts `silence_means_absence: false`, `automatic_person_detection_allowed: false` (R-01/R-02); red line transversal |
| RB-02 | Sin identificación de personas ni retención de MAC cruda | Const `pseudonym_scheme: incident_rotating_hmac`, `payload_retained: false` (R-03) |
| RB-03 | Sin emulación activa ni intercepción de contenido | Consts `active_emulation: false`, `content_interception: false` (R-03); Lifeseeker/Wi2SAR excluidos con boundary flag |
| RB-04 | SDR receive-only en campo; sin demodulación de terceros | Consts `mode: receive_only_in_field`, `demodulate_third_party_traffic: false` (R-04) |
| RB-05 | El autopiloto conserva el vuelo; release con confirmación humana | Const `flight_authority_in_core: false` (R-05); ADR-002 |
| RB-06 | Aislamiento medido, nunca presumido; nunca envolver sector con posible víctima | Consts `baseline_before_after_required: true`, `never_enclose_possible_victim_sector_without_analysis: true` (R-06); ADR-003 |
| RB-07 | Salidas de RuView son observaciones experimentales, nunca `victim_detected` | Consts `experimental_only: true`, `outputs_are_victim_detected: false`, `unknown_class_required: true` (R-07); ADR-001 |
| RB-08 | Offline finding: solo recepción, sin identificación, peso bajo, exclusión del propio despliegue | Consts `passive_only: true`, `gatt_connection_attempted: false`, `identification_attempted: false`, `raw_identifier_retained: false`, `alert_trigger_allowed: false`, `own_fleet_exclusion_applied: true` (R-08); RFC-0002 |
| RB-09 | Autojoin de emergencia: sólo bajo `emergency_assumed_risk` completo; sin captura, sin rerouting, sin inspección de contenido; ACK de portal ≠ persona localizada; sin perfil por defecto | Invariantes de contrato de `emergency-autojoin-profile` (R-09); ADR-005; review `emergency-autojoin-review.md` |

## 5. Secuencia y siguiente experimento

1. Contratos + fixtures + tests de invariantes (Fase 6A, ejecutada).
2. Guías de dominio + investigación citable (Fase 6B, ejecutada).
3. Gobernanza: ADR-004, reviews de seguridad, RFC 0001, esta matriz (Fase 6C, ejecutada).
4. Siguiente experimento por dominio (todos fuera de esta autorización):
   - R-01/R-02: replay propio y ensayo de banco del build exacto; caja de escombros instrumentada con ground truth.
   - R-03: ensayo propio con MAC randomization activa.
   - R-04: ensayo con baliza de test en banco/campo controlado; error angular DF medido.
   - R-05: drop pod + eventos en ejercicio controlado.
   - R-06: experimento de validación propio: conjunto armado medido por banda, baseline antes/después.

## 6. Riesgos de la decisión

- La reintegración puede leerse como respaldo de capacidades que siguen `specified`/`unverified`; las guías y la FAQ lo declaran explícitamente.
- El dual-use de CSI (re-identificación por BFI) existe independientemente del contrato; la mitigación es de alcance y gobernanza, no técnica total.
- Los collectors siguen sin implementarse: el valor inmediato es de marco de referencia, no operativo.

## 7. Referencias

- Investigación base: [`docs/research/rf-sensing-state-of-the-art.md`](../research/rf-sensing-state-of-the-art.md).
- Decisión: [`ADR-004`](../adr/ADR-004-rf-sensing-reintegration.md); vigentes: ADR-001 (RuView), ADR-002 (drones), ADR-003 (aislamiento medido).
- Proceso: [`docs/open-spec/rfc/0001-rf-sensing-addons.md`](../open-spec/rfc/0001-rf-sensing-addons.md).
- Reviews: `rf-sensing-csi-review.md`, `passive-rf-review.md`, `sdr-receive-review.md`, `drone-geometry-review.md`, `rf-quieting-review.md` en [`docs/security/`](../security/).
- Guías: `csi-sensing`, `passive-rf`, `sdr-beacons`, `drone-geometry`, `rf-quieting` en [`docs/guides/`](../guides/README.md).

## 8. Historial de gobernanza

| Fecha | Estado anterior | Estado nuevo | Evidencia/razón |
|---|---|---|---|
| 2026-07-19 | Dominios RF sensing archivados en `docs/legacy/` sin representación vigente | Reintegrados como 6 addons experimentales con invariantes de safety | ADR-004; investigación SOTA con tabla de evidencia; 5 reviews de diseño; RFC 0001 accepted. |
| 2026-07-19 | Sin canal hacia víctimas que no pueden interactuar con su teléfono | AP de emergencia con auto-join incluido sólo como excepción gobernada bajo `emergency_assumed_risk` (R-09/RB-09) | ADR-005; review de diseño; TM-020..TM-022; eficacia declarada `unverified` con experimento definido. |
| 2026-07-20 | R-08 y R-09 asignados `specified` | R-08 (`offline-finding-observation`, gate `rf-sensing-offline-finding`) y R-09 (`emergency-autojoin-profile`, gate `rf-sensing-autojoin`) elevados a `simulated` por simuladores de replay determinísticos; la eficacia física de R-09 sigue `unverified` | Nota de actualización (append-only): los estados de la tabla §3 se leen con esta corrección; no se reescribe la asignación histórica. |
