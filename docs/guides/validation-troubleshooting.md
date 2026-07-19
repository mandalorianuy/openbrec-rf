# Validación y troubleshooting

## Objetivo

Validar por capas y diagnosticar fallos sin elevar claims más allá de la evidencia.

## Audiencia

Constructores, integradores, operadores, revisores y contribuidores.

## Prerrequisitos

SHA/configuración exactos, logs/fixtures sin secretos, criterio de aceptación, estado inicial y rollback.

## Capacidades necesarias

Validadores offline, replay determinístico, health, timestamps, provenance y separación entre evidencia sintética, banco y campo.

## Alternativas permitidas

Checks estructurales, schema/fixtures, simulación, banco conducted/sin radiación o campo autorizado. Cada nivel es opcional para publicar la spec y sólo sustenta su propio claim.

## Componentes e interfaces

`openbrec.verify`, fixtures, receipts, logs mínimos, evidence pack y matriz de resultados/limitaciones.

## Pasos

1. Ejecutar `uv run --offline python scripts/validate_docs.py`.
2. Ejecutar `uv run --offline python scripts/validate_bundle.py`.
3. Ejecutar `uv run --offline python -m openbrec.verify open-spec-exit`.
4. Probar schemas, fixtures, replay y determinismo relevantes.
5. Inyectar sensor ausente, duplicado, reordenamiento, partición, brownout simulado y congestión.
6. Clasificar el resultado con el vocabulario público y registrar qué no demuestra.
7. Si se ensaya hardware, separar protocolo/evidencia de la norma y no generalizar.

## Resultado esperado

Resultados reproducibles, fallos accionables y claims ligados a evidencia exacta.

## Validación mínima

Los comandos aplicables terminan `0`, enlaces internos existen, ejemplos parsean y el replay conserva hash entre corridas.

## Fallos comunes y recuperación

`validate_bundle.py` sólo valida estructura: no presentarlo como runtime. Un replay divergente exige fijar orden/canonicalización. Un link roto se corrige en la fuente, no se ignora. Una prueba física incompleta queda `unverified`.

## Safety, privacidad y preservación

Sanitizar secretos e identificadores, conservar evidence crítico y separar datasets públicos de cuarentena. Los tests nunca deben generar inferencias negativas sobre personas.

## Estado de evidencia

Los gates contractuales y replay son `simulated`; la ruta física opcional no está ejecutada y permanece `unverified`.

## Qué no demuestra

Un CI verde no demuestra hardware, cobertura, seguridad operacional, cumplimiento regulatorio, evaluación humana ni readiness de campo.

## Contratos normativos relacionados

[Conformance](../open-spec/CONFORMANCE.md), [publicación](../open-spec/PUBLISHING.md), [evidence packs](../evidence-packs/README.md) y [field profiles](../field-profiles/README.md).
