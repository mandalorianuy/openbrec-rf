# OpenBREC reference builds y reutilización

Estos documentos son planos funcionales abiertos, no recetas ligadas a un
producto. El punto de partida siempre es un **inventario de capacidades**,
interfaces, límites, energía, regulación y evidencia disponible. Después se
elige la composición mínima: construir, reutilizar componentes existentes o
combinar ambas rutas.

Un build `specified` demuestra que el manifiesto es completo y verificable. No acredita
desempeño físico, certificación, seguridad eléctrica, coexistencia RF
ni readiness de campo. Cada implementación debe registrar versiones exactas,
capacidades ausentes, sustituciones, stop conditions y evidencia propia.

## Flujo común

1. Inventariar capacidades y restricciones disponibles.
2. Seleccionar el perfil mínimo que satisface la misión.
3. Mapear cada componente existente mediante un adapter versionado.
4. Completar roles faltantes con componentes sustituibles.
5. Inspeccionar límites eléctricos, mecánicos, RF, privacidad y claves.
6. Ejecutar verificaciones offline y pruebas negativas.
7. Registrar evidencia, limitaciones y procedimiento de rollback.

## Guías

- [Energía de sitio](energy-site.md)
- [Telemetría máquina](machine-telemetry.md)
- [Mensajería humana](human-messaging.md)
- [Beacon por capacidades](beacon-node.md)
- [Gateway autónomo de ResponseCell](response-cell-gateway.md)

La reutilización nunca eleva automáticamente un adapter a `supported`; requiere
evidencia de la combinación exacta y revisión de los claims propuestos.
