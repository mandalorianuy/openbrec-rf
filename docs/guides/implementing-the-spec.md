# Cómo implementar la Open Spec

## Objetivo

Construir un componente, adapter o implementación conforme a la Open Spec `1.0.0-draft.1` — y declarar honestamente su estado de evidencia — sin leer seis documentos dispersos.

## Audiencia

Desarrolladores e integradores que implementan la spec por primera vez: adapters de transporte o sensor, runtimes alternativos, perfiles addon.

## Prerrequisitos

Git, `uv`, Python 3.12 y el checkout con dependencias bloqueadas (`uv sync --frozen`). No se requiere hardware: todo el camino hasta `simulated` corre offline.

## Capacidades necesarias

Comprensión de los contratos JSON Schema aplicables, un entorno que ejecute fixtures y replay, y un punto de integración versionado (adapter, perfil o servicio).

## Alternativas permitidas

Cualquier lenguaje, runtime o bearer mientras se conserven los contratos, las invariantes y la semántica de los envelopes. La reference implementation en Python (`openbrec/`, `apps/`) es una posibilidad, no un requisito.

## Componentes e interfaces

Contratos en [`schemas/`](../../schemas/) (core en `schemas/core/`, addons experimentales en `schemas/addons/`), perfiles normativos en [`specs/openbrec/`](../../specs/openbrec/), fixtures válidos/inválidos en [`fixtures/`](../../fixtures/) con catálogos sha256, y los verificadores `openbrec.verify`. La autoridad es la [Open Spec](../open-spec/README.md); la reference implementation es reemplazable.

## Pasos

1. **Leer los contratos.** Empezar por el schema del dominio (p.ej. `observation.schema.json`, `fusion-result.schema.json`) y el perfil normativo correspondiente en `specs/openbrec/1.0.0-draft.1/`. Los catálogos fijan sha256: verificar antes de confiar.
2. **Correr fixtures y replay.** Ejecutar `uv run --offline python -m openbrec.verify open-spec` y `uv run --offline python -m openbrec.verify core-replay --bundle fixtures/replay/core/m0-six-node.json`. Los fixtures válidos e inválidos definen el comportamiento esperado, incluidos los casos negativos.
3. **Escribir el adapter o componente versionado.** Fijar upstream (versión, firmware, protocolo), declarar interfaces y límites, y mapear cada capacidad a un `capability_id`, nunca a una marca.
4. **Declarar el estado inicial.** Todo adapter nuevo nace `unverified`. Pasa a `specified` con contrato y fixtures propios, y a `simulated` sólo con un escenario reproducible y receipt determinístico. Nunca declarar más de lo ejecutado.
5. **Respetar las reglas duras.** Los plugins publican observaciones y nunca escriben hechos consolidados; la fusión se abstiene ante evidencia insuficiente; todo resultado conserva provenance, timestamp, incertidumbre y fuentes; un SOS con firma inválida se preserva para review, no se descarta; el derivador de claves simulado de `lab-sim` está prohibido fuera de ese perfil.
6. **Pasar conformidad.** Ejecutar el gate del dominio aportado (p.ej. `openbrec.verify open-spec-transports`) y luego `openbrec.verify open-spec-exit`. Registrar comando, SHA y resultado. Ver [Conformance](../open-spec/CONFORMANCE.md).
7. **Elevar evidencia sólo con prueba real.** `bench-validated` y `field-validated` exigen un [evidence pack](../evidence-packs/README.md) de la combinación exacta: versión, configuración, hardware, entorno, protocolo, resultados y límites. CI y simulación no elevan estados físicos.

## Resultado esperado

Un componente que valida contra los contratos, reproduce los fixtures, pasa los gates aplicables y declara un estado de evidencia honesto con sus límites explícitos.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec` y el gate del dominio afectado, más replay si el componente participa del pipeline. Todos con código `0` sobre el SHA declarado.

## Fallos comunes y recuperación

- **Fixture inválido que “casi pasa”:** no editar el fixture para que pase; corregir la implementación o proponer el cambio normativo con vectores de compatibilidad (ver [PUBLISHING](../open-spec/PUBLISHING.md)).
- **Elevar el estado por entusiasmo:** un adapter probado una vez en el banco del autor sigue `unverified` hasta que el evidence pack documente protocolo y límites.
- **Confundir recepción con aceptación:** un ACK del bearer no mueve el lifecycle del mensaje a aceptado; ese paso es humano.
- **Inferir desde ausencia:** un sensor caído se declara `missing`; no se emite un cero ni una inferencia negativa.
- **Reutilizar el derivador de claves de laboratorio:** fuera de `lab-sim` las claves se generan reales por incidente (ver [Identidad y claves offline](identity-key-lifecycle.md)).

## Safety, privacidad y preservación

Minimizar identificadores y payloads, pero nunca descartar silenciosamente posible distress: se preserva con acceso, auditoría, retención y disposición explícitos. Ninguna implementación conformante incluye funciones ofensivas de radio ni TX fuera de los modos regulatorios declarados.

## Estado de evidencia

Este camino completo es `specified` y `simulated` en la reference implementation. Cualquier implementación externa comienza `unverified` hasta producir su propia evidencia.

## Qué no demuestra

Pasar los gates acredita compatibilidad con los contratos y el escenario nombrado. No acredita hardware físico, cobertura RF, autonomía, autorización regulatoria, seguridad eléctrica, detección de personas ni readiness de campo.

## Contratos normativos relacionados

[Open Spec](../open-spec/README.md), [Conformance](../open-spec/CONFORMANCE.md), [`schemas/`](../../schemas/), [`specs/openbrec/`](../../specs/openbrec/) y [arquitectura](../architecture.md).
