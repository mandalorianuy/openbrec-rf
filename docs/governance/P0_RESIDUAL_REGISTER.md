# Registro gobernado de residuales P0

- Estado: activo
- Plan: `docs/superpowers/plans/2026-07-17-openbrec-p0-simulated-addons-plan.md`
- Owner del registro: `release-reviewer`
- Regla: todo residual debe estar `resolved`, `controlled`, `planned` o `blocked`
- Estado inicial: cero residuales `blocked`; ninguno autoriza claims fuera de P0

## Registro

| ID | Residual | Estado | Owner | Resolución o plan | Gate/artefacto | Stop condition |
|---|---|---|---|---|---|---|
| P0-R001 | Los modelos de Meshtastic, MeshCore y Reticulum pueden divergir de firmware/wire behavior real. | controlled para P0 simulado; planned para P1a; hardware `unverified` | `radio-transport-maintainer` | P0-04 fija versión/commit, fuente, licencia, coeficientes y limitaciones; wire/firmware/hardware se valida sólo en P1a. | `transport-comparison`, workload y review P0-04 | Afirmación física, wire claim o promoción de soporte basada en el modelo bloquea P0-09/P1a. |
| P0-R002 | P0 no valida frecuencia, regulación, coexistencia ni TX en ninguna jurisdicción. | controlled por frontera P0; planificado para P1a/P1b | `privacy-safety-reviewer` | Cero TX y cero control de radio física en P0; perfil regulatorio/conducted/radiated se decide después. | secret/safety scan y review P0-09 | Cualquier TX, compra o claim RF detiene P0. |
| P0-R003 | Energía simulada no acredita loads reales, capacidad descargable ni autonomía de 72 horas. | controlled por frontera P0; planificado para P1a-06/P1a-07 | `energy-maintainer` | P0 sólo valida contratos/FSM; caracterización y storage-only 72h requieren plan P1a. | `energy-replay` y scan de claims | Claim físico, solar o “indefinido” bloquea aceptación. |
| P0-R004 | Fixtures beacon no representan rubble, ruido, clima, placement ni lotes físicos completos. | planned para P0-07 y campañas P1 | `beacon-science-maintainer` | Declarar environment class, provenance, OOD y límites; conservar unknown/abstention y diseñar protocolo físico posterior. | `beacon-replay`, model/dataset cards | Ocultar clase omitida o generalizar fuera del fixture bloquea P0-07/P0-09. |
| P0-R005 | Automatización P0 no demuestra comprensión bajo estrés ni accesibilidad humana real. | controlled en P0; planificado para P1a-03 | `product-ux-reviewer` | P0 valida semántica/UI técnica y versiona el protocolo con 8 operadores y 8 personas no preparadas. | `terminal-ux`, `accessibility`, guion P1a | Claim de usabilidad humana o field readiness bloquea P0-06/P0-09. |
| P0-R006 | La escala 50k/60/5/2 depende de recursos del runner y no representa todas las distribuciones operativas. | controlled para correctness P0; performance/representatividad planned para P0-09/P1a | `federation-maintainer` | P0-05 fija generador, seed, topología, carga, denominadores y límites; no emite benchmark ni claim operacional. P0-09 conserva el límite y P1a debe medir recursos/topologías autorizadas. | `federation-scale`, fixture y review P0-05 | Reducir denominador o afirmar capacidad, latencia o representatividad desde la simulación bloquea P0-09/P1a. |
| P0-R007 | Claves y secure storage simulados no acreditan custodia, HSM ni resistencia física de terminal robado; P0-03 resolvió sólo protocolo, revocación y rekey offline simulados. | controlled en P0; planificado para P1a/campo | `privacy-safety-reviewer` | Mantener material sintético; validar extracción, wipe, secure storage y custodia sólo con hardware autorizado. | `human-message-security`, secret scan y protocolo P1a | Clave real/default o claim HSM/campo basado en P0 bloquea el gate y P0-09. |
| P0-R008 | Fuentes, defaults y seguridad de bearers cambian con rapidez. | controlled por pins P0-04; review obligatorio P0-09/P1 | `radio-transport-maintainer` + `release-reviewer` | Workload fija versión/commit, fecha, fuente y licencia; P0-09 debe revalidar advisories/SBOM y cualquier plan P1 debe elegir pins nuevamente. | workload P0-04, SBOM y vulnerability receipt P0-09 | Fuente flotante, advisory sin gobernar, default credential o uso de pin obsoleto fuera del modelo bloquea aceptación. |
| P0-R009 | Pydantic y TypeScript no expresan todos los constraints Draft 2020-12; la intersección `BeaconObservation` puede conservar un índice TypeScript `unknown`. | controlled permanente desde P0-01 | `contract-maintainer` | JSON Schema con `FormatChecker` y registry local es autoridad; corre antes de consumidores generados. Los 36 fixtures válidos compilan en ambos consumidores y 126 negativos se evalúan contra JSON Schema. | `addon-contracts`, `addon-fixtures`, `contracts-gen --check` | Un consumidor generado nunca reemplaza validación normativa; drift o error de asignabilidad falla el gate. |
| P0-R010 | P0-01 define payloads y boundaries; energía, crypto/SOS, transportes y federación fueron resueltos por P0-02–P0-05, pero terminal y beacon runtime siguen pendientes. | P0-02–P0-05 slices resolved; planned para P0-06–P0-07 | owners de cada task consumidora | Cada task restante debe implementar sus invariantes con replay/fallos y no puede usar schemas ni gates anteriores como prueba de su runtime. | gates y receipts P0-06–P0-07 | Claim funcional, operativo o físico basado sólo en contratos/modelos previos bloquea aceptación de la task consumidora y P0-09. |
| P0-R011 | El checkpoint y restart determinísticos de P0-02 no prueban persistencia durable bajo corte eléctrico real, rollback del storage ni recuperación concurrente. | controlled para P0 simulado; planned para P0-08 y P1a-06/P1a-07 | `energy-maintainer` + `core-replay-maintainer` | Revalidar integración y fallos cruzados en P0-08; ensayar power-cut, storage y recuperación física sólo bajo plan P1a. | `p0-integrated`, protocolo power-cut P1a y receipt de recuperación | Pérdida de secuencia, accepted log o estado vital bloquea P0-08; cualquier claim durable/físico basado en P0-02 bloquea P0-09. |
| P0-R012 | Las claves P0-03 se derivan determinísticamente de labels públicos para vectores reproducibles y son inseguras fuera de replay. | controlled permanente para P0; reemplazo obligatorio antes de P1a runtime | `privacy-safety-reviewer` | Mantener namespace `simulated-only`, cero export a runtime y exigir generación/custodia real en un plan posterior. | secret scan, review P0-03 y preflight P1a | Reutilizar derivación, key IDs o ciphertext P0 como credencial operativa bloquea P0-09/P1a. |

