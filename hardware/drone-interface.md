# Drone integration interface

El bridge acepta MAVLink 2 o adapter vendor y emite eventos normalizados. No controla vuelo en v0.2.

## Required telemetry

- monotonic timestamp;
- latitude/longitude/altitude when available;
- local NED/ENU pose;
- attitude;
- navigation quality;
- motor/armed state;
- payload state;
- battery;
- mission/flight id.

## Release handshake

1. operator selects payload and target;
2. bridge validates geofence and health;
3. operator confirms;
4. flight system actuates release;
5. bridge records release and starts drop tracking;
6. node confirms impact/stability/online.
