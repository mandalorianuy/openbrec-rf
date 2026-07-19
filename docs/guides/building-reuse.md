# Construcción y reutilización de componentes

## Objetivo

Construir una solución por capacidades, reutilizando hardware existente o sustituyendo componentes sin alterar la norma.

## Audiencia

Makers, integradores, equipos técnicos y mantenedores de adapters.

## Prerrequisitos

Misión, inventario de hardware, interfaces eléctricas/lógicas, licencias, firmware, regulación y límites de seguridad.

## Capacidades necesarias

Como mínimo: cómputo/terminal, energía local, persistencia y un transporte. Mensajería, ubicación, gateway y beacons se añaden según el build.

## Alternativas permitidas

Construcción nueva, reutilización integral o híbrida. ESP32, SBC, teléfonos, radios LoRa u otros productos pueden ser ejemplos; todos son reemplazables por interfaces equivalentes.

## Componentes e interfaces

BOM por `capability_id`, energía DC, enlace local, adapter de transporte/sensor, manifest de versión, health y procedimiento de rollback.

## Pasos

1. Elegir [kit personal/equipo](../reference-builds/personal-team-kit.md), [ResponseCell](../reference-builds/response-cell.md) o [deployment federado](../reference-builds/federated-deployment.md).
2. Inventariar cada componente y mapearlo a una capacidad, no a un claim.
3. Verificar tensión, corriente, conectores, firmware, bandas y licencias.
4. Declarar interfaces y adapters; marcar gaps `unverified` o `unsupported`.
5. Sustituir componentes faltantes con alternativas documentadas.
6. Validar contratos y replay antes de conectar RF o sensores físicos.
7. Para pruebas físicas, crear un manifest exacto y evidence pack separado.

## Resultado esperado

BOM sustituible, diagrama de interfaces, configuración versionada, criterios de aceptación y rollback.

## Validación mínima

`uv run --offline python -m openbrec.verify open-spec-builds`; cada rol tiene capacidad, alternativa, interface y estado; ningún SKU aparece como requisito normativo.

## Fallos comunes y recuperación

Si una API propietaria no puede adaptarse, aislarla o elegir otra alternativa. Si la sustitución cambia potencia, RF o seguridad, invalidar sólo los claims afectados y repetir sus pruebas.

## Safety, privacidad y preservación

No energizar conexiones no verificadas ni usar TX no gobernado. Validar regulación/configuración o aplicar únicamente la excepción vital acotada `emergency_assumed_risk` definida por la Open Spec; borrar credenciales por defecto y preservar evidencia crítica con acceso y retención explícitos.

## Estado de evidencia

Los BOMs por capacidades están `specified`; la referencia software posee validación sintética. Cada composición física comienza `unverified`.

## Qué no demuestra

Compatibilidad nominal o schema válido no demuestra seguridad eléctrica, rendimiento, rango, autonomía, certificación ni field readiness.

## Contratos normativos relacionados

[Reference build profiles](../../specs/openbrec/1.0.0-draft.1/reference-build-profiles.json), [capacidades](../../specs/openbrec/1.0.0-draft.1/reference-capability-profiles.json) y [conformance](../open-spec/CONFORMANCE.md).
