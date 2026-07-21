# Arquitectura documental de OpenBREC

Este mapa separa la norma de sus implementaciones y ofrece una única entrada pública: [Start Here](START_HERE.md). La Open Spec se puede publicar, estudiar e implementar sin poseer hardware. Una prueba física sólo eleva la confianza de la combinación exacta ensayada.

## Capas y autoridad

### A. Open Spec normativa

[`docs/open-spec/`](open-spec/README.md), [`schemas/`](../schemas/) y [`specs/openbrec/`](../specs/openbrec/) definen contratos, invariantes, estados, interfaces, perfiles de capacidad, interoperabilidad y conformidad. Una implementación puede reemplazar cualquier componente mientras conserve esos contratos. La versión `1.0.0-draft.1` queda funcionalmente congelada salvo errores, contradicciones o cambios de seguridad.

### B. Reference implementation

[`openbrec/`](../openbrec/), [`apps/`](../apps/), [`services/`](../services/) y [`docker-compose.yml`](../docker-compose.yml) demuestran una forma de implementar la norma, incluido el pipeline lab-sim end-to-end (API → MQTT → worker → fusión → PostgreSQL → PWA) con datos sintéticos. Son reemplazables y no convierten Python, React, MQTT, PostgreSQL ni un dispositivo particular en requisitos normativos.

### C. Manuales y guías

[`docs/guides/`](guides/README.md) explica cómo seleccionar, construir, integrar, operar, validar y diagnosticar. Las guías orientan tareas; si contradicen la capa A, prevalece la Open Spec. Incluye las guías prácticas originales (quickstart, planificación, energía, transportes, mensajería, beacons, federación, construcción, troubleshooting), la guía del implementador ([implementing-the-spec](guides/implementing-the-spec.md)) y las guías de los addons experimentales ([víctimas](guides/victim-tracking.md), [identidad y claves](guides/identity-key-lifecycle.md), [reloj](guides/clock-discipline.md), [GIS offline](guides/offline-mapping.md), [interop CAP/EDXL](guides/interop-emergency-standards.md), [regulatorio](guides/regulatory.md), [doctrina USAR](guides/usar-doctrine-integration.md)) y las guías de los dominios de RF sensing reintegrados ([CSI](guides/csi-sensing.md), [RF pasiva](guides/passive-rf.md), [SDR receive-only](guides/sdr-beacons.md), [drones como geometría](guides/drone-geometry.md), [RF quieting](guides/rf-quieting.md), [offline finding](guides/offline-finding.md)), la excepción gobernada del [AP de emergencia con auto-join](guides/emergency-autojoin.md) y la [integración con el ecosistema SAR](guides/ecosystem-integration.md), cuya base citable de evidencia vive en [`docs/research/`](research/rf-sensing-state-of-the-art.md).

### D. Reference builds

[`docs/reference-builds/`](reference-builds/README.md) reúne composiciones reproducibles basadas en capacidades. Los productos citados son ejemplos reemplazables, nunca requisitos de conformidad.

### E. Evidence packs

[`docs/evidence-packs/`](evidence-packs/README.md) define cómo asociar resultados a una versión, configuración, hardware, entorno y protocolo exactos. Un pack no generaliza sus claims a otros builds.

### F. Field profiles

[`docs/field-profiles/`](field-profiles/README.md) aloja perfiles que hayan sido validados para una misión, entorno o jurisdicción determinada. No existen perfiles de campo validados en la versión actual.

### Documentos de orientación transversal

Documentos de entrada y referencia que no son capa normativa ni guía de tarea:

- [Arquitectura del sistema](architecture.md): vista unificada de planos, overlay, transportes, energía, beacons, federación, pipeline de evidencia y estados.
- [FAQ](faq.md): respuestas cortas a las preguntas habituales, con el nivel de evidencia real.
- [Glosario](glossary.md): definiciones de los términos e identificadores clave.
- [Investigación](research/sar-landscape.md): `docs/research/` aloja las bases citables no normativas — el [panorama SAR/USAR y posicionamiento](research/sar-landscape.md), la [arquitectura de integración con el ecosistema SAR](research/sar-integration.md) y el [estado del arte de RF sensing](research/rf-sensing-state-of-the-art.md).
- [Colaboración institucional](outreach/institutional-collaboration.md): `docs/outreach/` aloja el programa de validación física con universidades e instituciones ([programa y labs](outreach/institutional-collaboration.md), [pitch de una página](outreach/pitch-onepager.md)).

### Gobernanza, decisiones y seguridad

La autoridad transversal se ejerce con registros append-only, fuera de la capa normativa pero vinculados a ella:

