# Review de seguridad — observación RF pasiva (`passive-rf-observation`)

- Fecha: 2026-07-19
- Alcance: addon experimental `passive-rf-observation` (probe requests Wi-Fi, advertisements BLE, rtl_433/ADS-B, DJI DroneID; diseño contractual, sin runtime)
- Autoridad: ADR-004, red lines de ADR-0001 y `AGENTS.md`, marco legal de `docs/guides/regulatory.md`
- Base de evidencia: `docs/research/rf-sensing-state-of-the-art.md` §7–§8 y §12
- Veredicto: aceptado como diseño `specified`; ningún collector pasivo queda implementado por esta review

## Alcance

Revisión de diseño del contrato que modela metadata pasiva recibida en el incidente. Las fuentes activas engañosas (Lifeseeker, Wi2SAR) son referencias externas con boundary flag, nunca capacidades: este review las trata como perímetro excluido.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| PRF-T1 | Privacidad de probes: las probe requests y advertisements de víctimas, rescatistas y terceros revelan presencia, identificadores de red y patrones de movimiento de personas que no consintieron. | Collector operativo con retención; correlación temporal; fuga del almacén local. | Tracking de personas, daño a víctimas y terceros, riesgo legal (precedente reportado: multa ~600 000 € a Enschede por tracking Wi-Fi; GDPR 6.1.d como base potencial sólo en rescate). |
| PRF-T2 | Spoofing de probes: un actor inyecta probes con identificadores fabricados para simular un teléfono de víctima y desviar la búsqueda. | Proximidad RF; confianza en RSSI/presencia sin corroboración. | Desvío de recursos hacia un sector vacío. |
| PRF-T3 | Misión creep hacia IMSI-catcher/evil-twin: presión operativa para "hacer que el teléfono responda" deriva en emulación activa (Lifeseeker/Wi2SAR). | Hardware capaz de TX; ausencia de boundary contractual. | Violación de red lines, ilicitud (intercepción/suplantación), daño al proyecto. |
| PRF-T4 | Re-identificación por MAC estable o por SSIDs históricos en probes. | Persistencia de MAC cruda o de listas de SSID; cruce con bases externas. | Identificación de personas fuera de propósito life-safety. |
| PRF-T5 | Falsa ausencia: MAC randomization hace desaparecer los identificadores y el silencio se lee como sector vacío. | UI/fusión que infiera ausencia; desconocimiento de la limitación. | Abandono de sector con víctima (life-safety). |

## Controles

- **Contrato `passive-rf-observation`**: `pseudonym_scheme: incident_rotating_hmac` como const — `subject_ref` es HMAC rotativo por incidente, nunca MAC cruda; `payload_retained: false`, `content_interception: false` y `active_emulation: false` como consts. Un payload con MAC cruda o contenido no valida.
- **MAC randomization como limitación declarada**: la guía `passive-rf.md` documenta que la vinculación temporal es frágil; el silencio nunca es ausencia (red line transversal, const `silence_means_absence: false` en el dominio CSI y regla del pipeline de evidencia). También es una protección: el ecosistema ya rota identificadores, y el HMAC por incidente alinea el diseño con esa dirección.
- **Boundary anti-IMSI/evil-twin**: `active_emulation: false` es const; Lifeseeker y Wi2SAR se citan sólo con boundary flag en la investigación y la guía; ADR-0001 prohíbe suplantación y funciones ofensivas.
- **Marco legal**: todo colector vive del lado pasivo de la línea metadata-vs-contenido (§2511(2)(g) para distress en EE.UU., GDPR 6.1.d, UY Const. art. 28 / Ley 19.574 para contenido; ver `regulatory.md`, informativo, no asesoría legal).
- **Retención gobernada**: handling policy del core; stripping en el borde; observaciones con provenance e incertidumbre, nunca hechos.

## Riesgo residual

- La recepción pasiva de metadata es riesgo bajo pero no cero: la presencia misma de un equipo es información sensible; la minimización contractual no controla leaks de runtime aún inexistente.
- El spoofing de probes no es detectable por contrato; la mitigación real es corroboración cruzada y confianza baja de fuente única, ambas del pipeline, no del addon.
- Revisión legal local por jurisdicción sigue pendiente para cualquier despliegue real.

## Declaración de madurez

Review de **diseño** sobre contrato `specified`. La recepción pasiva de probes/BT es `bench-validated` comunitaria; Kismet como herramienta SAR es `unverified` (sin casos documentados). Nada de esta review habilita runtime, hardware ni campo.
