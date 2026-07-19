# Arquitectura documental de OpenBREC

Este mapa separa la norma de sus implementaciones y ofrece una única entrada pública: [Start Here](START_HERE.md). La Open Spec se puede publicar, estudiar e implementar sin poseer hardware. Una prueba física sólo eleva la confianza de la combinación exacta ensayada.

## Capas y autoridad

### A. Open Spec normativa

[`docs/open-spec/`](open-spec/README.md), [`schemas/`](../schemas/) y [`specs/openbrec/`](../specs/openbrec/) definen contratos, invariantes, estados, interfaces, perfiles de capacidad, interoperabilidad y conformidad. Una implementación puede reemplazar cualquier componente mientras conserve esos contratos. La versión `1.0.0-draft.1` queda funcionalmente congelada salvo errores, contradicciones o cambios de seguridad.

### B. Reference implementation

[`openbrec/`](../openbrec/), [`apps/`](../apps/), [`services/`](../services/) y [`docker-compose.yml`](../docker-compose.yml) demuestran una forma de implementar la norma. Son reemplazables y no convierten Python, React, MQTT, PostgreSQL ni un dispositivo particular en requisitos normativos.

### C. Manuales y guías

[`docs/guides/`](guides/README.md) explica cómo seleccionar, construir, integrar, operar, validar y diagnosticar. Las guías orientan tareas; si contradicen la capa A, prevalece la Open Spec.

### D. Reference builds

[`docs/reference-builds/`](reference-builds/README.md) reúne composiciones reproducibles basadas en capacidades. Los productos citados son ejemplos reemplazables, nunca requisitos de conformidad.

### E. Evidence packs

[`docs/evidence-packs/`](evidence-packs/README.md) define cómo asociar resultados a una versión, configuración, hardware, entorno y protocolo exactos. Un pack no generaliza sus claims a otros builds.

### F. Field profiles

[`docs/field-profiles/`](field-profiles/README.md) aloja perfiles que hayan sido validados para una misión, entorno o jurisdicción determinada. No existen perfiles de campo validados en la versión actual.

## Audiencias y ruta única

| Audiencia | Entrada recomendada | Resultado |
|---|---|---|
| Lector | [Start Here](START_HERE.md) | Comprende alcance, límites y arquitectura. |
| Constructor | [Construcción y reutilización](guides/building-reuse.md) | Elige capacidades, interfaces y BOM sustituible. |
| Integrador | [Transportes](guides/transports.md) y [federación](guides/federation.md) | Implementa adapters y sincronización. |
| Operador | [Planificación](guides/deployment-planning.md) y [troubleshooting](guides/validation-troubleshooting.md) | Prepara y recupera un deployment. |
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

Los identificadores de máquina `lab_validated` y `field_validated` se muestran al público como `bench-validated` y `field-validated`. Para migrar vocabulario histórico: `experimental` pasa a `simulated` sólo si existe ejecución sintética reproducible y, si no, a `unverified`; `supported` no tiene equivalencia automática y exige clasificar la evidencia exacta; `unavailable` pasa a `unsupported` sólo cuando está deliberadamente fuera de alcance y, si no, a `unverified`. `watch`, `active` o `superseded` describen ciclos de vida de registros, no evidencia de una capacidad.

## Regla de precedencia

La norma define qué debe cumplirse; la implementación demuestra una posibilidad; el manual explica una tarea; el build compone capacidades; el evidence pack sustenta claims acotados; el field profile registra una validación contextual. Ninguna capa inferior modifica silenciosamente una capa superior.
