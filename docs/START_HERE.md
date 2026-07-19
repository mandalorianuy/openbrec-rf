# Start Here

OpenBREC es una Open Spec y una plataforma de referencia para crear comunicaciones, energía y sensores offline durante operaciones BREC/USAR. No promete localizar personas: organiza evidencia, conserva incertidumbre y mantiene funciones críticas localmente cuando una red superior desaparece.

## Elegí tu objetivo

- **Entender el sistema:** leé el [README principal](../README.md) y la [arquitectura documental](DOCUMENTATION_ARCHITECTURE.md).
- **Probar una ruta mínima sin hardware:** seguí el [Quickstart off-grid](guides/quickstart-offgrid.md).
- **Construir o reutilizar componentes:** usá [Construcción y reutilización](guides/building-reuse.md) y elegí un [reference build](reference-builds/README.md).
- **Planificar una operación:** empezá por [Planificación del deployment](guides/deployment-planning.md).
- **Integrar un transporte:** compará [Meshtastic, MeshCore, Reticulum, LoRaWAN y adapters futuros](guides/transports.md).
- **Operar o diagnosticar:** consultá [Validación y troubleshooting](guides/validation-troubleshooting.md).
- **Implementar la norma:** abrí la [Open Spec normativa](open-spec/README.md) y [Conformance](open-spec/CONFORMANCE.md).

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
