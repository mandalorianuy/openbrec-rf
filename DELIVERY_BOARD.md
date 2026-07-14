# OpenBREC RF — Delivery Board

## Now — M0 Fundación
- [ ] Crear monorepo y ADR-0001 de alcance/red lines.
- [ ] Generar modelos Pydantic y TypeScript desde JSON Schema.
- [ ] Implementar simulador de seis nodos, dos tracks y tres zonas.
- [ ] Arrancar `lab-sim` completamente offline.
- [ ] Mostrar matriz de capacidades, mapa, timeline y explicación.
- [ ] Implementar replay determinístico y prueba de hash de salida.

## Next — M1 RF pasivo
- [ ] Collector Kismet desde fixture sanitizado.
- [ ] Collector BLE sintético y luego BlueZ/nRF52840.
- [ ] HMAC rotativo por incidente.
- [ ] Métricas RSSI/sector y estado de radio/canal.
- [ ] Gate que demuestra que no se persisten payloads.

## Later — M2 CSI y campo
- [ ] Firmware ESP32-S3 con telemetría de salud y CSI.
- [ ] Registro de radio, cable, antena, azimut, altura y polarización.
- [ ] Baseline/adaptive change detection sin ML.
- [ ] Cajas, energía, tripods y procedimientos de calibración.
- [ ] Banco de escombros instrumentado y protocolo ciego.

## Experimental
- [ ] SDR receive-only.
- [ ] 802.15.4.
- [ ] BFI/Wi-BFI con clase unknown y OOD.
- [ ] UWB para rescatistas/nodos.
- [ ] mmWave, acústica y sísmica como plugins.

## Gates permanentes
- [ ] Offline startup.
- [ ] Deterministic replay.
- [ ] Schema compatibility.
- [ ] No payload retention.
- [ ] No offensive RF features.
- [ ] Node-loss degradation.
- [ ] Explainability and abstention.


## M7 — RuView adapter
- [ ] ADR-018 UDP decoder and replay fixture
- [ ] JSONL/RVF compatibility gate
- [ ] sidecar model adapter with OOD

## M8 — Drone-deployed sensing
- [ ] Drop Pod prototype and FSM
- [ ] MAVLink read-only bridge
- [ ] human-confirmed release simulator
- [ ] drone EMI baseline protocol

## M9 — RF Quieting
- [ ] curtain sample characterization
- [ ] IsolationProfile ingest/UI
- [ ] independent communications safety gate
