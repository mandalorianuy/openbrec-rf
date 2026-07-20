# RFC 0002: addon de detección pasiva de redes de localización crowdsourced (offline finding)

- Estado: `accepted` (2026-07-19)
- Decisor: project owner, según [RFC-PROCESS](../RFC-PROCESS.md) (proceso unipersonal vigente; sus obligaciones de registro append-only y preservación de disenso aplican a este archivo)
- Decisión asociada: [ADR-004](../../adr/ADR-004-rf-sensing-reintegration.md) y [RFC-0001](0001-rf-sensing-addons.md) (extiende el dominio de RF pasiva)
- Comentarios en contra recibidos: ninguno (proceso unipersonal; esta sección se conserva para registrar disenso futuro)

## 1. Problema

Las redes de localización crowdsourced (Apple Find My, Google Find Hub, Samsung SmartThings Find) emiten anuncios BLE observables pasivamente: company ID `0x004C` / payload type `0x12` (Apple), Service Data UUID `0xFEAA` / frame types `0x40`-`0x41` (Google FMDN v1.3), y patrones observables de spec cerrada (Samsung, USENIX Security 2023). En un escenario SAR, esos anuncios son un **indicio débil** de presencia de un dispositivo — incluido el caso documentado de iPhones 11+ que siguen emitiendo horas después de apagados por reserva de batería.

Sin un contrato propio, esa observación caía en una de dos trampas: (a) absorberla informalmente en `passive-rf-observation`, diluyendo sus invariantes específicos (prohibición de GATT, hipótesis de clasificación, exclusión del propio despliegue); o (b) no observarla en absoluto, perdiendo un indicio gratuito de vida potencial. La investigación y las fuentes primarias (OpenHaystack/PoPETs 2021, FMDN spec, RE de AirTag, DULT) se citan en la guía `docs/guides/offline-finding.md`.

## 2. Propuesta

Agregar el addon experimental `offline-finding-observation` a `schemas/addons/1.0.0/`, registrado en el catálogo con `status: experimental` y `accepted_at: null`:

| Aspecto | Decisión |
|---|---|
| Tipo | payload (standalone, patrón de `csi-link-observation`; el `allOf` a core observation no admite campos nuevos por `additionalProperties: false`) |
| Red | `network` enum `apple_find_my / google_find_hub / samsung_smartthings_find / unknown` |
| Patrón | `frame_pattern` (`0x004C/0x12`, `0xFEAA/0x40`, `undocumented`) — cabecera, nunca identificador |
| Seudonimización | `subject_ref` con patrón `hmac-sha256:<hex>` y `pseudonym_scheme: incident_rotating_hmac` |
| Hipótesis | `classification_hypothesis` opcional con `statement_kind: hypothesis` y `confidence` 0–1 |
| Consts de safety | `passive_only: true`, `gatt_connection_attempted: false`, `identification_attempted: false`, `raw_identifier_retained: false`, `silence_means_absence: false`, `alert_trigger_allowed: false`, `fusion_weight: low`, `own_fleet_exclusion_applied: true`, `max_declared_evidence: bench-validated` |

Acompañan: fixtures válidos/inválidos, rechazos en `tests/test_p0_01_contracts.py`, la guía `docs/guides/offline-finding.md` y las entradas de consistencia (research, FAQ, matriz de decisión, índice de guías).

## 3. Compatibilidad

Compatible hacia atrás. Ningún contrato core ni addon existente cambia de bytes; el catálogo y `compatibility-baseline.json` se actualizan de forma aditiva (29 → 30 addons). La versión de spec se mantiene `1.0.0-draft.1`. Los tests de contratos fijan los nuevos conteos (30 schemas, 60 válidos, 210 inválidos) como parte del cambio.

## 4. Alternativas consideradas

1. **Reusar `passive-rf-observation`** con una nueva entrada en su enum `source`: descartada — las invariantes específicas (cero GATT, hipótesis etiquetada, exclusión del propio despliegue, `alert_trigger_allowed: false`) no tienen lugar en ese contrato y forzarlas lo rompería en bytes.
2. **No observar estas redes**: descartada — el indicio es pasivo, gratuito y potencialmente life-safety; el costo es sólo un contrato.
3. **Addon propio con consts explícitas** (adoptada): mismo patrón validado de Fase 3 / RFC-0001, con los límites de fusión y privacidad como consts verificables.

## 5. Impacto en evidencia y estados

- **Ningún claim se eleva.** El dominio entra como `specified`: no existe literatura SAR publicada de detección pasiva de estas redes. El const `max_declared_evidence: bench-validated` fija el tope declarable futuro; superarlo requiere evidence pack propio (PUBLISHING) midiendo rango bajo escombros, prevalencia regional, tasa de falsos positivos y duración post-apagado.
- **Fixtures y gates:** casos válidos (Apple, Google con hipótesis) e inválidos estándar; los rechazos nuevos cubren `gatt_connection_attempted`, `identification_attempted`, `raw_identifier_retained`, `alert_trigger_allowed` y `silence_means_absence` en `true`. Gates `addon-contracts`, `addon-fixtures`, `schema-compat` y `contracts-gen --check` en verde.
- **El silencio pesa más aquí que en cualquier otro dominio:** teléfono apagado sin reserva, Bluetooth deshabilitado, Find My/Find Hub deshabilitado, AirTag en estado *Connected*, agregación de Google o escombros silencian el indicio — el contrato lo fija con `silence_means_absence: false`.
- **Este RFC no habilita** runtime, hardware, conexión GATT, identificación de personas ni alertas automáticas.
