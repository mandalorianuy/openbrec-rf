# RFC 0001: addons de RF sensing (CSI, RF pasiva, SDR, drones, RF quieting, RuView)

- Estado: `accepted` (2026-07-19)
- Decisor: project owner, según [RFC-PROCESS](../RFC-PROCESS.md) (proceso unipersonal vigente; sus obligaciones de registro append-only y preservación de disenso aplican a este archivo)
- Decisión asociada: [ADR-004](../../adr/ADR-004-rf-sensing-reintegration.md)
- Comentarios en contra recibidos: ninguno (proceso unipersonal; esta sección se conserva para registrar disenso futuro)

## 1. Problema

La encarnación previa del proyecto (Wi-Fi CSI, Kismet, SDR, drones, RF quieting) quedó archivada en `docs/legacy/` con estado `superseded` al reorientarse OpenBREC a una Open Spec offline-first de comunicaciones, energía y evidencia. El archivo resolvió la autoridad normativa, pero dejó tres problemas concretos:

1. **Dominios con valor BREC sin representación contractual.** La recepción de balizas 406 MHz, la detección pasiva de teléfonos, la geometría de sensing con drones y el aislamiento RF medido no existían en la spec vigente: ni como capacidad ni como boundary.
2. **Claims no verificados como única fuente.** El material legacy mezclaba diseño rescatable con afirmaciones sin validación; sin migración, cualquier reuso informal heredaba esa mezcla.
3. **Boundaries sin fijar.** Referencias externas como Lifeseeker (emulación celular) y Wi2SAR (AP mimético) circulaban en el ecosistema SAR sin una declaración normativa de que quedan fuera del perímetro del proyecto.

La investigación `docs/research/rf-sensing-state-of-the-art.md` (corte 2026-07-19) aporta la evidencia: tabla §14 de niveles por tecnología, incluidos resultados negativos (cero casos CSI/RTI/Kismet/SDR en SAR real; sin literatura de RF quieting en escena SAR; separación multi-persona de 39–56 % en hardware commodity).

## 2. Propuesta

Agregar seis addons experimentales a `schemas/addons/1.0.0/`, registrados en el catálogo con `status: experimental` y `accepted_at: null`, con fixtures válidos/inválidos e invariantes de safety como consts:

| Addon | Tipo | Consts de safety |
|---|---|---|
| `csi-link-observation` | payload | `silence_means_absence: false`, `automatic_person_detection_allowed: false`, `max_declared_evidence: bench-validated` |
| `passive-rf-observation` | payload | `pseudonym_scheme: incident_rotating_hmac`, `payload_retained: false`, `content_interception: false`, `active_emulation: false` |
| `sdr-receive-profile` | policy | `mode: receive_only_in_field`, `demodulate_third_party_traffic: false` |
| `ruview-observation` | payload | `experimental_only: true`, `outputs_are_victim_detected: false`, `unknown_class_required: true` |
| `drone-deployment-event` | payload | `flight_authority_in_core: false`, `drop_sample_states_excluded_from_fusion: [RELEASED, IMPACT, SETTLING]` |
| `rf-isolation-profile` | payload | `baseline_before_after_required: true`, `never_enclose_possible_victim_sector_without_analysis: true` |

Acompañan: guías de dominio (`csi-sensing`, `passive-rf`, `sdr-beacons`, `drone-geometry`, `rf-quieting`), la investigación citable, cinco reviews de seguridad de diseño en `docs/security/`, ADR-004 y la matriz de decisión de 2026-07-19. Los seis schemas legacy en `schemas/legacy/` permanecen congelados por el gate SHA-256 de ADR-0001: la adopción se hace por archivos nuevos, nunca por corrección in place.

## 3. Compatibilidad

Compatible hacia atrás. Ningún contrato core ni addon existente cambia de bytes; el catálogo de addons agrega entradas sin modificar las vigentes; `compatibility-baseline.json` se actualiza de forma aditiva. La versión de spec se mantiene `1.0.0-draft.1`. Los tests de contratos fijan los nuevos conteos (23 → 29 addons) como parte del cambio, no como regresión.

## 4. Alternativas consideradas

1. **No reintegrar** (conservar todo como legacy `superseded`): descartada — deja dominios valiosos sin contrato y sin boundaries, y los claims no verificados como única referencia.
2. **Reintegrar en el core**: descartada — viola la frontera de ADR-0001 (el core no conoce protocolos de radio, fabricantes ni modalidades concretas) e inyecta dominios `specified`/`unverified` en la autoridad central.
3. **Reintegrar como addons experimentales** (adoptada): replica el patrón validado de la Fase 3 y mantiene cada dominio con su estado de evidencia honesto.

El detalle comparativo vive en `docs/decision-matrices/2026-07-19-rf-sensing-reintegration-decision-matrix.md`.

## 5. Impacto en evidencia y estados

- **Ningún claim se eleva.** Los estados se asignan según la tabla §14 de la investigación: CSI presencia/movimiento y respiración ideal, probes/BT pasivos, decodificación 406 MHz y DF coherente quedan `bench-validated` comunitarios acotados; CSI through-wall y multi-persona quedan `simulated` con evidencia negativa declarada; CSI/RTI/Kismet/SDR en SAR real quedan `unverified`; RF quieting queda `specified` con resultado negativo de literatura declarado; interop 802.11bf queda `specified` (estándar ratificado 2025-09-26, sin silicio comercial).
- **Fixtures y gates:** cada addon agrega casos válidos e inválidos que verifican sus consts de safety (rechazo de `silence_means_absence: true`, MAC cruda, `release_mode` automático, `measurements` vacíos, demodulación de terceros, TX en campo); los gates `addon-contracts`, `addon-fixtures` y `schema-compat` pasan.
- **Lifeseeker y Wi2SAR** se citan sólo como referencias externas con boundary flag; ningún schema ni fixture los modela como capacidad.
- **Promoción futura:** todo collector implementado nacerá `unverified` y requerirá evidence pack propio (PUBLISHING); este RFC no habilita runtime, hardware, TX ni campo.
