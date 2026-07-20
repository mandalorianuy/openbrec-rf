# Start Here

OpenBREC es una Open Spec y una plataforma de referencia para crear comunicaciones, energía y sensores offline durante operaciones BREC/USAR. No promete localizar personas: organiza evidencia, conserva incertidumbre y mantiene funciones críticas localmente cuando una red superior desaparece.

Estado actual en una línea: Open Spec `1.0.0-draft.1` completa (8 / 8), todo `specified` o `simulated`, cero validación física. Elegí tu rol y seguí el camino de lectura en orden.

## Equipo de rescate / operador

1. El concepto y sus límites: [README principal](../README.md) y [Arquitectura](architecture.md).
2. Cómo encaja en un operativo real: [Integración con doctrina USAR](guides/usar-doctrine-integration.md) (ICS-205, INSARAG, ciclo operacional).
3. La base regulatoria antes de transmitir: [Marco regulatorio de RF](guides/regulatory.md).
4. Las rutas de solución: [Kit mínimo personal/equipo](reference-builds/personal-team-kit.md), [ResponseCell](reference-builds/response-cell.md) y [Deployment federado](reference-builds/federated-deployment.md).
5. Si la víctima no puede actuar (inconsciente, atrapada): la excepción gobernada del [AP de emergencia con auto-join](guides/emergency-autojoin.md) — sólo bajo `emergency_assumed_risk`, eficacia `unverified`.
6. [Qué no demuestra](#antes-de-usar-en-una-operación-real): ninguna ejecución sintética demuestra readiness operativa.

## Desarrollador que implementa la spec

1. La vista unificada: [Arquitectura](architecture.md).
2. La norma: [Open Spec](open-spec/README.md) y [Conformance](open-spec/CONFORMANCE.md).
3. El camino completo del implementador: [Cómo implementar la spec](guides/implementing-the-spec.md) (contratos, fixtures, adapters, conformidad, estados de evidencia).
4. Los contratos y fixtures de máquina: [`schemas/`](../schemas/), [`specs/openbrec/`](../specs/openbrec/) y [`fixtures/`](../fixtures/).
5. La referencia ejecutable: [`openbrec/`](../openbrec/) y [`apps/`](../apps/).

## Integrador de hardware / transportes

1. Construir por capacidades, no por marcas: [Construcción y reutilización](guides/building-reuse.md).
2. Elegir el bearer: [Transportes](guides/transports.md) (Meshtastic, MeshCore, Reticulum, LoRaWAN, carry bundle).
3. Dimensionar la energía: [Energía](guides/energy.md).
4. Componer una ruta: [reference builds](reference-builds/README.md).
5. Sensing RF experimental (addons reintegrados por ADR-004): [CSI](guides/csi-sensing.md), [RF pasiva](guides/passive-rf.md), [SDR receive-only](guides/sdr-beacons.md), [drones](guides/drone-geometry.md), [RF quieting](guides/rf-quieting.md) y [offline finding](guides/offline-finding.md) — todo `specified`/`simulated`, salvo excepciones declaradas en cada guía; los estados exactos por tecnología están en la [investigación SOTA](research/rf-sensing-state-of-the-art.md).
6. Si ejecutás una prueba física: [evidence packs](evidence-packs/README.md) — todo adapter nuevo nace `unverified` y sólo un pack exacto lo eleva.

## Evaluador / investigador

1. El estado honesto: [README principal](../README.md).
2. Cómo está armado: [Arquitectura](architecture.md).
3. Los estados de evidencia y su autoridad: [arquitectura documental](DOCUMENTATION_ARCHITECTURE.md) y [Conformance](open-spec/CONFORMANCE.md).
4. Riesgos y límites: [threat model](security/OpenBREC-RF-threat-model.md) y reviews en [`docs/security/`](security/).
5. Historia y rumbo: [ROADMAP.md](../ROADMAP.md) (vigente) y [DELIVERY_BOARD.md](../DELIVERY_BOARD.md) (audit trail).

## Selección rápida de perfil

1. Definí la misión: personas comunicándose, telemetría de máquinas, beacons o una combinación.
2. Elegí la escala: kit personal/equipo, ResponseCell o deployment federado.
3. Inventariá energía, interfaces y hardware disponible.
4. Elegí el transporte por topología, densidad, movilidad, regulación y complejidad; no hay ganador universal.
5. Asigná un estado real a cada capacidad: `specified`, `simulated`, `bench-validated`, `field-validated`, `unsupported` o `unverified`.
6. Ejecutá la validación mínima del build y conservá los límites del resultado.

## Tres rutas iniciales

- [Kit mínimo personal/equipo](reference-builds/personal-team-kit.md): texto breve, estado, SOS y ubicación sin dependencia superior.
- [ResponseCell](reference-builds/response-cell.md): varios operadores, gateway local, persistencia, replay y beacons opcionales.
- [Deployment federado](reference-builds/federated-deployment.md): múltiples equipos y celdas con sincronización eventual.

## Antes de usar en una operación real

Una ejecución sintética no demuestra cobertura, autonomía, sensibilidad, seguridad eléctrica, cumplimiento regulatorio ni readiness de campo. Para elevar un claim, producí un [evidence pack](evidence-packs/README.md) de la combinación exacta. La ausencia de radio, movimiento, calor o detección nunca demuestra ausencia de personas.

¿Dudas puntuales? [FAQ](faq.md) · [Glosario](glossary.md)
