> ⚠️ Documento histórico — corresponde a la encarnación Wi-Fi-CSI previa del proyecto. Sin autoridad normativa. Ver [docs/legacy/README.md](README.md).

# Arquitectura modular

## Núcleo obligatorio
- registro de incidentes, sectores, nodos y antenas;
- bus MQTT;
- normalización de observaciones;
- motor de fusión;
- PWA local;
- replay y auditoría.

## Nodos
### Drop Node
ESP32-S3/C6 económico, antena externa, batería y montaje rápido. Puede escuchar BLE/Wi-Fi, ejecutar enlaces CSI controlados y enviar telemetría.

### RF Scout Node
Raspberry Pi/mini-PC con dos o más radios Wi-Fi, Bluetooth, SDR receive-only y puertos de antena. Ejecuta Kismet remote capture y collectors.

### Gateway
Mini-PC resistente o laptop que aloja Docker, base local, UI y sincronización. El backhaul preferido es Ethernet/PoE; el inalámbrico es contingencia.

## Diseño degradable
Cada plugin publica un manifiesto de capacidades. La UI solo presenta inferencias que el despliegue puede sostener.
