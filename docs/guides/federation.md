# Federación y operación autónoma

## Objetivo

Componer nodos, equipos, ResponseCells, áreas y hubs opcionales sin que un nivel dependa para operar del nivel superior.

## Audiencia

Arquitectos de deployment, integradores y operadores de incidentes grandes.

## Prerrequisitos

Identificadores por incidente, ownership por ámbito, políticas de prioridad/conflicto y almacenamiento local en cada nivel.

## Capacidades necesarias

Operación local, replicación eventual, deduplicación, provenance, scopes, health y carry/sync alternativo.

## Alternativas permitidas

Jerarquía completa o subconjuntos: nodo/equipo autónomo, ResponseCell, área y hub. Los hubs mejoran coordinación global, pero no son single point of operational dependency.

## Componentes e interfaces

`Node`, `Team`, `ResponseCell`, `OperationalArea`, `IncidentFederation`, journals append-only y sync envelope. La autoridad sobre un evento permanece trazable a su origen.

## Pasos

1. Asignar nodos a equipos y una ResponseCell que pueda operar aislada.
2. Definir qué datos cruzan cada frontera y su prioridad/retención.
3. Mantener journals locales y cursores de sincronización.
4. Simular corte con área/hub; crear mensajes y observaciones localmente.
5. Reconectar y reconciliar por event ID, origen, secuencia y versión.
6. Resolver conflictos sin borrar evidencia original; registrar la decisión derivada.
7. Ensayar pérdida total de red con carry bundle.

## Resultado esperado

Continuidad local durante particiones y vista federada eventual sin duplicar ni reescribir el origen.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-federation`; escenario de partición/reconexión con SOS, telemetría y conflicto, hash determinístico y cero confirmaciones falsas.

## Fallos comunes y recuperación

Si el hub es requerido para crear/leer eventos locales, rediseñar la dependencia. Si hay colisión de IDs, aislar el journal y reconciliar con namespace de origen. Si el backlog satura, conservar primero distress y estados operativos críticos.

## Safety, privacidad y preservación

Compartir por necesidad operacional y scope; los niveles superiores no reciben datos sensibles por defecto. Una política de privacidad no debe provocar descarte silencioso de distress durante una partición.

## Estado de evidencia

Jerarquía y reconciliación `specified`, escenarios `simulated`; escala y rendimiento físico son `unverified`.

## Qué no demuestra

No demuestra capacidad para miles de nodos, latencia de campo, interoperabilidad entre productos reales ni disponibilidad de un hub.

## Contratos normativos relacionados

[Perfiles de federación recursiva](../../specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json), [mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json) y [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json). Los contratos de máquina del dominio viven como addons en schemas/addons/1.0.0/ ([catálogo](../../schemas/addons/catalog.json)): `federation-event` y `federation-topology-event`.
