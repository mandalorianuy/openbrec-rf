# Receta: telemetría máquina local

## Objetivo
Transportar estados de componentes dentro de una ResponseCell con backhaul opcional.
## Audiencia
Integradores de sensores, gateways y redes.
## Prerrequisitos
Endpoints, identidad/secuencia, cuotas, claves y bearer elegido.
## Capacidades necesarias
Cola local, collector append-only, health, deduplicación y fallback.
## Alternativas permitidas
LoRaWAN privado, enlaces locales, gateways existentes, Reticulum o carry; componentes reemplazables.
## Componentes e interfaces
`endpoint → bearer local → collector → backhaul opcional`; el overlay conserva identidad y semántica.
## Pasos
Asignar identidades; integrar adapter; limitar telemetría; probar store-and-forward; separar de mensajes humanos; definir kill switch.
## Resultado esperado
Telemetría local que degrada sin consumir la reserva de SOS ni depender de una mega-mesh.
## Validación mínima
Replay, contador regresivo, pérdida de enlace, congestión y partición sintética.
## Fallos comunes y recuperación
Ante counter rollback aislar endpoint; ante congestión bajar duty cycle; ante pérdida de collector conservar cola.
## Safety, privacidad y preservación
Claves default o interferencia perjudicial detienen TX; minimizar metadatos sin borrar health crítico.
## Estado de evidencia
Receta `specified`; transporte sintético `simulated`; RF `unverified`.
## Qué no demuestra
No demuestra entrega, capacidad, coexistencia ni autorización regulatoria.
## Contratos normativos relacionados
[Transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [guía](../guides/transports.md).
