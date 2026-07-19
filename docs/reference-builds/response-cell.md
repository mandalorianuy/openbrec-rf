# ResponseCell

## Objetivo

Construir una célula local con varios operadores/nodos, transportes combinables, persistencia, replay, gateway y beacons opcionales.

## Audiencia

Equipos BREC/USAR e integradores de sitio.

## Prerrequisitos

Kit mínimo funcional, roles de célula, mapa de sectores, presupuesto energético y threat model local.

## Capacidades necesarias

Mensajería humana, telemetría máquina, store-and-forward, core local, gateway opcional y uno o más beacons opcionales.

## Alternativas permitidas

Uno o varios bearers; gateway en laptop/SBC/servidor; energía por componente, compartida o híbrida; sensores acústicos, movimiento o térmicos. Todos son reemplazables.

## Componentes e interfaces

Kits de equipo + [gateway autónomo](response-cell-gateway.md) + [telemetría](machine-telemetry.md) + [energía](energy-site.md) + [beacon](beacon-node.md) opcional. MQTT local es una referencia, no norma.

## Pasos

1. Crear namespace, roles y claves de ResponseCell.
2. Separar colas humano/máquina y reservar SOS.
3. Instalar core/store local y adapters de bearer.
4. Añadir energía y degradaciones medibles.
5. Integrar beacons sólo como observaciones.
6. Ensayar pérdida de cada superior y del gateway.
7. Ensayar replay/reconciliación y documentar rollback.

## Resultado esperado

La célula mantiene funciones críticas y evidencia local durante una partición y puede sincronizar después.

## Validación mínima

Open Spec exit y gates de capacidades en `0`; partición/reinicio/replay sintéticos; cero confirmaciones falsas y abstención de beacons.

## Fallos comunes y recuperación

Si el gateway es single point, devolver colas/identidad a nodos. Si hay congestión, bajar máquina antes que SOS. Si un sensor falla, declarar ausencia y continuar.

## Safety, privacidad y preservación

No exportar claves ni payload crudo por defecto. Preservar distress, provenance y material ambiguo bajo review; no inferir ausencia.

## Estado de evidencia

Build `specified` con escenarios `simulated`; la composición física permanece `unverified`.

## Qué no demuestra

No demuestra capacidad RF, cantidad máxima de nodos, energía, detección, interoperabilidad física ni field readiness.

## Contratos normativos relacionados

[Capacidades](../../specs/openbrec/1.0.0-draft.1/reference-capability-profiles.json), [federación](../../specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json) y [build profiles](../../specs/openbrec/1.0.0-draft.1/reference-build-profiles.json).
