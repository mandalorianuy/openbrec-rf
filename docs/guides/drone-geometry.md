# Drones como geometría de sensing

## Objetivo

Usar el dron como constructor rápido de geometría de sensing — drop pods, relay temporal, scan móvil — con el autopiloto conservando toda la autoridad de vuelo y confirmación humana en todo release.

## Audiencia

Pilotos/responsables UAS del incidente, integradores del bridge de telemetría y operadores de la red de sensing.

## Prerrequisitos

Responsable UAS declarado, plataforma con autopiloto propio (PX4/ArduPilot o vendor), regulación aérea local validada (ejemplo de referencia: FAA SGI y Public Safety Shielded Operations en EE.UU.; **verificar local** en cada jurisdicción) y la [base citable de evidencia](../research/rf-sensing-state-of-the-art.md). La tesis de origen está en [docs/legacy/09](../legacy/09-drone-deployment.md) `[superseded, fuente]`; la decisión vigente es ADR-002.

## Capacidades necesarias

El addon experimental [`drone-deployment-event`](../../schemas/addons/1.0.0/drone-deployment-event.schema.json), telemetría normalizada según [hardware/drone-interface.md](../../hardware/drone-interface.md), geofence y lost-link documentados, y baseline EMI de motores registrada. Const del contrato: `flight_authority_in_core: false` — OpenBREC nunca controla vuelo (ADR-002).

## Alternativas permitidas

Caminos de hardware (todos ejemplos reemplazables):

1. **Accesible:** airframe abierto PX4/ArduPilot, Pixhawk y release por PWM.
2. **Field:** plataforma soportada localmente, RTK/VIO, winch ligero y redundancia.
3. **Industrial:** dron de carga/winch para gateway, batería o kit; integración cerrada como plugin.
4. **Interior:** microdrone protegido solo para reconocimiento/relay ligero; polvo y pérdida de señal limitan su uso.

## Componentes e interfaces

Bridge MAVLink 2 o API vendor-approved que solo consume telemetría y emite eventos normalizados: `drone_pose`, `payload_armed`, `payload_released`, `drop_impact`, `drop_stable`, `node_online`, `node_position_estimate`, `drone_emi_baseline`, `mission_aborted`. El drop pod sigue la FSM de [hardware/drop-pod.md](../../hardware/drop-pod.md): `PACKED → ARMED → RELEASED → IMPACT → SETTLING → ACTIVE → RECOVERED/LOST`, y las muestras de `RELEASED`, `IMPACT` y `SETTLING` **quedan excluidas de la fusión** (const del contrato).

## Release handshake

Doble confirmación humana, según [hardware/drone-interface.md](../../hardware/drone-interface.md) y `release_mode: human_confirmed` (const):

1. El operador selecciona payload y objetivo.
2. El bridge valida geofence y salud del sistema.
3. El operador confirma.
4. El sistema de vuelo actúa el release.
5. El bridge registra el release e inicia tracking de la caída.
6. El nodo confirma impacto, estabilidad y presencia en línea.

No existe release automático ni iniciado por el software de OpenBREC.

## Pasos

1. Documentar el safety gate UAS: responsable, masa, centro de gravedad, autonomía, release test, geofence, lost-link, zona de caída y procedimiento de abort.
2. Registrar la baseline EMI de motores (`drone_emi_baseline`) antes de usar el dron como plataforma de sensing.
3. Planificar la geometría: posiciones de drop, rutas de relay y ventanas de scan, coordinadas con el mando.
4. Ejecutar drops con el handshake de doble confirmación; cada evento queda registrado.
5. Excluir de fusión las muestras en caída/impacto/asentamiento; activar el nodo solo en `ACTIVE`.
6. Estimar `node_position_estimate` con su incertidumbre; revisión visual de la ubicación cuando sea posible.
7. Recuperar nodos cuando sea seguro y registrar `RECOVERED`/`LOST`.

## Resultado esperado

Una red de sensing con geometría registrada y trazable, construida sin exponer personal a zonas inaccesibles, con el vuelo siempre bajo el autopiloto y el release siempre bajo confirmación humana.

## Validación mínima

Fixtures válidos/inválidos del addon (rechazo de `release_mode` automático y de autoridad de vuelo en el core) y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

## Fallos comunes y recuperación

Ante lost-link, el autopiloto ejecuta su procedimiento propio; OpenBREC registra `mission_aborted` y nunca intenta recuperar el control. Ante nodo que no alcanza `ACTIVE`, declararlo `LOST` para fusión y no usar sus muestras. Ante EMI de motores que contamina el sensing, repetir baseline y acotar el scan a ventanas con motores en estado declarado.

## Safety, privacidad y preservación

Un drop es un objeto en caída sobre una escena con personal y posibles víctimas: zona de caída despejada, ventana anunciada y abort disponible son condiciones, no opciones. El dron no es cámara de vigilancia por defecto ni taxi autónomo; su rol es geometría de sensing y relay.

## Estado de evidencia

Térmica en drones USAR: `field-validated` (capacidad externa consolidada, fuera del core). Payloads RF open-source (drop pods, relay, scan): `specified`/`simulated`; sin casos SAR documentados. El stack PX4/MAVLink es maduro como plataforma, pero la integración OpenBREC es `specified` hasta evidence pack.

## Qué no demuestra

Un dron en el aire no demuestra cobertura de sensing, y la posición estimada de un nodo no demuestra su funcionamiento. Nada de lo sensado desde o vía el dron demuestra presencia o ausencia de víctimas por sí solo.

## Contratos normativos relacionados

Addon experimental [`drone-deployment-event`](../../schemas/addons/1.0.0/drone-deployment-event.schema.json) ([catálogo de addons](../../schemas/addons/catalog.json)), [hardware/drone-interface.md](../../hardware/drone-interface.md), [hardware/drop-pod.md](../../hardware/drop-pod.md), ADR-002 en [docs/adr](../adr/ADR-002-drone-deployed-sensor-geometry.md) y [Marco regulatorio](regulatory.md).
