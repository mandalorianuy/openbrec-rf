# Registro gobernado de residuales P0

- Estado: activo
- Plan: `docs/superpowers/plans/2026-07-17-openbrec-p0-simulated-addons-plan.md`
- Owner del registro: `release-reviewer`
- Regla: todo residual debe estar `resolved`, `controlled`, `planned` o `blocked`
- Estado inicial: cero residuales `blocked`; ninguno autoriza claims fuera de P0

## Registro

| ID | Residual | Estado | Owner | Resolución o plan | Gate/artefacto | Stop condition |
|---|---|---|---|---|---|---|
| P0-R001 | Los modelos de Meshtastic, MeshCore y Reticulum pueden divergir de firmware/wire behavior real. | planned para P0-04; hardware permanece `unverified` | `radio-transport-maintainer` | Fijar versión/fuente, capability manifest, fixtures raw y limitaciones; validar físicamente sólo en P1a. | `transport-comparison`, provenance y review multi-bearer | Afirmación no respaldada o versión flotante bloquea aceptación P0-04. |
| P0-R002 | P0 no valida frecuencia, regulación, coexistencia ni TX en ninguna jurisdicción. | controlled por frontera P0; planificado para P1a/P1b | `privacy-safety-reviewer` | Cero TX y cero control de radio física en P0; perfil regulatorio/conducted/radiated se decide después. | secret/safety scan y review P0-09 | Cualquier TX, compra o claim RF detiene P0. |
| P0-R003 | Energía simulada no acredita loads reales, capacidad descargable ni autonomía de 72 horas. | controlled por frontera P0; planificado para P1a-06/P1a-07 | `energy-maintainer` | P0 sólo valida contratos/FSM; caracterización y storage-only 72h requieren plan P1a. | `energy-replay` y scan de claims | Claim físico, solar o “indefinido” bloquea aceptación. |
| P0-R004 | Fixtures beacon no representan rubble, ruido, clima, placement ni lotes físicos completos. | planned para P0-07 y campañas P1 | `beacon-science-maintainer` | Declarar environment class, provenance, OOD y límites; conservar unknown/abstention y diseñar protocolo físico posterior. | `beacon-replay`, model/dataset cards | Ocultar clase omitida o generalizar fuera del fixture bloquea P0-07/P0-09. |
| P0-R005 | Automatización P0 no demuestra comprensión bajo estrés ni accesibilidad humana real. | controlled en P0; planificado para P1a-03 | `product-ux-reviewer` | P0 valida semántica/UI técnica y versiona el protocolo con 8 operadores y 8 personas no preparadas. | `terminal-ux`, `accessibility`, guion P1a | Claim de usabilidad humana o field readiness bloquea P0-06/P0-09. |
| P0-R006 | La escala 50k/60/5/2 puede depender de recursos del runner y no representa todas las distribuciones operativas. | planned para P0-05 | `federation-maintainer` | Versionar generador, seed, topología, carga y recursos; separar correctness de performance y reportar límites. | `federation-scale` y campaign manifest | Reducir escala/denominador sin nueva decisión bloquea P0-05. |
| P0-R007 | Claves y secure storage simulados no acreditan custodia, HSM ni resistencia de terminal robado. | controlled en P0; planificado para P1a/campo | `privacy-safety-reviewer` | Usar sólo material sintético efímero; probar protocolo/revocación sin claim hardware-backed. | `human-message-security`, secret scan | Clave real/default o claim HSM/campo bloquea el gate. |
| P0-R008 | Fuentes, defaults y seguridad de bearers cambian con rapidez. | planned para P0-04 y P0-09 | `radio-transport-maintainer` + `release-reviewer` | Pin de versión/commit, fecha de revisión, SBOM/licencia y evidencia primaria por adapter. | capability manifest, SBOM y vulnerability receipt | Fuente no fijada, advisory sin gobernar o default credential bloquea aceptación. |
| P0-R009 | Pydantic y TypeScript no expresan todos los constraints Draft 2020-12; la intersección `BeaconObservation` puede conservar un índice TypeScript `unknown`. | controlled permanente desde P0-01 | `contract-maintainer` | JSON Schema con `FormatChecker` y registry local es autoridad; corre antes de consumidores generados. Los 36 fixtures válidos compilan en ambos consumidores y 126 negativos se evalúan contra JSON Schema. | `addon-contracts`, `addon-fixtures`, `contracts-gen --check` | Un consumidor generado nunca reemplaza validación normativa; drift o error de asignabilidad falla el gate. |
| P0-R010 | P0-01 define payloads y boundaries, pero no implementa reducers, criptografía, energía, adapters, federación, terminal ni beacon runtime. | planned para P0-02–P0-07 | owners de cada task consumidora | Cada task debe implementar sus invariantes con replay/fallos y no puede usar la existencia del schema como prueba funcional. | gates y receipts P0-02–P0-07 | Claim funcional, operativo o físico basado sólo en contrato bloquea aceptación de la task consumidora y P0-09. |

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
