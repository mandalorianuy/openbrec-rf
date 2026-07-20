# Interoperación con estándares de emergencia (CAP/EDXL-DE)

## Objetivo

Declarar el mapeo mínimo de `HumanMessage`/SOS hacia alertas OASIS CAP 1.2 envueltas en EDXL-DE 1.0, como contrato para una futura integración con agencias externas.

## Audiencia

Integradores con agencias de emergencia, oficiales de enlace y mantenedores de mensajería.

## Prerrequisitos

Perfil de mensajería vigente, handling policy que autorice la exportación y confirmación humana previa a todo envío externo.

## Capacidades necesarias

`InteropEmergencyStandardsProfile`, `HumanMessage` y un operador que declare la exportación.

## Alternativas permitidas

Sólo exportación (`direction: export_only`). No existe gateway implementado (`gateway_implemented: false` es invariante): el perfil describe transformaciones, no un servicio.

## Componentes e interfaces

El `field_map` declara por campo el elemento CAP destino y la transformación permitida: `copy`, `iso8601_utc`, `controlled_vocabulary` o `incident_rotating_hash` (para seudonimizar origen/celda). EDXL-DE actúa sólo como wrapper de distribución.

## Pasos

1. Seleccionar los tipos de mensaje exportables (`sos`, `location`, `status`, `text`).
2. Declarar el `field_map` con transformaciones controladas.
3. Pseudonimizar identificadores de celda/actor con el hash rotativo del incidente.
4. Obtener confirmación humana antes de exportar.
5. Registrar la exportación en el journal con provenance.

## Resultado esperado

Alertas CAP/EDXL-DE derivables de forma determinística desde mensajes internos, sin elevar claims de aceptación externa.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; los fixtures inválidos demuestran que `gateway_received_means_rescue: true` o `gateway_implemented: true` son rechazados.

## Fallos comunes y recuperación

Agencia inalcanzable: conservar la alerta pendiente y reintentar según la política del incidente; la falta de acuse no cambia el estado operativo interno. Acuse `Ack` recibido: registrarlo como recepción técnica, nunca como aceptación operativa (`cap_ack_means_operational_acceptance: false`).

## Safety, privacidad y preservación

Exportar un SOS fuera del incidente expone datos sensibles: seudonimizar, minimizar campos y exigir confirmación humana. `gateway_received_means_rescue: false` es invariante: que un gateway reciba el mensaje no significa rescate en curso.

## Estado de evidencia

El mapeo está `specified`; no hay gateway implementado ni interoperabilidad probada con ninguna agencia.

## Qué no demuestra

No demuestra conformidad certificada con CAP/EDXL-DE ni aceptación por agencias; es un contrato de mapeo mínimo para trabajo futuro.

## Otros caminos de integración

Este perfil queda como el camino CAP/EDXL (export-only). El resto de la integración con el ecosistema — puente CoT/TAK local, Meshtastic MQTT, locator de CalTopo y APRS opcional — se describe en la guía [Integración con el ecosistema SAR](ecosystem-integration.md) y su [arquitectura de investigación](../research/sar-integration.md); no modifican este perfil.

## Contratos normativos relacionados

[InteropEmergencyStandardsProfile](../../schemas/addons/1.0.0/interop-emergency-standards-profile.schema.json), [catálogo de addons](../../schemas/addons/catalog.json) y [HumanMessage](../../schemas/addons/1.0.0/human-message.schema.json).
