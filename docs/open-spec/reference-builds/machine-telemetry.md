# Red privada de telemetría máquina

## Alcance

Transporta estados de componentes mediante redes locales por ResponseCell. No
define una mega-mesh del incidente ni exige un bearer concreto.

## Plano funcional

`endpoint → bearer local → collector append-only → backhaul opcional/carry`

El bearer sólo transporta envelopes; identidad y semántica siguen en OpenBREC.

## BOM por capacidades

- endpoints con identidad, secuencia y cola local;
- collector offline con frontera de adapter;
- backhaul outbound-only opcional.

## Reutilización

Puede reutilizar LoRaWAN privado, enlaces locales, gateways existentes o carry
bundles si se fijan versiones, claves, cuotas y fallback.

## Verificación

Probar replay, contador regresivo, pérdida de enlace, store-and-forward,
congestión y kill switch. Medir RF antes de habilitar claims físicos.

## Límites

No garantiza entrega, capacidad o autorización regulatoria. Clave default,
interferencia perjudicial o counter rollback obligan a deshabilitar TX.
