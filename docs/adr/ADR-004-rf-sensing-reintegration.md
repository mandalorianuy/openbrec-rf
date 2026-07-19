# ADR-004: reintegración de los dominios de RF sensing como addons experimentales

- Estado: Accepted
- Fecha: 2026-07-19
- Decisor: project owner
- Alcance: dominios CSI/radio-tomografía, observación RF pasiva, recepción SDR, drones como geometría de sensing, RF quieting y RuView como proveedor opcional

## Contexto

La encarnación previa de OpenBREC RF era una plataforma de fusión radioeléctrica basada en Wi-Fi CSI, Kismet, SDR, despliegue con drones y recintos de atenuación RF. Esa línea quedó archivada en `docs/legacy/` con estado `superseded` y sin autoridad normativa cuando el proyecto se reorientó a una Open Spec offline-first de comunicaciones, energía y evidencia para BREC/USAR (Fase 0 del roadmap vigente).

El archivo resolvió la autoridad, pero dejó un costo: dominios con valor BREC real (detección pasiva de teléfonos, recepción de balizas 406 MHz, geometría de sensing con drones, aislamiento RF medido) quedaron sin representación contractual en la spec vigente, y el material legacy que los describía mezclaba claims no verificados con diseño rescatable.

Entre 2026-07-14 y 2026-07-19 se ejecutó una investigación de estado del arte con fuentes citables, publicada en [`docs/research/rf-sensing-state-of-the-art.md`](../research/rf-sensing-state-of-the-art.md). Su tabla de niveles de evidencia (§14) es la fuente de verdad editorial: qué está `bench-validated` comunitariamente, qué es sólo `simulated`, qué es `specified` por ausencia total de evidencia y qué es `unverified` por falta de casos SAR documentados. La investigación también produjo un resultado negativo relevante: no existe literatura publicada de RF quieting aplicado a escenas SAR.

## Decisión

### Reintegración como addons experimentales

Los dominios de RF sensing se reintegran a la Open Spec como seis addons experimentales en `schemas/addons/1.0.0/`, con fixtures válidos/inválidos, entrada en el catálogo de addons (`status: experimental`, `accepted_at: null`) e invariantes de safety fijadas como consts de contrato:

| Addon | Dominio | Consts de safety principales |
|---|---|---|
| `csi-link-observation` | CSI/radio-tomografía | `silence_means_absence: false`, `automatic_person_detection_allowed: false`, `max_declared_evidence: bench-validated` |
| `passive-rf-observation` | Metadata pasiva (probes, BT, rtl_433, DroneID) | `pseudonym_scheme: incident_rotating_hmac`, `payload_retained: false`, `content_interception: false`, `active_emulation: false` |
| `sdr-receive-profile` | Recepción SDR | `mode: receive_only_in_field`, `demodulate_third_party_traffic: false` |
| `ruview-observation` | RuView como proveedor CSI opcional | `experimental_only: true`, `outputs_are_victim_detected: false`, `unknown_class_required: true` |
| `drone-deployment-event` | Drones como geometría de sensing | `flight_authority_in_core: false`, release con confirmación humana, estados de caída excluidos de fusión |
| `rf-isolation-profile` | RF quieting / aislamiento medido | `baseline_before_after_required: true`, `never_enclose_possible_victim_sector_without_analysis: true` |

Ningún addon eleva un claim por encima de la tabla de evidencia de la investigación. La reintegración es de marco de referencia (contratos, fixtures, guías, reviews): no autoriza implementación de collectors, compra de hardware ni TX.

### Los seis schemas legacy quedan congelados

Los archivos de la encarnación previa registrados en `schemas/legacy/catalog.json` **no se mueven, corrigen ni regeneran**. ADR-0001 fijó ese baseline con gate de integridad por SHA-256 y la regla de que toda adopción legacy produce un archivo nuevo más una decisión registrada. Este ADR es esa decisión: los seis addons nuevos son archivos nuevos que adoptan, corrigen o descartan partes del material legacy; los schemas legacy permanecen como evidencia histórica byte-idéntica.

### Boundaries

- **Lifeseeker y Wi2SAR quedan excluidos como capacidades.** Emulación de celda celular y AP mimético implican transmisión activa engañosa y contradicen las red lines de ADR-0001 y `AGENTS.md` (nada ofensivo, `active_emulation: false`). Se citan únicamente como referencias externas con boundary flag para delimitar el perímetro.
- **SDR es receive-only en campo.** `mode: receive_only_in_field` es const; cualquier TX de prueba pertenece a banco autorizado bajo `conducted_only`, coherente con la red line de no TX activo en la fase inicial.
- **El autopiloto conserva el vuelo.** ADR-002 sigue vigente: OpenBREC registra eventos de despliegue y telemetría normalizada, nunca autoridad de vuelo (`flight_authority_in_core: false`).
- **El aislamiento RF es medido, no presumido.** ADR-003 sigue vigente: ningún claim de atenuación del conjunto sin medición por banda con incertidumbre y baseline antes/después.
- **ADR-001 sigue vigente** para RuView: integración por adapter, version-pinned, opcional y reemplazable; sus salidas son observaciones experimentales, nunca `victim_detected`.

Los ADR-001, ADR-002 y ADR-003, escritos antes del archivo legacy, quedan así referenciando addons reales y vigentes.

### Base editorial

Los estados de evidencia públicos de estos dominios (`specified`, `simulated`, `bench-validated` comunitario acotado, `unverified` en SAR operacional) se asignan según la tabla §14 de la investigación. Ningún documento, guía, fixture ni review puede elevarlos sin evidencia nueva citada en esa tabla. Las guías de dominio (`csi-sensing`, `passive-rf`, `sdr-beacons`, `drone-geometry`, `rf-quieting`) y las reviews de seguridad de `docs/security/` derivan de esta decisión.

## Consecuencias

- La spec pasa de 23 a 29 addons experimentales; los tests de contratos fijan los nuevos conteos y las invariantes de safety se verifican con fixtures inválidos.
- El material legacy relevante queda citado como `[superseded, fuente]` desde las guías nuevas; el resto permanece como contexto histórico sin autoridad.
- Toda futura implementación de collector (CSI, Kismet, SDR, drone bridge) nace `unverified` y exige evidence pack propio para subir de estado; la reintegración contractual no acredita nada físico.
- El proceso RFC de la Open Spec registra esta reintegración como su primer caso de uso (`docs/open-spec/rfc/0001-rf-sensing-addons.md`).
- El threat model incorpora las nuevas superficies (dual-use de CSI, privacidad de probes, riesgo UAS, supresión RF) con reviews de diseño por dominio; sigue sin existir aplicación de campo desplegada que evaluar en runtime.

## Criterios de revisión

Revisar este ADR si: aparece silicio comercial 802.11bf (habilita interop real), se publica evidencia de RF quieting en SAR, un despliegue CSI/RTI/Kismet/SDR en ejercicio u operación real queda documentado, o una red line de ADR-0001 cambia por RFC propio. Nuevas versiones de RuView, Kismet o toolchains CSI no justifican por sí solas modificarlo: actualizan el pin o la tabla de evidencia mediante el proceso RFC ordinario.
