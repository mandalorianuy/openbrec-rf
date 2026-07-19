# Kit mínimo personal/equipo

## Objetivo

Construir una unidad autónoma para texto breve, estado, SOS y ubicación entre uno o más nodos.

## Audiencia

Equipos pequeños, constructores e integradores que necesitan una base off-grid.

## Prerrequisitos

Dos terminales o instancias simuladas, identidades por incidente, energía local y elección de bearer.

## Capacidades necesarias

UI offline, persistencia, reloj/secuencia, autenticidad de aplicación, ubicación opcional por nodo, energía y transporte.

## Alternativas permitidas

Teléfono más radio, terminal integrado, SBC o simulador; Meshtastic, MeshCore, Reticulum/RNode, LoRaWAN privado con gateway local o carry. Todo componente es reemplazable.

## Componentes e interfaces

`HumanMessage` → `TransportEnvelope` → adapter; almacenamiento append-only; `EnergyStatus`. BOM por capacidades: 1–N terminales, energía por terminal o compartida y al menos un bearer local.

## Pasos

1. Inventariar terminales, energía y radios disponibles.
2. Asignar identidades/keys por incidente y deshabilitar defaults.
3. Integrar el bearer sin delegarle autenticidad ni semántica.
4. Configurar prioridad SOS, TTL, retry y ubicación.
5. Ejecutar el quickstart y fallos de partición/reinicio.
6. Registrar sustituciones y rollback.

## Resultado esperado

El equipo crea, conserva, entrega cuando es posible y muestra mensajes localmente sin hub ni cloud.

## Validación mínima

Gates de mensajería/transporte en `0`; replay de cuatro tipos, duplicado, expiración y reinicio; operación local sin nivel superior.

## Fallos comunes y recuperación

Ante pérdida de bearer, conservar cola y usar alternativa/carry. Ante batería crítica, suspender telemetría y reservar SOS. Ante terminal perdido, revocar y rekey.

## Safety, privacidad y preservación

No presentar ACK técnico como rescate. Minimizar identidad/ubicación, pero preservar distress no verificable para review gobernado.

## Estado de evidencia

Build `specified`; flujo software `simulated`; hardware, energía y bearer físicos `unverified`.

## Qué no demuestra

No demuestra cobertura, autonomía, robustez, regulación, comprensión humana ni rescate.

## Contratos normativos relacionados

[Mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json), [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [energía](../../specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json).
