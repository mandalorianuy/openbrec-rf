# Quickstart mínimo off-grid

## Objetivo

Ejecutar localmente un flujo reproducible de terminales, texto breve, estado, SOS y ubicación sin cloud ni transmisión RF.

## Audiencia

Lectores, integradores y constructores que quieren comprobar la semántica antes de elegir hardware.

## Prerrequisitos

Git, `uv`, Python 3.12 y las dependencias ya bloqueadas. El checkout debe estar limpio para producir receipts canónicos.

## Capacidades necesarias

Dos identidades de terminal simuladas, almacenamiento local, reloj monotónico y un adapter de transporte simulado.

## Alternativas permitidas

El adapter simulado puede sustituirse después por Meshtastic, MeshCore, Reticulum, LoRaWAN privado u otro bearer que preserve el overlay OpenBREC.

## Componentes e interfaces

`HumanMessage`, `TransportEnvelope`, lifecycle append-only, fixtures JSONL y verificador offline. Ninguna marca o radio es obligatoria.

## Pasos

1. Clonar el repositorio e instalar el lock sin resolver dependencias nuevas: `uv sync --frozen`.
2. Validar los contratos: `uv run --offline python -m openbrec.verify open-spec`.
3. Validar mensajería y SOS: `uv run --offline python -m openbrec.verify open-spec-messaging`.
4. Ejecutar replay: `uv run --offline python -m openbrec.verify core-replay --bundle fixtures/replay/core/m0-six-node.json`.
5. Inspeccionar el resultado sin interpretar recepción técnica como lectura o rescate.

## Resultado esperado

Contratos válidos, replay determinístico y eventos distinguibles para texto, estado, SOS y ubicación, sin conexión cloud ni TX.

## Validación mínima

Los tres comandos terminan con código `0`. Registrar el SHA, los comandos y los resultados; asignar como máximo `simulated`.

## Pipeline software end-to-end (lab-sim, opcional)

Además de los gates, el repo incluye un pipeline de referencia que corre local con datos sintéticos: API → MQTT → worker → fusión determinística → PostgreSQL → API de lectura → PWA. Requiere `docker compose`; la primera ejecución descarga las imágenes pineadas por digest, después funciona offline.

1. Provisionar secretos de laboratorio (efímeros, fuera del árbol de git):

   ```bash
   mkdir -p .lab-secrets
   openssl rand -base64 32 > .lab-secrets/postgres_password
   openssl rand -base64 32 > .lab-secrets/openbrec_master_key
   export OPENBREC_POSTGRES_PASSWORD_FILE_HOST=$PWD/.lab-secrets/postgres_password
   export OPENBREC_MASTER_KEY_FILE_HOST=$PWD/.lab-secrets/openbrec_master_key
   ```

2. Levantar la pila: `docker compose --profile lab-sim up --build --wait`. La red `lab-core` es interna; solo la PWA queda expuesta en `127.0.0.1:8080` y proxya `/api/` hacia la API.
3. Publicar una observación sintética válida:

   ```bash
   curl -sS -X POST http://127.0.0.1:8080/api/v1/observations -H 'content-type: application/json' --data @fixtures/contracts/core/1.0.0/observation/valid/minimal.json
   ```

4. Leer lo persistido por el worker (validado contra los schemas core):

   ```bash
   curl -sS 'http://127.0.0.1:8080/api/v1/observations?limit=10'
   curl -sS 'http://127.0.0.1:8080/api/v1/fusion-results?limit=10'
   curl -sS 'http://127.0.0.1:8080/api/v1/fusion-results/<result_id>'
   ```

5. Abrir `http://127.0.0.1:8080`: el indicador **Fuente** muestra `API en vivo` cuando la PWA lee `/v1/fusion-results` del pipeline, o `fixtures verificados` cuando cae a los fixtures estáticos (comportamiento offline-first; sin la API todo sigue funcionando desde el cache).

El motor de fusión (`openbrec/fusion.py`) aplica reglas determinísticas sin ML: una sola fuente produce un `indicator` de confianza baja, la corroboración exige ≥2 sensores y ≥2 tipos de sensor, y ante evidencia insuficiente (calidad < 0.5 o solo `no_event_detected`) el resultado es `abstained` con razones explícitas. Ningún resultado confirma presencia ni ausencia; el silencio nunca implica ausencia. Para apagar: `docker compose --profile lab-sim down --volumes`.

## Fallos comunes y recuperación

Si `uv` intenta usar red, ejecutar primero `uv sync --frozen` con conectividad de provisioning y repetir los gates con `--offline`. Si falla un fixture, no editar el resultado: corregir el contrato o fixture y repetir desde cero.

## Safety, privacidad y preservación

No descartar SOS ambiguos; preservarlos para review con acceso y retención gobernados. Minimizar identificadores, pero no provocar pérdida silenciosa de información crítica.

## Estado de evidencia

`simulated` para la ruta incluida; transportes y hardware físicos permanecen `unverified` hasta un evidence pack aplicable.

## Qué no demuestra

No demuestra alcance, airtime, autenticidad de un dispositivo real, autonomía, cumplimiento regulatorio, detección de personas ni operación de campo.

## Contratos normativos relacionados

[Mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json), [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [conformance](../open-spec/CONFORMANCE.md).
