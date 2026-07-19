# Receta: energía de sitio sustituible

## Objetivo
Alimentar cargas locales con degradación medible y reserva crítica, sin prometer operación perpetua.
## Audiencia
Constructores e integradores de energía.
## Prerrequisitos
Load profile, duración, entorno, conectores y límites de cada componente.
## Capacidades necesarias
Almacenamiento protegido, distribución, medición, aislamiento y fuente opcional.
## Alternativas permitidas
Solar, red, generador, vehículo, batería portátil o reemplazo manual; todo es reemplazable.
## Componentes e interfaces
`fuente → protección/control → almacenamiento → distribución → cargas`; `EnergyStatus` informa sin garantizar autonomía.
## Pasos
Inventariar cargas; dimensionar Wh con pérdidas/margen; reservar SOS; definir umbrales; elegir adapters; simular y, opcionalmente, medir la combinación exacta.
## Resultado esperado
Diagrama, BOM por capacidades, presupuesto y apagado/recuperación definidos.
## Validación mínima
Gate de energía, revisión de polaridad/protecciones y brownout simulado.
## Fallos comunes y recuperación
Ante sobrecarga aislar ramas degradables; ante brownout reiniciar en modo seguro y verificar storage.
## Safety, privacidad y preservación
Evitar backfeed, sobretemperatura y polaridad incorrecta; no ocultar un riesgo crítico por minimizar telemetría.
## Estado de evidencia
Receta `specified`; desempeño físico `unverified`.
## Qué no demuestra
No demuestra 72 horas, sostenibilidad, seguridad del conjunto ni vida útil.
## Contratos normativos relacionados
[Energía](../../specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json) y [guía](../guides/energy.md).
