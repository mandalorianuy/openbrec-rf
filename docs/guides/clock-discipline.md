# Disciplina de reloj offline

## Objetivo

Declarar fuentes de tiempo, deriva e incertidumbre de reloj para que toda observación pueda ordenarse y auditarse sin depender de tiempo de red.

## Audiencia

Integradores de sensores, mantenedores de fusión y analistas de evidencia.

## Prerrequisitos

Al menos una fuente de tiempo declarada por nodo y un canal para reportar saltos de reloj al operador.

## Capacidades necesarias

`ClockDisciplineProfile`, timestamps canónicos en los contratos core y propagación de `clock_uncertainty_seconds` a las observaciones.

## Alternativas permitidas

Fuentes `gnss`, `pps`, `ntp_local` o `manual`, con roles `primary`, `backup` y `last_resort`. La hora manual es válida si declara su incertidumbre; nunca se presenta como precisa.

## Componentes e interfaces

Cada fuente declara `declared_uncertainty_seconds` y `max_drift_seconds_per_day`. La política de observaciones exige el campo `clock_uncertainty_seconds` cuando aplica y fija un máximo aceptable. El holdover define cuánto tiempo se opera sin fuente antes de degradar a hora manual o declarar el tiempo `unknown`.

## Pasos

1. Declarar fuentes, roles, incertidumbre y deriva por nodo.
2. Propagar `clock_uncertainty_seconds` a cada `Observation`.
3. Monitorear violaciones de monotonía y desacuerdo entre fuentes.
4. Ante salto de reloj, fallar visible y notificar al operador (`fail_visible`).
5. Agotado el holdover, degradar a hora manual o declarar tiempo desconocido.

## Resultado esperado

Evidencia ordenable con incertidumbre temporal explícita y saltos de reloj visibles en auditoría.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; el fixture inválido demuestra que `silent_reorder_allowed: true` es rechazado.

## Fallos comunes y recuperación

Salto de reloj: congelar el ordenamiento automático, marcar la evidencia afectada y dejar que el operador decida; **nunca reordenar silenciosamente evidencia almacenada**. Pérdida de GNSS: conmutar a la fuente backup declarada y aumentar la incertidumbre publicada.

## Safety, privacidad y preservación

Un reloj corrupto puede ocultar o desordenar evidencia crítica; por eso el salto de reloj es un evento visible y auditable, no una corrección transparente.

## Estado de evidencia

El perfil está `specified`; las deriva e incertidumbres de ejemplo no provienen de medición física.

## Qué no demuestra

No demuestra sincronización real entre nodos ni precisión de GNSS/PPS en campo; sólo obliga a declararla.

## Contratos normativos relacionados

[ClockDisciplineProfile](../../schemas/addons/1.0.0/clock-discipline-profile.schema.json), [catálogo de addons](../../schemas/addons/catalog.json) y [Observation](../../schemas/core/1.0.0/observation.schema.json).
