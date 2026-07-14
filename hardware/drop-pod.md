# OpenBREC Drop Pod v1

## Requisitos

- masa 150–350 g;
- carcasa no metálica IP54/IP65;
- autoenderezable o con antena útil en varias caras;
- absorción de impacto y batería retenida;
- U.FL/SMA con strain relief;
- ESP32-S3/C6, IMU, almacenamiento local y temperatura;
- GNSS opcional, UWB recomendado para GNSS-denied;
- aro de liberación certificado para 5× masa estática;
- LED/buzzer con modo oscuro/silencioso;
- QR y código visible;
- firmware firmado y botón físico de wipe/provision.

## FSM

`PACKED → ARMED → RELEASED → IMPACT → SETTLING → ACTIVE → RECOVERED/LOST`

Las muestras de `RELEASED`, `IMPACT` y `SETTLING` no participan en fusión.