- [`docs/adr/`](adr/): decisiones de arquitectura. ADR-0001 fija alcance del core, autoridad y red lines; [ADR-004](adr/ADR-004-rf-sensing-reintegration.md) reintegra los dominios de RF sensing como addons experimentales y mantiene vigentes ADR-001 (RuView), ADR-002 (drones) y ADR-003 (aislamiento medido); [ADR-005](adr/ADR-005-emergency-autojoin-governed-exception.md) fija el AP de emergencia con auto-join como excepción gobernada bajo `emergency_assumed_risk`.
- [`docs/open-spec/rfc/`](open-spec/rfc/): RFCs de la spec según [RFC-PROCESS](open-spec/RFC-PROCESS.md): [RFC 0001](open-spec/rfc/0001-rf-sensing-addons.md) (addons de RF sensing, `accepted`), [RFC 0002](open-spec/rfc/0002-offline-finding-addon.md) (`offline-finding-observation`, `accepted`), [RFC 0003](open-spec/rfc/0003-emergency-autojoin-addon.md) (`emergency-autojoin-profile`, `accepted`) y [RFC 0004](open-spec/rfc/0004-cot-tak-bridge-addon.md) (`cot-bridge-profile`, `accepted`).
- [`docs/security/`](security/): threat model y reviews datadas, incluidas las reviews de diseño de los dominios RF sensing (`rf-sensing-csi`, `passive-rf`, `sdr-receive`, `drone-geometry`, `rf-quieting`).
- [`docs/decision-matrices/`](decision-matrices/): matrices de decisión con historial de gobernanza; la de 2026-07-19 registra la reintegración de RF sensing.

### Material de soporte del repositorio

Directorios de trabajo que no son capa normativa ni documentación pública de tarea:

- [`docs/governance/`](governance/): registros residuales de la ejecución M0/P0 y el intake del carril P1a (`P1A_ASSET_INTAKE`).
- [`docs/runtime/`](runtime/): notas de operación del lab-sim y SOPs de ciclo de vida de claves.
- [`docs/testing/`](testing/): protocolos de ensayo humano del carril P1a (p.ej. comprensión de terminal).
- [`docs/assets/`](assets/): imágenes y recursos referenciados por los documentos.
- [`docs/superpowers/`](superpowers/): planes internos de diseño y ejecución; material de trabajo sin autoridad normativa.

### Documentos legacy (sin autoridad)

[`docs/legacy/`](legacy/README.md) archiva la documentación de la encarnación Wi-Fi-CSI previa del proyecto, con estado `superseded`. Es contexto histórico: no participa de la precedencia ni define comportamiento vigente.

## Audiencias y ruta única

| Audiencia | Entrada recomendada | Resultado |
|---|---|---|
| Lector | [Start Here](START_HERE.md) | Comprende alcance, límites y arquitectura. |
| Constructor | [Construcción y reutilización](guides/building-reuse.md) | Elige capacidades, interfaces y BOM sustituible. |
| Integrador | [Transportes](guides/transports.md) y [federación](guides/federation.md) | Implementa adapters y sincronización. |
| Operador | [Planificación](guides/deployment-planning.md) y [troubleshooting](guides/validation-troubleshooting.md) | Prepara y recupera un deployment. |
| Implementador de la spec | [Cómo implementar la spec](guides/implementing-the-spec.md) | Produce un componente conforme con estado honesto. |
| Contribuidor | [Contribuir](../CONTRIBUTING.md) | Modifica contratos o referencias sin confundir autoridad. |

## Vocabulario público de evidencia

| Estado | Significado permitido |
|---|---|
| `specified` | Contrato y criterios definidos; no implica ejecución. |
| `simulated` | Ejecutado con datos o entorno sintético reproducible. |
| `bench-validated` | Ensayado físicamente en banco para la configuración declarada. |
| `field-validated` | Ensayado en campo bajo el perfil y condiciones declarados. |
| `unsupported` | Fuera del contrato o deliberadamente no soportado. |
| `unverified` | Sin evidencia suficiente para asignar otro estado. |

Los identificadores de máquina `lab_validated` y `field_validated` se muestran al público como `bench-validated` y `field-validated`. El vocabulario vigente es sólo el de la tabla; las reglas para migrar tokens históricos están en el [apéndice](#apéndice-migración-de-vocabulario-histórico).

## Regla de precedencia

La norma define qué debe cumplirse; la implementación demuestra una posibilidad; el manual explica una tarea; el build compone capacidades; el evidence pack sustenta claims acotados; el field profile registra una validación contextual. Ninguna capa inferior modifica silenciosamente una capa superior.

## Apéndice: migración de vocabulario histórico

Reglas para traducir tokens de evidencia de versiones anteriores del proyecto al vocabulario vigente. No forman parte del vocabulario activo y no deben aparecer en documentos nuevos:

- `experimental` pasa a `simulated` sólo si existe ejecución sintética reproducible y, si no, a `unverified`.
- `supported` no tiene equivalencia automática: exige clasificar la evidencia exacta.
- `unavailable` pasa a `unsupported` sólo cuando está deliberadamente fuera de alcance y, si no, a `unverified`.
- `watch`, `active` o `superseded` describen ciclos de vida de registros, no evidencia de una capacidad.
