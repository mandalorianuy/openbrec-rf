# Quickstart mínimo off-grid

## Objetivo

Ejecutar localmente un flujo reproducible de terminales, texto breve, estado, SOS y ubicación sin cloud ni transmisión RF.

## Audiencia

Lectores, integradores y constructores que quieren comprobar la semántica antes de elegir hardware.

## Prerrequisitos

Git, `uv`, Python 3.12 y las dependencias ya bloqueadas. El checkout debe estar limpio para producir receipts canónicos.

## Capacidades necesarias

Dos identidades de terminal simuladas, almacenamiento local, reloj monotónico y un adapter de transporte simulado.

## Alternativas permitidas

El adapter simulado puede sustituirse después por Meshtastic, MeshCore, Reticulum, LoRaWAN privado u otro bearer que preserve el overlay OpenBREC.

## Componentes e interfaces

`HumanMessage`, `TransportEnvelope`, lifecycle append-only, fixtures JSONL y verificador offline. Ninguna marca o radio es obligatoria.

## Pasos

1. Clonar el repositorio e instalar el lock sin resolver dependencias nuevas: `uv sync --frozen`.
2. Validar los contratos: `uv run --offline python -m openbrec.verify open-spec`.
3. Validar mensajería y SOS: `uv run --offline python -m openbrec.verify open-spec-messaging`.
4. Ejecutar replay: `uv run --offline python -m openbrec.verify core-replay --bundle fixtures/replay/core/m0-six-node.json`.
5. Inspeccionar el resultado sin interpretar recepción técnica como lectura o rescate.

## Resultado esperado

Contratos válidos, replay determinístico y eventos distinguibles para texto, estado, SOS y ubicación, sin conexión cloud ni TX.

## Validación mínima

Los tres comandos terminan con código `0`. Registrar el SHA, los comandos y los resultados; asignar como máximo `simulated`.

## Fallos comunes y recuperación

Si `uv` intenta usar red, ejecutar primero `uv sync --frozen` con conectividad de provisioning y repetir los gates con `--offline`. Si falla un fixture, no editar el resultado: corregir el contrato o fixture y repetir desde cero.

## Safety, privacidad y preservación

No descartar SOS ambiguos; preservarlos para review con acceso y retención gobernados. Minimizar identificadores, pero no provocar pérdida silenciosa de información crítica.

## Estado de evidencia

`simulated` para la ruta incluida; transportes y hardware físicos permanecen `unverified` hasta un evidence pack aplicable.

## Qué no demuestra

No demuestra alcance, airtime, autenticidad de un dispositivo real, autonomía, cumplimiento regulatorio, detección de personas ni operación de campo.

## Contratos normativos relacionados

[Mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json), [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [conformance](../open-spec/CONFORMANCE.md).
