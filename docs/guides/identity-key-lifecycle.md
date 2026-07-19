# Identidad y ciclo de vida de claves offline

## Objetivo

Declarar cómo se enrolan identidades, se vinculan actores con dispositivos y se rotan, revocan y custodian claves sin ninguna dependencia cloud.

## Audiencia

Responsables técnicos de seguridad, operadores de comunicaciones y mantenedores de runtime.

## Prerrequisitos

Inventario de actores y dispositivos, handling policy aceptada y un procedimiento de enrollment presencial.

## Capacidades necesarias

`IdentityKeyLifecycleProfile`, firma `Ed25519`, cifrado `AES-256-GCM` y un journal append-only para enrollment, rotación y revocación.

## Alternativas permitidas

Enrollment por ingreso manual offline, intercambio QR offline o transferencia por medio físico. Custodia en keystore de hardware, archivo cifrado o respaldo en papel. Revocación por lista offline o reemplazo de compromiso de clave, distribuida por gossip dentro de la celda, carry bundle o intercambio directo.

## Componentes e interfaces

El perfil materializa `actor_device_binding`: un vínculo `actor_id` ↔ `device_id` con `bound_at` y prueba `ed25519_device_attestation`. La rotación es siempre `per_incident`; los disparadores declarados son inicio/cierre de incidente, sospecha de compromiso o decisión del operador.

## Pasos

1. Enrolar actor y dispositivo presencialmente y registrar el `actor_device_binding`.
2. Generar claves reales por incidente; nunca derivarlas de etiquetas.
3. Declarar disparadores de rotación y mecanismo de revocación offline.
4. Ante compromiso, revocar y re-enrolar o congelar la identidad pendiente de review.
5. Cerrar el incidente rotando y archivando el material según la handling policy.

## Resultado esperado

Identidades verificables offline, con rotación por incidente y revocación que converge sin conectividad.

## Validación mínima

`uv run --offline python -m openbrec.verify addon-fixtures`; el fixture inválido demuestra que `allowed_profiles` distinto de `["lab-sim"]` es rechazado.

## Fallos comunes y recuperación

Clave comprometida: revocar por el mecanismo declarado y re-enrolar; no reutilizar `key_id`. Lista de revocación divergente entre celdas: reconciliar al reconectar preservando la versión más restrictiva.

## Safety, privacidad y preservación

**Red line:** el derivador simulado `openbrec-p0-simulated-only` (material público y reproducible) está prohibido fuera del perfil `lab-sim`; `prohibited_outside_allowed_profiles: true` es invariante del contrato. Todo uso fuera de laboratorio invalida la confidencialidad y autenticidad del sistema.

## Estado de evidencia

El perfil está `specified`; la ceremonia de claves no tiene validación de campo.

## Qué no demuestra

No demuestra resistencia ante compromiso físico de dispositivos ni una PKI operativa; sólo declara el procedimiento y sus invariantes.

## Contratos normativos relacionados

[IdentityKeyLifecycleProfile](../../schemas/addons/1.0.0/identity-key-lifecycle-profile.schema.json), [catálogo de addons](../../schemas/addons/catalog.json) y [HumanMessage](../../schemas/addons/1.0.0/human-message.schema.json).
