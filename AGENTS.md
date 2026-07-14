# AGENTS.md — reglas para Codex y otros agentes

## Objetivo
Construir OpenBREC RF de forma incremental, reproducible, segura y verificable.

## Principios
1. Safety before capability: ninguna función ofensiva de Wi-Fi o radio.
2. Evidence, not assertions: toda inferencia debe conservar fuentes y confianza.
3. Offline-first: ninguna dependencia cloud obligatoria.
4. Capability-driven: el sistema opera con los sensores disponibles, sin requerir BFI, UWB o radar.
5. Replayable: todo pipeline debe poder ejecutarse desde archivos PCAP/JSONL grabados.
6. Privacy-minimizing: hash rotativo, retención limitada y stripping de payloads.
7. Open hardware friendly: no depender de un único fabricante.

## Stack preferido
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, PostgreSQL.
- Bus de campo: MQTT 5 / Mosquitto.
- Tareas: asyncio; Celery solo si aparece una necesidad real.
- UI: React + TypeScript + Vite, PWA offline.
- Firmware: ESP-IDF, C/C++.
- Infra: Docker Compose; k3s opcional y posterior.
- Observabilidad: OpenTelemetry + Prometheus, activable por perfil.
- Tests: pytest, hypothesis, Playwright, ESP-IDF Unity.

## Reglas de implementación
- No inventar soporte de hardware. Cada driver declara `supported`, `experimental` o `unverified`.
- No guardar contenido de paquetes, credenciales, SSID históricos sensibles ni identificadores permanentes por defecto.
- Separar observación, hipótesis y hecho consolidado.
- Todo resultado incluye: timestamp, zona, precisión, confianza, fuentes, sensores ausentes y explicación resumida.
- Los plugins no pueden escribir directamente la tabla de hechos; solo publican observaciones.
- La fusión debe funcionar sin ML mediante reglas determinísticas y filtros básicos.
- Los modelos ML deben estar versionados y permitir abstención/`unknown`.
- No implementar TX activo en SDR en la fase inicial.

## Definition of Done general
- Código formateado, tipado y testeado.
- Contratos JSON validados.
- Migraciones reproducibles.
- Demo offline con datos sintéticos.
- Documentación actualizada.
- Threat model y safety review para toda nueva capacidad de radio.


## RuView, drones y aislamiento RF

- RuView debe permanecer opcional, version-pinned y reemplazable.
- Ningún servicio OpenBREC controla vuelo; solo telemetría y payload con confirmación humana.
- No aceptar claims de atenuación RF sin medición del conjunto.
- No inferir ausencia de víctima por silencio radioeléctrico.
- Toda nueva fuente debe producir fixtures de replay y explicar incertidumbre.
