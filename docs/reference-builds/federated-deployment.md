# Deployment federado

## Objetivo

Componer múltiples equipos y ResponseCells en áreas/hubs opcionales, con operación aislada y sincronización eventual.

## Audiencia

Coordinadores de incidentes grandes, arquitectos e integradores multi-equipo.

## Prerrequisitos

ResponseCells autónomas, ownership y namespaces, estrategia multi-bearer, scopes de datos y plan de partición/reconciliación.

## Capacidades necesarias

Journals locales, federación recursiva, gateways outbound, prioridad global/local, deduplicación, provenance y carry fallback.

## Alternativas permitidas

Áreas y hub pueden omitirse. Backhaul puede ser RF, Wi-Fi, Ethernet, Reticulum, enlace privado o carry. Cada componente y nivel es reemplazable y no condiciona al inferior.

## Componentes e interfaces

N ResponseCells → OperationalArea opcional → IncidentFederation/Hub opcional; sync envelopes firmados, cursores, resúmenes mínimos y políticas de conflicto.

## Pasos

1. Dimensionar celdas por autonomía operativa, no sólo cobertura.
2. Asignar scopes, prioridades, claves y límites de exportación.
3. Seleccionar backhaul/fallback por área.
4. Simular múltiples particiones y producción concurrente de eventos.
5. Reconciliar sin overwrite, LWW ciego ni pérdida de origen.
6. Priorizar SOS/estado crítico durante backlog.
7. Versionar el deployment manifest y plan de recuperación.

## Resultado esperado

Cada nivel sigue operando aislado y la coordinación global reaparece de forma eventual y auditable.

## Validación mínima

Gates de federación/transporte/mensajería en `0`; simulación de varias celdas, hub caído/hostil y carry; hash determinístico y cero pérdida silenciosa.

## Fallos comunes y recuperación

Una dependencia central oculta se elimina o replica. Backlog excesivo se resume sin borrar distress/provenance. Conflictos se conservan como eventos y requieren resolución explícita.

## Safety, privacidad y preservación

La agregación aumenta riesgo de reidentificación; compartir sólo el scope necesario. La minimización no puede descartar silenciosamente evidencia crítica.

## Estado de evidencia

Arquitectura `specified` y reconciliación `simulated`; escala, RF, seguridad operacional y campo `unverified`.

## Qué no demuestra

No demuestra operación en miles de edificios/nodos, capacidad de hub, latencia, regulación ni coordinación humana real.

## Contratos normativos relacionados

[Federación recursiva](../../specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json), [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [conformance](../open-spec/CONFORMANCE.md).
