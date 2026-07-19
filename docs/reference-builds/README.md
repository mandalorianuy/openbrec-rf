# Reference builds abiertos

Los builds son composiciones reproducibles de capacidades, no productos. Todos los componentes y ejemplos comerciales son reemplazables si conservan interfaces, límites y criterios de aceptación. Un build documentado no necesita hardware para existir; comienza `specified` o `simulated` y sólo un [evidence pack](../evidence-packs/README.md) exacto puede elevar un claim físico.

## Rutas de solución

1. [Kit mínimo personal/equipo](personal-team-kit.md): texto, estado, SOS y ubicación con energía local.
2. [ResponseCell](response-cell.md): varios operadores, nodos, gateway local, persistencia y beacons opcionales.
3. [Deployment federado](federated-deployment.md): múltiples equipos/celdas con áreas y hubs opcionales.

## Recetas de capacidad reutilizables

- [Energía de sitio](energy-site.md)
- [Telemetría máquina](machine-telemetry.md)
- [Mensajería humana](human-messaging.md)
- [Beacon por capacidades](beacon-node.md)
- [Gateway autónomo de ResponseCell](response-cell-gateway.md)

## Flujo común

Crear un **inventario de capacidades**; elegir el build mínimo; mapear hardware mediante adapters versionados; cubrir gaps con sustitutos; inspeccionar límites; ejecutar validación offline y fallos; registrar evidencia, límites y rollback. Reutilizar un componente nunca eleva por sí solo su estado y un build documentado no acredita desempeño físico.