## Regla append-only

Cada transición conserva fecha, estado anterior, estado nuevo y evidencia. Un
residual `planned` que alcanza su task sin solución pasa a `blocked`; no se
arrastra automáticamente. Resultados negativos permanecen unidos al mismo ID.

## Historial

| Fecha | Residual | Estado anterior | Estado nuevo | Evidencia/razón |
|---|---|---|---|---|
| 2026-07-17 | P0-R001–P0-R008 | inexistente | estados iniciales gobernados | Plan P0 aprobado después del exit M0; no se inició implementación. |
| 2026-07-17 | P0-R009 | inexistente | controlled permanente desde P0-01 | Se conservó JSON Schema como autoridad y se comprobaron consumidores generados sin otorgarles autoridad normativa. |
| 2026-07-17 | P0-R010 | inexistente | planned para P0-02–P0-07 | P0-01 cierra contratos, no runtimes; cada capacidad conserva su gate y task propia. |
| 2026-07-17 | P0-R010 | planned para P0-02–P0-07 | energía resolved; planned para P0-03–P0-07 | P0-02 implementó y validó budget, FSM, degradación y replay energético; las demás capacidades siguen sin iniciar. |
| 2026-07-17 | P0-R011 | inexistente | controlled para P0; planned P0-08/P1a | El brownout es un modelo replay, no evidencia de storage durable ni corte eléctrico físico. |
| 2026-07-17 | P0-R007 | controlled en P0; planned P1a/campo | protocolo simulado resolved; custodia física controlled/planned | P0-03 probó revocación/rekey offline sin afirmar secure storage ni resistencia física. |
| 2026-07-17 | P0-R010 | energía resolved; planned para P0-03–P0-07 | energía y P0-03 resolved; planned P0-04–P0-07 | P0-03 implementó crypto, reducer SOS y política genérica; no implementó adapters específicos ni tasks posteriores. |
| 2026-07-17 | P0-R012 | inexistente | controlled permanente P0; reemplazo P1a | Los vectores determinísticos son evidencia reproducible, no secretos operativos. |
| 2026-07-17 | P0-R001 | planned para P0-04 | controlled P0; planned P1a | P0-04 fijó fuentes/versiones y límites; firmware, wire behavior, hardware y RF permanecen `unverified`. |
| 2026-07-17 | P0-R008 | planned para P0-04/P0-09 | controlled por pins; review P0-09/P1 | Tres pins oficiales y licencias quedaron en el workload; su vigencia no se extrapola fuera de la simulación. |
| 2026-07-17 | P0-R010 | P0-02/P0-03 resolved; planned P0-04–P0-07 | P0-02–P0-04 resolved; planned P0-05–P0-07 | P0-04 implementó adapters/modelos opacos y gates; no implementó federación, terminal ni beacons. |
| 2026-07-17 | P0-R006 | planned para P0-05 | controlled para correctness P0; performance/representatividad planned P0-09/P1a | P0-05 ejecutó el denominador completo con generador/seed/hash; no produjo benchmark ni evidencia operacional. |
| 2026-07-17 | P0-R010 | P0-02–P0-04 resolved; planned P0-05–P0-07 | P0-02–P0-05 resolved; planned P0-06–P0-07 | P0-05 implementó autonomía, federación y reconciliación simuladas; terminal y beacons siguen sin iniciar. |
