# OpenBREC — propuesta de colaboración en una página

**Para:** direcciones de laboratorio, cátedras, escuelas de bomberos/defensa civil, clubes de radioaficionados.
**De qué se trata:** validación física de una especificación abierta de comunicaciones y evidencia para búsqueda y rescate.

## El proyecto

OpenBREC es una **Open Spec offline-first** para operaciones BREC/USAR (búsqueda y rescate en estructuras colapsadas): comunicaciones mesh, energía, sensores y evidencia con provenance que operan sin nube, sin red eléctrica y sin backhaul. La spec está completa y verificada en simulación (8/8 gates, todo ejecutable offline), pero **no tiene validación física**: ese es, exactamente, el aporte que buscamos. Disclaimer permanente: OpenBREC transporta indicios; no detecta personas y el silencio de sensores nunca demuestra ausencia de víctimas.

## Qué pedimos

**Un laboratorio puntual** del programa de validación: ocho labs acotados, con protocolo ya definido y criterios objetivos de aceptación. Ejemplos:

- **L1 (cero compra):** demo de integración ATAK/TAK con una laptop y una máquina vieja — observaciones del sistema visibles en ATAK sin servidor ni internet.
- **L3:** detección de presencia por Wi-Fi CSI con dos ESP32 (~USD 20 total) y protocolo de 5 etapas ya escrito.
- **L7 (original):** primera medición publicada de aislamiento RF en contexto SAR — no existe literatura; quien la hace produce la referencia.

Lista completa con equipamiento, costos estimados y duración: [institutional-collaboration.md](institutional-collaboration.md).

## Qué ofrecemos

- Un problema real con norma abierta versionada, contratos, fixtures y gates ejecutables: ideal para proyectos de grado con criterios objetivos.
- **Coautoría de evidence packs citables** y evidencia reproducible (SHA, configuración, hardware, entorno, protocolo).
- Participación en la gobernanza de la spec (RFC + proceso de evidencia comunitaria).
- Los **resultados negativos también cuentan** y se conservan: un lab que demuestra que algo no funciona es un aporte publicable.

## La regla del juego

La institución mide; el proyecto **nunca** eleva un claim sin el evidence pack de la combinación exacta. Todo queda registrado con revisión de seguridad, privacidad y safety.

## Links

- Programa completo: [institutional-collaboration.md](institutional-collaboration.md)
- Punto de entrada: [README](../../README.md) y [Start Here](../START_HERE.md)
- Posicionamiento (qué usa el mundo SAR hoy y dónde encaja esto): [sar-landscape.md](../research/sar-landscape.md)
- Contacto: repositorio GitHub `mandalorianuy/openbrec-rf` (issues) · seguridad: [SECURITY.md](../../SECURITY.md)
