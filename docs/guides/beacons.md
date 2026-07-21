# Beacons multimodales

## Objetivo

Construir beacons acústicos, de movimiento, térmicos o extensibles que publiquen observaciones con incertidumbre y abstención.

## Audiencia

Integradores de sensores, analistas de evidencia y responsables de privacidad/safety.

## Prerrequisitos

Zona/tiempo definidos, modalidad disponible, calibración declarada, política de review y retención, y un canal de telemetría.

## Capacidades necesarias

Al menos una modalidad, `Observation`, provenance, unidad, incertidumbre, health, timestamps y estado de sensores ausentes.

## Alternativas permitidas

Acústica por bandas/rasgos sin audio persistente por defecto, PIR/acelerometría, térmica, o nuevas modalidades mediante adapter. La fusión multimodal es opcional y debe poder abstenerse.

## Componentes e interfaces

Sensor, adapter, `BeaconCapability`, `Observation`, almacenamiento/review y transporte máquina. Los plugins publican observaciones; nunca escriben hechos consolidados.

## Pasos

1. Declarar modalidad, rango operativo, calibración, precisión y limitaciones.
2. Capturar una señal y transformarla a observación, conservando provenance e incertidumbre.
3. Separar `observation`, `hypothesis` y `consolidated fact`.
4. Aplicar reglas determinísticas y permitir `unknown`/abstención.
5. Enviar sólo rasgos mínimos; preservar material crítico en una zona de review si la vida puede estar en riesgo.
6. Combinar modalidades sin convertir la falta de una en evidencia negativa.
7. Ejecutar replay con presencia, ruido, sensor ausente y datos ambiguos.

## Resultado esperado

Observaciones explicables, revisables y degradables, sin claims de detección universal.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-beacons`; datasets sintéticos por modalidad, abstención ante insuficiencia y ausencia de inferencias negativas.

## Fallos comunes y recuperación

Ante ruido o drift, bajar confianza/abstenerse y solicitar review; recalibrar antes de reactivar. Ante sensor ausente, declarar `missing`, no producir cero como observación. Ante almacenamiento lleno, priorizar evidencia crítica y aplicar retención gobernada.

## Safety, privacidad y preservación

Voces, calor y movimiento pueden ser sensibles. Minimizar payloads y acceso, pero preservar señales de posible distress cuando descartarlas pueda afectar vida; registrar la excepción.

## Estado de evidencia

Modalidades y contratos `specified`; fixtures son `simulated`. Sensibilidad, falsos positivos y clasificación física son `unverified`.

## Qué no demuestra

Silencio acústico, falta de movimiento, falta de calor o ausencia de detección nunca demuestran ausencia de una persona o animal.

## Contratos normativos relacionados

[Perfiles de beacon](../../specs/openbrec/1.0.0-draft.1/beacon-capability-profiles.json), [Observation](../../schemas/core/1.0.0/observation.schema.json) y [matriz funcional](../decision-matrices/open-spec-functionality-matrix.json). Los contratos de máquina del dominio viven como addons en schemas/addons/1.0.0/ ([catálogo](../../schemas/addons/catalog.json)): `beacon-capability`, `beacon-observation`, `beacon-health` y `beacon-placement`.

**Addons de review y captura gobernada (sin guía propia):** dos addons del dominio de beacons no tienen guía porque son eventos internos del pipeline de evidencia, no tareas de operador. `capture-authorization-event` registra la autorización firmada de una captura cruda gobernada (modo de captura, vigencia, actor, política de retención, razón y limitaciones): es el carril por el que una señal de posible distress puede preservarse con control dual. `review-task-event` modela la tarea de revisión humana sobre una observación (estado de revisión, disposición, actor, notas): ninguna observación sensible se promueve sin ese review. Un tercer addon, `terminal-capability`, declara la capacidad de una terminal offline y se describe en [Mensajería y SOS](messaging-sos.md).
