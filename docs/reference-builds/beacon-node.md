# Receta: beacon por capacidades

## Objetivo
Publicar observaciones desde una o más modalidades sustituibles con incertidumbre y abstención.
## Audiencia
Integradores de sensores y analistas de evidencia.
## Prerrequisitos
Modalidad, calibración declarada, zona/tiempo y política de retención/review.
## Capacidades necesarias
Al menos una modalidad, procesamiento, `Observation`, health y almacenamiento acotado.
## Alternativas permitidas
Acústica, movimiento, térmica o extensión futura; sensores y gateways reemplazables.
## Componentes e interfaces
`modalidad → features → Observation → store-and-forward`; el core conserva provenance.
## Pasos
Declarar límites; integrar adapter; deshabilitar raw por defecto; generar fixtures; probar missing/OOD; combinar sólo con abstención.
## Resultado esperado
Observaciones explicables que no se convierten directamente en hechos.
## Validación mínima
Artefactos, shared cause, datos ambiguos y sensor ausente producen incertidumbre/abstención.
## Fallos comunes y recuperación
Ante drift recalibrar; ante sensor ausente declarar missing; ante ruido abstenerse y revisar.
## Safety, privacidad y preservación
Minimizar voz/calor/movimiento; preservar posible distress bajo acceso gobernado.
## Estado de evidencia
Receta `specified`, fixtures `simulated`, sensibilidad física `unverified`.
## Qué no demuestra
No demuestra presencia, ausencia, identidad, diagnóstico, rango ni sensibilidad.
## Contratos normativos relacionados
[Beacons](../../specs/openbrec/1.0.0-draft.1/beacon-capability-profiles.json) y [guía](../guides/beacons.md).
