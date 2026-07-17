# SOP de claves M0 para `lab-sim`

## Alcance y autoridad

Este procedimiento gobierna únicamente el perfil sustituible `lab_secret_file_replaceable`. Demuestra el contrato de ciclo de vida necesario para M0, no custodia de campo. No autoriza HSM, secure element, backup operacional ni reutilización de una key entre incidentes.

La vida y la preservación de posible evidencia life-safety tienen prioridad sobre minimización, pero nunca permiten usar una key ausente, revocada, stale o proveniente de rollback. Ese material se conserva sólo si el boundary criptográfico puede sellarlo; de otro modo el servicio falla cerrado y la unidad upstream debe permanecer sin ACK para reintento/revisión.

## Commissioning

1. Generar 32 bytes con CSPRNG fuera del repositorio y codificarlos en Base64 estricto.
2. Crear un `key_id` opaco por incidente y un `epoch` monotónico persistido por el custodio externo.
3. Entregar la key por archivo `0600` mediante el mecanismo de secrets. Nunca usar argumento CLI, log, variable versionada o valor default.
4. Arrancar y ejecutar `key-lifecycle`, `postgres-disposition` y `offline-startup`.
5. Confirmar que las tablas cifradas registran `key_id`, nonce único por incidente/key y AAD canónico.

## Rotación

1. Generar una key nueva y un `key_id` nunca reutilizado.
2. Incrementar `epoch`; un valor igual o menor es rollback y debe rechazarse.
3. Marcar la key anterior `retired`, no revocada, mientras existan objetos que necesiten lectura/revisión.
4. Activar la nueva key antes de aceptar nuevas escrituras y verificar una escritura/lectura sintética.
5. Registrar actor, razón, epoch anterior/nuevo y hash del receipt; no registrar material de key.

## Recuperación y rollback

1. El recovery envelope usa AES-256-GCM y AAD `openbrec-lab-key-recovery-v1`; su wrapping key pertenece a un custodio externo y separado.
2. Verificar autenticidad y exigir `minimum_epoch` contra la autoridad monotónica externa.
3. Rechazar envelope truncado, alterado, con key inválida o epoch inferior. No degradar a una key default.
4. Tras recuperar, ejecutar el vector sintético antes de reanudar ingest.

## Pérdida, revocación y zeroization

1. Ante pérdida o exposición, revocar el `key_id`, detener nuevas escrituras con esa key y rotar con epoch superior.
2. Una key revocada no puede cifrar ni descifrar. Los objetos inaccesibles permanecen registrados para revisión; no se borran silenciosamente.
3. Zeroization sobre `bytearray` es best-effort en Python y elimina la entrada del registry. No demuestra borrado de copias del runtime, swap o hardware.
4. Borrar el archivo secret y el recovery material sólo después de revisar retención, hold y obligaciones life-safety. Emitir receipt de la decisión.

## Brownout y reinicio

- El runtime no acepta un epoch inferior al mínimo externo.
- PostgreSQL conserva `key_id` por objeto; el reinicio no cambia destino ni reconciliación.
- Si desaparece la key activa, el worker no emite ACK. La unidad permanece en el bus/upstream para reintento o manejo gobernado.
- Ejecutar fault injection de rollback, key stale, key revocada, secret ausente, transacción duplicada y restart antes de cada release del perfil.

## Stop conditions

- key embebida, default, compartida entre incidentes o expuesta en logs;
- nonce reutilizado para el mismo incidente/key;
- ACK antes del commit durable;
- recovery sin minimum epoch externo;
- claim de zeroization fuerte, HSM o soporte de campo sin evidencia específica.

Ante cualquiera de estas condiciones, `lab-sim` falla cerrado y todo perfil de campo permanece `unverified`.
