# Selección e integración de transportes

## Objetivo

Elegir e integrar bearers por entorno, topología y misión, sin declarar un ganador universal.

## Audiencia

Arquitectos de red, integradores y operadores técnicos.

## Prerrequisitos

Topología, movilidad, densidad, volumen/prioridad de tráfico, bandas posibles, energía, threat model y regulación local por validar.

## Capacidades necesarias

Adapter versionado, overlay OpenBREC autenticado, deduplicación, prioridad, health y operación desconectada.

## Alternativas permitidas

| Perfil | Favorece | Límite principal |
|---|---|---|
| Meshtastic | Grupos móviles y despliegue ad hoc | Flooding y saturación con alta densidad. |
| MeshCore | Repetidores planificados y redes urbanas | Requiere infraestructura y diseño previo. |
| Reticulum/RNode | Routing multi-bearer y E2E avanzado | Complejidad y overhead mayores. |
| LoRaWAN privado | Telemetría estructurada star-of-stars | Dependencia de gateway/servidor local y downlink acotado. |
| Carry bundle | Particiones largas o ausencia de RF | Latencia humana/logística. |

Wi-Fi, Ethernet, packet radio u otros pueden añadirse mediante el mismo contrato.

## Componentes e interfaces

`TransportEnvelope`, identidad por incidente, MAC/firma de aplicación, sequence/boot ID, TTL, prioridad y adapter. El bearer se trata como no confiable para autenticidad.

## Pasos

1. Modelar nodos, movilidad, hops, payloads y airtime.
2. Seleccionar uno o más perfiles y un fallback.
3. Separar planos humano/máquina por prioridad, claves, colas y presupuesto.
4. Configurar identidades/keys por incidente; prohibir credenciales por defecto.
5. Ensayar congestión, partición, duplicados, mensajes tardíos y pérdida de gateway.
6. Documentar banda/configuración y seleccionar un modo regulatorio. Preferir `jurisdiction_validated`; si una emergencia vital exige operar bajo incertidumbre, `emergency_assumed_risk` requiere doble autorización, RF/geografía exactas, monitoreo, expiración, stop condition y kill switch, y no constituye autorización legal.
7. Implementar un adapter nuevo sin alterar la semántica del mensaje.

## Resultado esperado

Una decisión trazable, adapters reemplazables y degradación explícita cuando un bearer falla.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-transports`; replay de envelopes duplicados/reordenados y prueba sintética de partición.

## Fallos comunes y recuperación

Ante congestión, preservar SOS, reducir telemetría y aplicar backoff; considerar celdas/canales/bearers separados. Ante pérdida de gateway, continuar localmente y reconciliar luego.

## Safety, privacidad y preservación

No confiar en Node IDs ni PSK compartida como identidad humana. Rotar/revocar claves, minimizar metadatos y preservar mensajes críticos no verificables para review.

## Estado de evidencia

Los cinco perfiles están `specified`; escenarios contractuales son `simulated`. Rendimiento de cualquier radio/topología es `unverified` sin evidence pack.

## Qué no demuestra

No demuestra rango, capacidad, coexistencia, seguridad del firmware, autorización regulatoria ni comunicaciones garantizadas.

## Contratos normativos relacionados

[Perfiles multi-bearer y registro de extensiones](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json).
