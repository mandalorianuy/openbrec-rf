# RFC 0003: addon emergency-autojoin-profile (AP de emergencia estilo Karma como excepción gobernada)

- Estado: `accepted` (2026-07-19)
- Decisor: project owner, según [RFC-PROCESS](../RFC-PROCESS.md) (proceso unipersonal vigente; sus obligaciones de registro append-only y preservación de disenso aplican a este archivo)
- Decisión asociada: extiende el carril regulatorio `emergency_assumed_risk` ya normativo en [`multi-bearer-transport-profiles.json`](../../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json); relacionado con [ADR-004](../../adr/ADR-004-rf-sensing-reintegration.md) (boundaries de RF) y registrado como decisión de arquitectura en [ADR-005](../../adr/ADR-005-emergency-autojoin-governed-exception.md) (excepción gobernada)
- Comentarios en contra recibidos: ninguno (proceso unipersonal; esta sección se conserva para registrar disenso futuro)

## 1. Problema

Una víctima inconsciente no puede elegir una red Wi-Fi ni pulsar nada. Si su teléfono sondea redes recordadas, un AP de emergencia que responde a cualquier SSID sondeado (comportamiento estilo Karma/pineapple) puede lograr que el dispositivo se auto-conecte y servirle un portal que suena, vibra o flashea: el teléfono se convierte en baliza y la asociación misma es un indicio de presencia del dispositivo.

El problema normativo es que ese comportamiento es, por diseño, indistinguible de un ataque evil twin: contradice las red lines del proyecto (`active_emulation: false` en el dominio de RF pasiva) si se admite como capacidad. La decisión del project owner es incluirlo **sólo como excepción gobernada** bajo el modo regulatorio `emergency_assumed_risk` ya existente, nunca como perfil por defecto. La eficacia real en 2026 es baja y cayendo (mitigaciones de auto-join en iOS/Android, rotación de MAC, redes recordadas con WPA2/WPA3 que exigen credencial): el estado honesto es `unverified`/`specified`.

## 2. Propuesta

Agregar el addon experimental `emergency-autojoin-profile` (policy) a `schemas/addons/1.0.0/`, con `status: experimental` y `accepted_at: null`:

| Grupo | Consts / campos |
|---|---|
| Carril regulatorio | `regulatory_mode: emergency_assumed_risk` (const) |
| Gobernanza (const true) | `dual_authorization_required` (con `authorizing_actors` ≥ 2), `expiry_required` (con `expires_at` canónico obligatorio), `kill_switch_required`, `stop_condition_required`, `monitoring_required`, `never_equals_legal_authorization` |
| Técnica | `karma_ssid_response: true` (responde a cualquier SSID sondeado), `ssid_labeling: emergency_labeled_portal`, `geofence_ref` y `channel_plan` obligatorios |
| Límites de contenido (const false) | `content_interception`, `traffic_rerouting_allowed`, `credential_capture`, `payload_retained`, `person_identification_allowed` |
| Portal como baliza | `portal_capabilities` enum (`emergency_message`, `sound_alert`, `vibration_alert`, `flash_alert`); `portal_ack_means_person_located: false` |
| Observaciones | asociaciones fluyen al pipeline con `subject_ref` HMAC rotativo (`incident_rotating_hmac`); `own_fleet_exclusion_applied: true` |
| Evidencia | `silence_means_absence: false`, `device_type_inference: heuristic_only`, `default_profile_allowed: false`, `max_declared_evidence: unverified` |

Acompañan: fixtures válidos/inválidos, diez rechazos nuevos en `tests/test_p0_01_contracts.py` y la documentación de dominio (guía, ADR y security review) que se produce en paralelo.

## 3. Compatibilidad

Compatible hacia atrás. Ningún contrato core ni addon existente cambia de bytes; catálogo y `compatibility-baseline.json` se actualizan de forma aditiva (30 → 31 addons). La versión de spec se mantiene `1.0.0-draft.1`. **No altera red lines:** no abre un carril nuevo; usa el modo `emergency_assumed_risk` que la spec ya declara, y deja como consts las condiciones que lo gobiernan. `never_equals_legal_authorization: true` registra que el riesgo asumido no equivale a autorización legal: la revisión por jurisdicción sigue siendo obligatoria.

## 4. Alternativas consideradas

1. **No incluirlo**: descartada por el caso de vida — es uno de los pocos mecanismos que puede convertir en baliza el teléfono de una víctima incapaz de interactuar; el costo es un contrato con consts estrictas.
2. **Incluirlo como capacidad normal** (perfil por defecto): descartada — sería un evil twin operativo; `default_profile_allowed: false` lo prohíbe por contrato.
3. **AP etiquetado sin respuesta Karma** (SSID único claramente de emergencia, esperando que el usuario se conecte): **no descartada — queda como complemento posible**; no requiere RFC nuevo porque no responde a SSIDs arbitrarios ni induce auto-join, y puede declararse dentro del mismo perfil con `karma_ssid_response` documentado. La excepción Karma se mantiene para la víctima que no puede elegir red.
4. **Excepción gobernada con consts verificables** (adoptada): hace cumplibles por contrato la doble autorización, la expiración, el kill switch, la condición de parada, el monitoreo y los límites de contenido.

## 5. Impacto en evidencia y estados

- **Estado asignado: `unverified` como tope** (`max_declared_evidence: unverified`). No hay literatura SAR de este uso y la eficacia declina con las mitigaciones de los OS (auto-join restringido, MAC randomization, exigencia de credencial en redes recordadas). Nada en este RFC declara eficacia.
- **Experimento definido para subir de nivel:** ensayo controlado con dispositivos propios consentidos (versiones de OS declaradas), midiendo tasa de auto-join por OS/versión, tiempo hasta asociación, falsos positivos del propio despliegue y comportamiento del portal — bajo `conducted_only` o Faraday medido (`rf-isolation-profile`), nunca en espacio público sin autorización.
- **Fixtures y gates:** matriz estándar más rechazos de `regulatory_mode` distinto, `dual_authorization_required: false`, `expires_at` ausente, `content_interception`/`traffic_rerouting_allowed`/`credential_capture`/`person_identification_allowed`/`portal_ack_means_person_located`/`default_profile_allowed`/`silence_means_absence` en valores prohibidos. Gates `addon-contracts`, `addon-fixtures`, `schema-compat` y `contracts-gen --check` en verde.
- **Este RFC no habilita** runtime, hardware, transmisión activa fuera de banco autorizado ni uso en campo sin la gobernanza declarada; una asociación al portal nunca es una persona localizada (`portal_ack_means_person_located: false`) y el silencio nunca es ausencia.
