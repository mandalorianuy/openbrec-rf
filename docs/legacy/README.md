# Documentos legacy — encarnación previa del proyecto

**Estado: `superseded`. Sin autoridad normativa. Fecha de archivo: 2026-07-19.**

Este directorio conserva la documentación de la encarnación previa de OpenBREC
RF: una plataforma de fusión radioeléctrica basada en radio-tomografía Wi-Fi
CSI, Kismet, SDR, despliegue con drones y recintos de atenuación RF (cortinas
Faraday). Esa línea fue reemplazada por el proyecto vigente: una **Open Spec
offline-first de comunicaciones de emergencia para BREC/USAR** (mesh LoRa,
Meshtastic/Reticulum, energía, beacons y federación), cuya autoridad normativa
vive en [`docs/open-spec/`](../open-spec/) y [`schemas/`](../../schemas/).

Los documentos de este directorio:

- **no definen** el comportamiento, los contratos ni los requisitos del sistema
  actual;
- **no elevan claims**: cualquier afirmación de capacidad (detección de
  personas, atenuación RF, despliegue con drones) corresponde a aquella
  encarnación y carece de validación vigente;
- se conservan como **contexto histórico y audit trail** de las decisiones que
  llevaron al proyecto actual.

Para el estado y rumbo vigentes, ver [`ROADMAP.md`](../../ROADMAP.md) en la
raíz del repositorio y [`README.md`](../../README.md).

**Nota 2026-07-19:** los dominios de RF sensing de esta encarnación (CSI,
metadata pasiva, SDR receive-only, drones, RF quieting, RuView) fueron
**reintegrados como addons experimentales** de la spec vigente — ver
[`docs/adr/ADR-004-rf-sensing-reintegration.md`](../adr/ADR-004-rf-sensing-reintegration.md)
y las guías de `docs/guides/`. El material de este directorio sigue siendo
fuente `[superseded]`: las guías nuevas lo citan como
`[superseded, fuente]` y ningún claim se hereda sin la tabla de evidencia de
[`docs/research/rf-sensing-state-of-the-art.md`](../research/rf-sensing-state-of-the-art.md).

## Contenido

| Documento | Tema de la encarnación previa |
| --- | --- |
| [OPENBREC_RF_TECHNICAL_DESIGN.md](OPENBREC_RF_TECHNICAL_DESIGN.md) | Diseño técnico integral de la plataforma Wi-Fi-CSI |
| [BOM.md](BOM.md) | Lista de materiales de aquella plataforma |
| [01-concepto-operacional.md](01-concepto-operacional.md) | Concepto operacional |
| [02-arquitectura.md](02-arquitectura.md) | Arquitectura modular |
| [03-antenas.md](03-antenas.md) | Diseño de antenas externas |
| [04-validacion.md](04-validacion.md) | Plan de validación |
| [05-seguridad-etica.md](05-seguridad-etica.md) | Seguridad, privacidad y ética |
| [06-roadmap.md](06-roadmap.md) | Roadmap de aquella encarnación (obsoleto) |
| [07-requisitos.md](07-requisitos.md) | Requisitos |
| [08-ruview-evaluation.md](08-ruview-evaluation.md) | Evaluación de RuView (Wi-Fi CSI) |
| [09-drone-deployment.md](09-drone-deployment.md) | Despliegue mediante drones |
| [10-rf-quieting.md](10-rf-quieting.md) | RF Quieting: cortinas y recintos de atenuación |
