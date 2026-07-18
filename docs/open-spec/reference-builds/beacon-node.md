# Beacon por capacidades

## Alcance

Nodo con una o más modalidades sustituibles. Una modalidad basta; acústica,
movimiento y térmica forman sólo una referencia opcional.

## Plano funcional

`modalidad → features locales → Observation → store-and-forward opcional`

El core conserva la cadena `Observation → Evidence → FusionResult`.

## BOM por capacidades

- procesamiento local y retención acotada;
- al menos una modalidad con schema/calibración;
- transporte de observaciones opcional.

## Reutilización

Sensores o gateways existentes se integran con un adapter que declare mapping,
versión, calibración, limitaciones, datos ausentes y disable procedure.

## Verificación

Reproducir artefactos, cobertura insuficiente, shared cause y OOD. Verificar
abstención, ausencia de inferencia negativa y raw capture deshabilitado.

## Límites

No acredita presencia, ausencia, identidad, diagnóstico, rango o sensibilidad.
Captura continua o inferencia automática de personas detiene el perfil.
