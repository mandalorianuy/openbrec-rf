# GIS offline: tiles, tracks y áreas de búsqueda

## Objetivo

Operar mapas completamente offline: paquetes de tiles versionados, CRS declarado, capas operativas, tracks de equipos con privacidad y áreas de búsqueda con POD anotado por operador.

## Audiencia

Planificadores BREC/USAR, operadores de consola y responsables de privacidad.

## Prerrequisitos

Paquetes de tiles descargados antes del despliegue, CRS acordado por incidente y handling policy para tracks.

## Capacidades necesarias

`OfflineMappingProfile`, almacenamiento local de tiles y `OperatorAnnotation` como base del POD.

## Alternativas permitidas

Formatos `mbtiles`, `pmtiles` o `geopackage`; capas base, de áreas de búsqueda, de hazard, de tracks de equipos y de anotaciones de operador. Todo CRS se declara por EPSG.

## Componentes e interfaces

Cada `tile_package` declara versión semántica, extent y `sha256`, e importa offline. Los tracks de equipos usan seudónimo `incident_rotating_hash`, retención acotada (`retention_hours` ≤ 168) y no conservan historia precisa (`precise_history_kept: false`).

## Pasos

1. Importar paquetes de tiles verificando `sha256` y declarando el CRS.
2. Crear capas de áreas de búsqueda por dibujo de operador o importación offline.
3. Registrar el POD de cada área sólo como anotación de operador (`pod.automatic: false`, vinculado a un `annotation_id`).
4. Habilitar tracks con seudónimo rotativo y retención limitada, o dejarlos deshabilitados.
5. Actualizar el POD sólo mediante nuevas anotaciones humanas.

## Resultado esperado

Mapas utilizables sin conectividad, con procedencia de tiles verificable y POD auditable como juicio humano.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; el fixture inválido demuestra que `pod.automatic: true` es rechazado.

## Fallos comunes y recuperación

Tiles corruptos: rechazar el paquete por `sha256` y reimportar. CRS inconsistente entre capas: detener la superposición y declarar el conflicto; nunca reproyectar silenciosamente.

## Safety, privacidad y preservación

Los tracks revelan patrones de movimiento de los rescatistas: retención limitada, seudónimo por incidente y acceso por rol. El POD guía la búsqueda pero nunca cierra un sector por sí solo.

## Estado de evidencia

El perfil está `specified`; no hay validación de campo de cobertura de tiles ni de estimaciones de POD.

## Qué no demuestra

Un área con POD alto no demuestra presencia, y un área barrida no demuestra ausencia. Ver [Planificación del deployment](deployment-planning.md) para el flujo operativo completo.

## Contratos normativos relacionados

[OfflineMappingProfile](../../schemas/addons/1.0.0/offline-mapping-profile.schema.json), [catálogo de addons](../../schemas/addons/catalog.json) y [OperatorAnnotation](../../schemas/core/1.0.0/operator-annotation.schema.json).
