# Runtime `lab-sim` M0

## Frontera

`lab-sim` es un entorno contenido de validación, no un deployment de campo. Ejecuta API, worker, PWA, Mosquitto y PostgreSQL sobre una única red Docker con `internal: true`. MQTT y PostgreSQL no publican puertos; los servicios no tienen ruta de salida a Internet durante startup ni smoke.

La contraseña PostgreSQL se genera por corrida dentro de `openbrec.verify` y se entrega mediante Docker Compose secrets. No existe credencial default versionada.

## Gates

```bash
uv run --offline python -m openbrec.verify compose-build
uv run --offline python -m openbrec.verify offline-startup
```

`compose-build` pertenece al provisioning: valida Compose, descarga las imágenes de infraestructura necesarias y construye API/PWA. `offline-startup` sólo usa imágenes locales mediante `--no-build --pull never`, espera healthchecks, ejecuta el smoke y elimina contenedores/volúmenes.

El smoke demuestra:

- una `Observation` válida recorre API → MQTT → worker;
- una observación inválida devuelve HTTP 422 y no entra al topic aceptado;
- el shell, manifest y service worker de la PWA están disponibles;
- una conexión directa externa falla desde la red de prueba;
- el cierre elimina el volumen PostgreSQL usado por el gate.

## Límites gobernados

- MQTT anónimo está permitido sólo dentro de esta red interna y sin listeners publicados.
- M0-04 prueba la semántica durable y reconciliada en un storage SQLite portable de laboratorio; el worker de `lab-sim` todavía no escribe PostgreSQL. Esa integración, sus migraciones específicas y pruebas de concurrencia/rollback pertenecen al residual M0-R017 y bloquean el M0 exit.
- El acuse `processed` es efímero y sólo sirve al smoke; no es evidencia ni hecho.
- La exposición local de la PWA y su prueba browser offline pertenecen a M0-05.
- Los digests, SBOM y licencias del conjunto final pertenecen a M0-06.

Estos límites están registrados con owner y stop condition en `docs/governance/M0_RESIDUAL_REGISTER.md`.
