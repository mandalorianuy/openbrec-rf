# Registro de víctimas confirmadas por operador

## Objetivo

Registrar personas localizadas, extraídas o trasladadas durante un incidente, exclusivamente por confirmación humana, con trazabilidad a las observaciones que motivaron el registro.

## Audiencia

Operadores de consola, comandantes de incidente y responsables de privacidad/safety.

## Prerrequisitos

Incidente declarado, identidad de operador con `actor_device_binding` vigente, handling policy aceptada y al menos una fuente (observación, anotación o reporte directo del operador).

## Capacidades necesarias

`VictimRecord`, `Observation` como fuente, provenance, handling policy y un journal append-only.

## Alternativas permitidas

El registro puede referenciar observaciones de sensores, anotaciones de operador o sólo el reporte directo del operador que confirma. El triage START (`immediate`, `delayed`, `minor`, `expectant`) es opcional y siempre lo asigna un humano.

## Componentes e interfaces

El operador crea el `VictimRecord`; la fusión y los plugins nunca lo crean. Cada actualización es una nueva revisión append-only (`revision` creciente, `updates_append_only: true`), nunca una sobrescritura.

## Pasos

1. Confirmar humanamente la localización y crear el registro con estado `located`.
2. Vincular las `source_observation_ids` y/o `source_annotation_ids` que motivaron el registro (pueden ser vacías si la fuente es el reporte directo).
3. Asignar triage START si el operador lo determina.
4. Registrar provenance y handling policy por referencia (`provenance_ref`, `handling_policy_ref`).
5. Actualizar el estado (`extraction_in_progress`, `extracted`, `transported`, `handed_over`) sólo mediante nuevas revisiones confirmadas por un humano.

## Resultado esperado

Un historial auditable por víctima, con fuentes, responsable humano y cadena de revisiones, separado de observaciones e hipótesis automáticas.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; los fixtures inválidos demuestran que `confirmation.method` distinto de `human_operator_confirmation`, `silence_means_absence: true` o `updates_append_only: false` son rechazados.

## Fallos comunes y recuperación

Ante una confirmación dudosa, no editar el registro: agregar una revisión con la corrección y su razón. Ante duplicados de persona, mantener ambos registros y resolver por anotación de operador, nunca por merge automático.

## Safety, privacidad y preservación

Un `VictimRecord` es dato personal sensible: aplica la handling policy del incidente, acceso por rol y retención limitada. Preservar todo registro y sus fuentes cuando la vida pueda estar en riesgo.

## Estado de evidencia

El contrato está `specified`; no existe implementación de runtime ni validación de campo.

## Qué no demuestra

Un sector sin `VictimRecord` no demuestra ausencia de personas (`silence_means_absence: false` es invariante del contrato). El registro acredita confirmación humana, no hallazgo automático.

## Contratos normativos relacionados

[VictimRecord](../../schemas/addons/1.0.0/victim-record.schema.json), [catálogo de addons](../../schemas/addons/catalog.json), [Observation](../../schemas/core/1.0.0/observation.schema.json) y [HandlingPolicy](../../schemas/core/1.0.0/handling-policy.schema.json).
