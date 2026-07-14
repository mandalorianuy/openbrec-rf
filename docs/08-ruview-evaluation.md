# Evaluación e integración de RuView

## Veredicto

**Aporta de forma material**, especialmente como acelerador del plano CSI: firmware ESP32-S3/C6, formato binario, streaming UDP, servidor Rust/Axum, puente WebSocket, librerías Python y modelos publicados. No se adopta como núcleo ni se aceptan sus salidas semánticas como evidencia BREC sin validación independiente.

## Evidencia revisada

Revisión realizada el 14 de julio de 2026 sobre `ruvnet/RuView`, commit `90667d0f1d9f4dc129d999c7998d4036cac2e1b8`.

- El README declara CSI sobre ESP32-S3/C6, Rust, Docker y procesamiento edge.
- ADR-059 documenta `ESP32-S3 → UDP:5005 → sensing-server → WS:8765 → browser`.
- El repositorio usa licencia MIT.
- El propio README reconoce una brecha concreta: el modelo HF se distribuye como JSONL RVF, mientras el loader del sensing-server espera RVF binario. El uso de `--model` puede producir `invalid magic` y salida nula.
- El README también corrige una métrica previa de “100% presence” y publica una evaluación temporal distinta, señal positiva de transparencia pero también evidencia de que las cifras deben auditarse.

## Qué reutilizar

1. Firmware y captura CSI, previa prueba de RF, reloj, pérdida de frames y antena.
2. ADR-018 como transport format o como fuente para un decoder compatible.
3. Sensing-server como bridge opcional.
4. Extractores Python concretos con model card y dataset card.
5. Ideas de replay determinístico, witness logs y documentación por ADR.

## Qué no importar ciegamente

- claims de pose, signos vitales o conteo sin dataset BREC;
- modelos entrenados en habitaciones como evidencia en escombros;
- dependencia de servicios/appliances propietarios;
- seguimiento automático de `main`;
- catálogos de módulos sin test de integración reproducible;
- inferencia live con la brecha JSONL/RVF abierta.

## Adapter contract

`collector-ruview` debe aceptar tres fuentes:

- UDP ADR-018 crudo;
- WebSocket del sensing-server;
- batch/replay desde archivos.

Y emitir:

- `RadioObservation` con frame metadata;
- `Evidence` etiquetada `experimental`;
- `ModelVersion` con hash, commit, formato y configuración;
- métricas de pérdida, jitter, frecuencia efectiva y calibración.

## Gates

- reproducción de fixture determinístico;
- detección explícita del error JSONL/RVF;
- fallback visible, nunca null silencioso;
- evaluación por día, geometría, material y posición;
- clase `unknown`/OOD;
- baseline sin modelo;
- no persistir payloads de terceros.

## Fuentes

- https://github.com/ruvnet/RuView
- https://github.com/ruvnet/RuView/blob/main/docs/adr/ADR-059-live-esp32-csi-pipeline.md
- https://github.com/ruvnet/RuView/blob/main/LICENSE
