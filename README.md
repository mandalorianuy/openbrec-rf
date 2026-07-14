# OpenBREC RF

OpenBREC RF es una plataforma open source, modular y offline-first para investigar **radio-tomografía oportunista, despliegue rápido de sensores y fusión explicable de evidencia** durante operaciones BREC/USAR en estructuras colapsadas.

![Arquitectura](docs/assets/architecture.png)

## Qué hace diferente al proyecto

- reutiliza captura Wi‑Fi pasiva, BLE, CSI, BFI, SDR y herramientas defensivas de ciberseguridad como sensores de contexto;
- forma enlaces radio controlados alrededor de sectores o vacíos;
- admite antenas externas omni y direccionales como componentes calibrados;
- integra RuView como collector/model provider opcional, sin acoplar el core;
- permite desplegar Drop Nodes con drones y convertir la trayectoria del dron en una apertura sintética;
- incorpora cortinas o recintos de atenuación RF para reducir interferencia de forma temporal y medible;
- funciona con las capacidades disponibles y se abstiene cuando la evidencia es insuficiente.

> [!IMPORTANT]
> El sistema produce **indicios**, no diagnósticos ni certezas de víctima. La ausencia de RF nunca descarta una persona atrapada.

## Documentos principales

- [`OPENBREC_RF_TECHNICAL_DESIGN.md`](OPENBREC_RF_TECHNICAL_DESIGN.md) — diseño técnico completo.
- [`BOM.md`](BOM.md) — componentes por niveles, Uruguay y fuentes oficiales/US.
- [`CODEX_MASTER_PROMPT.md`](CODEX_MASTER_PROMPT.md) — bundle de ejecución para Codex.
- [`AGENTS.md`](AGENTS.md) — reglas para agentes de desarrollo.
- [`docs/08-ruview-evaluation.md`](docs/08-ruview-evaluation.md) — validación e integración de RuView.
- [`docs/09-drone-deployment.md`](docs/09-drone-deployment.md) — drones, Drop Pods y scans móviles.
- [`docs/10-rf-quieting.md`](docs/10-rf-quieting.md) — cortinas, carpas y aislamiento medido.

## Perfiles

| Perfil | Sensores / capacidades |
|---|---|
| `field-basic` | Wi‑Fi pasivo, BLE y mapa de actividad. |
| `field-csi` | Enlaces CSI controlados y detección de cambio. |
| `field-ruview` | Firmware/procesamiento RuView mediante adapter. |
| `field-spectrum` | SDR receive-only y barridos direccionales. |
| `field-drone-drop` | Telemetría de dron y Drop Nodes. |
| `field-drone-rf` | Barrido RF móvil con pose conocida. |
| `field-rf-quiet` | Medición antes/después con cortinas o recinto RF. |
| `lab-bfi` | BFI experimental con participantes registrados. |
| `advanced-fusion` | Plugins avanzados UWB/mmWave/acústica/sísmica. |

## Validación local

```bash
python3 scripts/validate_bundle.py
```

## Crear el repositorio GitHub

El ZIP incluye un repositorio Git inicializado en `main`, sin remoto ni credenciales. Tras descomprimir:

```bash
cd OpenBREC-RF-v0.2
git log --oneline
git remote add origin git@github.com:TU_USUARIO/openbrec-rf.git
git push -u origin main
```

También se incluye [`GITHUB_PUBLISH.md`](GITHUB_PUBLISH.md).

## Licencias

- software y configuración: Apache-2.0;
- hardware de referencia: CERN-OHL-S-2.0;
- documentación: CC BY-SA 4.0;
- dependencias y proyectos externos conservan sus licencias. RuView no está vendorizado y se referencia bajo MIT.
