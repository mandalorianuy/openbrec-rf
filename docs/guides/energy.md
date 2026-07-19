# Energía off-grid

## Objetivo

Dimensionar y operar fuentes, baterías y solar como addons combinables, con reserva explícita para funciones críticas.

## Audiencia

Constructores, integradores y responsables de logística/energía.

## Prerrequisitos

Inventario de cargas por estado, duración objetivo, temperatura, conectores y restricciones de transporte y seguridad.

## Capacidades necesarias

Medición de tensión/corriente, protección eléctrica, almacenamiento, fuente primaria y estados de degradación observables.

## Alternativas permitidas

Energía por componente, sitio compartido, híbrida o reemplazo logístico. Solar, generador, red disponible y baterías portátiles son source adapters opcionales y combinables.

## Componentes e interfaces

`EnergyStatus`, fuente, almacenamiento, conversión DC/DC, protección, cargas críticas/degradables y telemetría local. Componentes comerciales son reemplazables si cumplen interfaces y límites.

## Pasos

1. Medir o estimar potencia por modo y duty cycle; marcar estimaciones `unverified`.
2. Calcular Wh utilizables con profundidad de descarga, pérdidas, temperatura, envejecimiento y margen.
3. Reservar energía separada para SOS, persistencia y apagado seguro.
4. Definir umbrales con histéresis: normal, conservación, crítico y shutdown.
5. Elegir fuentes/adapters y conectores protegidos.
6. Simular 72 horas con un perfil de cargas versionado; no llamarlo autonomía física.
7. Para elevar el claim, medir trazas y brownout en banco bajo un protocolo exacto.

## Resultado esperado

Presupuesto reproducible, diagrama de potencia, degradación predecible y ausencia de claims perpetuos.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-energy` y una tabla de cargas cuya suma, pérdidas, margen y reserva sean verificables.

## Fallos comunes y recuperación

Si la carga excede presupuesto, reducir telemetría o añadir almacenamiento/fuente; no consumir la reserva crítica. Tras brownout, verificar replay, reloj, almacenamiento y estado antes de reactivar cargas.

## Safety, privacidad y preservación

Usar protecciones, polaridad, fusibles y límites del fabricante. La telemetría energética puede revelar ubicación/patrón operativo: compartir sólo lo necesario sin ocultar un riesgo crítico.

## Estado de evidencia

Perfiles `specified` y simulación contractual disponible. Autonomía, solar y seguridad de una construcción permanecen `unverified` sin medición física.

## Qué no demuestra

No demuestra 72 horas reales, vida útil, seguridad eléctrica, rendimiento solar, operación climática ni certificación.

## Contratos normativos relacionados

[Perfiles de energía](../../specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json) y [capacidades de referencia](../../specs/openbrec/1.0.0-draft.1/reference-capability-profiles.json).
