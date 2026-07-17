# Runtime `lab-sim` M0

## Frontera

`lab-sim` es un entorno contenido de validación, no un deployment de campo. Ejecuta API, worker, PWA, Mosquitto y PostgreSQL sobre una única red Docker con `internal: true`. MQTT y PostgreSQL no publican puertos; sólo la PWA publica `127.0.0.1:${OPENBREC_WEB_PORT:-8080}` para un navegador local. Los servicios no tienen ruta de salida a Internet durante startup ni smoke.

La contraseña PostgreSQL y una master key AES-256 se generan por corrida dentro de `openbrec.verify`, se escriben en un directorio temporal host `0700` y se montan read-only (`0444`) mediante Docker Compose secrets para que el worker no-root pueda leerlas. El directorio se elimina al terminar el gate. No existe credencial ni key default versionada.

## Gates

```bash
uv run --offline python -m openbrec.verify compose-build
uv run --offline python -m openbrec.verify offline-startup
uv run --offline python -m openbrec.verify postgres-disposition
```

`compose-build` pertenece al provisioning: valida Compose, descarga imágenes fijadas por digest y construye API/PWA. `offline-startup` sólo usa imágenes locales mediante `--no-build --pull never`, espera healthchecks, ejecuta el smoke y elimina contenedores/volúmenes. `postgres-disposition` prueba por separado migración, cuatro destinos, rollback, restart, concurrencia y reconciliación.

El smoke demuestra:

- una `Observation` válida se convierte en `DomainEvent`, recorre API → MQTT → worker y recibe acuse sólo después del commit PostgreSQL;
- una observación inválida devuelve HTTP 422 y no entra al topic aceptado;
- el accepted log contiene una unidad, ingress y destinos reconcilian con `unreconciled: 0`;
- el shell, manifest y service worker de la PWA están disponibles;
- una conexión directa externa falla desde la red de prueba;
- el cierre elimina el volumen PostgreSQL usado por el gate.

## Límites gobernados

- MQTT anónimo está permitido sólo dentro de esta red interna y sin listeners publicados.
- SQLite conserva la referencia portable; M0-06 implementa la misma disposición de cuatro destinos en PostgreSQL y conecta el worker. El acuse `durably_processed` sólo aparece después del commit, pero sigue siendo una notificación efímera: el accepted log/audit es la autoridad y el acuse no es evidencia ni hecho.
- La custodia `lab_secret_file_replaceable` demuestra key IDs, epoch monotónico, rotación, recuperación, revocación, zeroization best-effort y rechazo de rollback. No acredita HSM, secure element ni perfil de campo; el SOP está en `docs/runtime/m0-lab-key-lifecycle-sop.md`.
- M0-05 resuelve la exposición local de la PWA para laboratorio: `ui-smoke` construye y conduce Chromium, comprueba la proyección explicable y recarga desde el service worker después de cortar la red. No acredita un terminal ni deployment de campo.
- Los digests, SBOM, licencias, secret scan y vulnerabilidades se verifican en gates separados de M0-06.

Estos límites están registrados con owner y stop condition en `docs/governance/M0_RESIDUAL_REGISTER.md`.
