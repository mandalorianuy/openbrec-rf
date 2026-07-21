# Mensajería, estado, SOS y ubicación

## Objetivo

Implementar mensajes humanos breves con semántica verificable, reintentos y operación offline.

## Audiencia

Desarrolladores de terminales/adapters, operadores y revisores de seguridad.

## Prerrequisitos

Identidades por incidente, reloj/secuencia persistente, almacenamiento append-only, claves de aplicación y un transporte elegido.

## Capacidades necesarias

Texto breve, estado, SOS y ubicación; autenticidad de aplicación, deduplicación, TTL, prioridad y lifecycle derivado.

## Alternativas permitidas

Cualquier bearer puede transportar el contrato. La UI puede ser PWA, teléfono, terminal dedicado o integración existente si conserva accesibilidad y semántica.

## Componentes e interfaces

`HumanMessage`, `TransportEnvelope` y eventos `created`, `accepted_by_adapter`, `transmitted`, `received_by_peer`, `displayed_to_human`, `operationally_acknowledged`, `expired` o `failed`. El estado se deriva; no se acepta un estado final enviado por el transporte.

## Pasos

1. Crear identidad y claves por incidente; registrar dispositivo/actor sin usar el Node ID del fabricante como identidad suficiente.
2. Serializar, canonicalizar y firmar/MAC el mensaje.
3. Encolar localmente y priorizar SOS sobre estado/telemetría.
4. Reintentar con backoff hasta TTL sin crear IDs nuevos.
5. Registrar cada transición append-only con actor/dispositivo cuando aplique.
6. Mostrar por separado recepción técnica, visualización humana y aceptación operativa.
7. Tras partición o reinicio, reanudar y deduplicar por identidad/evento.

## Resultado esperado

Mensajes trazables y resistentes a duplicados, con confirmaciones que no exageran su significado.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-messaging`; fixtures válidos/inválidos y replay de duplicado, reordenamiento, expiración y reinicio.

## Fallos comunes y recuperación

Si falta autenticidad, marcar no verificado y preservar; no atribuirlo a una persona. Si no hay acuse, mantener estado explícito y cambiar bearer/carry cuando sea posible. Nunca convertir timeout en “persona no encontrada”.

## Safety, privacidad y preservación

La vida precede a la minimización cuando existe conflicto real: conservar posible distress en cuarentena gobernada. Limitar accesos, retención y exportación; no descartar silenciosamente contenido crítico.

> ⚠️ El derivador determinista de claves del simulador (`_simulated_only_derived_bytes` en `openbrec/messaging.py`, dominio `openbrec-p0-simulated-only`) existe **solo** para los fixtures de laboratorio: cualquier clave así derivada es públicamente reproducible. Está prohibido usarlo fuera del contexto `lab-sim`; los despliegues reales provisionan, rotan y revocan claves por el ciclo de vida offline de claves.

## Estado de evidencia

Semántica `specified` y fixtures/replay `simulated`; autenticidad, UX y entrega sobre dispositivos reales permanecen `unverified`.

## Qué no demuestra

Un `received_by_peer` no demuestra lectura; `displayed_to_human` no demuestra comprensión; `operationally_acknowledged` no garantiza respuesta ni rescate.

## Contratos normativos relacionados

[Mensajería interoperable](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json), [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [conformance](../open-spec/CONFORMANCE.md). Los contratos de máquina del dominio viven como addons en schemas/addons/1.0.0/ ([catálogo](../../schemas/addons/catalog.json)): `human-message`, `human-message-event` y `terminal-capability` (declaración de capacidad de una terminal offline: acciones disponibles sin red, modos de entrada/salida, accesibilidad y capacidades ausentes).
