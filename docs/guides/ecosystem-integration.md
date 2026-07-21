# Integración con el ecosistema SAR (TAK, Meshtastic MQTT, CAP, CalTopo, APRS)

## Objetivo

Conectar un deployment OpenBREC con las plataformas que el mundo SAR/USAR ya usa, como complemento exportador/consumidor con provenance, sin elevar estados de evidencia ni crear dependencia de nube.

## Audiencia

Integradores, operadores técnicos del puesto de comando y enlaces con equipos que operan ATAK, CalTopo, Meshtastic o APRS.

## Prerrequisitos

Deployment local funcionando (broker MQTT, pipeline de evidencia), la arquitectura y citas de [Integración con el ecosistema SAR](../research/sar-integration.md) leída, y por camino:

- **CoT/TAK:** ATAK en la misma LAN (multicast basta) u OpenTAKServer en Raspberry Pi para persistencia; PyTAK como librería del puente.
- **Meshtastic MQTT:** nodo gateway **ESP32** con el módulo MQTT oficial habilitado por canal hacia el broker propio.
- **CAP/EDXL:** el perfil `interop-emergency-standards-profile` declarado ([guía](interop-emergency-standards.md)); convenio con la autoridad solo si se busca consumo gubernamental (IPAWS y análogos son por MOA, no por API).
- **CalTopo:** cuenta con locator "Live Track - Fleet, Email, Other" (connect key) o import/export GPX/KML/CSV; conectividad eventual hacia el SaaS.
- **APRS (opcional):** licencia de radioaficionado para la parte RF y direwolf como TNC.

## Capacidades necesarias

El addon experimental `cot-bridge-profile` (schemas/addons/1.0.0/) para el puente CoT, el addon existente `interop-emergency-standards-profile` para CAP/EDXL, y las invariantes transversales de la sección siguiente en **toda** integración saliente.

## Invariantes de toda integración saliente

- Nunca identificar personas: seudonimización con el hash rotativo del incidente.
- El silencio nunca es ausencia; exportar silencio está prohibido como afirmación.
- El ACK de una plataforma externa (CoT recibido, CAP `Ack`, track visible en CalTopo) **no confirma persona localizada** ni aceptación operativa.
- Provenance preservado: toda observación exportada conserva fuente, timestamp e incertidumbre.
- Los estados de evidencia **no se elevan por exportar**: una observación `unverified` llega `unverified` y se etiqueta como tal.

## Alternativas permitidas

Los cinco caminos de la [matriz de priorización](../research/sar-integration.md): CoT/TAK (#1), Meshtastic MQTT (#2), CAP/EDXL (#3), CalTopo (#4), APRS (opcional). Descartados con razón registrada: goTenna, Virtual OSOCC (sin API), SARCOP-write temprano (export de archivos primero; su dominio de waypoints es el vocabulario destino de referencia).

## Componentes e interfaces

Puente MQTT→CoT (PyTAK; multicast SA 239.2.3.1:6969, TCP 8087 o TLS 8089), modelado `usericon` propio + `detail/remarks` estructurado (no hay taxonomía USAR oficial de types CoT), gateway Meshtastic↔broker por canal, exportador CAP/EDXL-DE, poster de posiciones al locator CalTopo y publicador de Objects APRS vía direwolf. Precedentes de mapping del ecosistema: aprscot, inrcot, LINCOT.

## Pasos

1. **CoT/TAK:** consumir eventos del broker local, mapear observaciones/hechos a eventos CoT con `uid` estable, `type` con usericon propio y remarks estructurado (fuente, estado de evidencia, confianza); emitir por UDP multicast SA para ATAK en LAN o por TCP/TLS a OpenTAKServer en la RPi; declarar `stale` para que los marcadores expiren.
2. **Meshtastic MQTT:** habilitar uplink/downlink por canal en el gateway ESP32 hacia el broker propio; consumir JSON si el gateway es ESP32, protobuf (`ServiceEnvelope`) si no; mantener cifrado y descifrar en el puente con la clave del canal; tratar node ID como identidad no confiable.
3. **CAP/EDXL:** declarar el `field_map` del perfil, seudonimizar, confirmar humanamente y exportar por MQTT/HTTP/archivo; conservar pendientes si la autoridad es inalcanzable.
4. **CalTopo:** POST de posiciones al locator "Fleet/Email/Other" cuando haya conectividad; import/export GPX/KML/CSV como camino base; nunca en el camino crítico.
5. **APRS (opcional):** publicar Objects (p.ej. `VICTIM-01`) vía direwolf respetando beacon rates; solo con licencia ham para RF.
6. En todos: registrar cada exportación en el journal con provenance y ejecutar replay del mapeo con fixtures.

## Resultado esperado

Observaciones y hechos OpenBREC visibles en ATAK/CalTopo/SARTrack con su incertidumbre y provenance intactos, sin dependencia de nube en el camino crítico y sin claims elevados.

## Validación mínima

Fixtures válidos/inválidos de los addons y gates de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

Replay determinístico del mapper OpenBREC→CoT (XML lab-sim, sin sockets: uid incident-scoped, stale por TTL, remarks estructurado con provenance, abstención preservada, sin coordenadas inventadas):

```bash
uv run --offline python -m openbrec.verify interop-cot
```

## Fallos comunes y recuperación

Gateway nRF52 sin JSON mode: usar gateway ESP32 o consumir protobuf. Broker con tráfico en claro: reactivar cifrado del canal y descifrar en el puente. Marcadores CoT que no expiran: declarar `stale` siempre. Downlink mesh saturado: presupuestar duty cycle y priorizar SOS. CalTopo/APRS-IS inalcanzables: exportación diferida; el estado operativo interno no cambia.

## Safety, privacidad y preservación

Exportar posiciones y observaciones expone datos de víctimas y rescatistas fuera del perímetro propio: seudonimizar, minimizar y confirmar humanamente cada camino. APRS-IS puede gatear todo paquete a RF pública; el multicast CoT es visible para cualquier ATAK de la LAN. La prioridad life-safety manda sobre la minimización, con auditoría.

## Estado de evidencia

Caminos Meshtastic MQTT, CAP/EDXL, CalTopo y APRS: `specified` (diseño + investigación citada). Puente CoT: el addon `cot-bridge-profile` y su mapper de referencia quedan en `simulated` a nivel contrato/mapeo (gate `interop-cot`, replay determinístico lab-sim sin sockets, receipt en `evidence/interop/`). Interoperabilidad probada con ATAK, CalTopo o APRS: `unverified` hasta evidence pack de la combinación exacta. Los componentes externos citados (PyTAK, OpenTAKServer, módulo MQTT, direwolf) son de terceros con actividad documentada en la investigación.

## Qué no demuestra

No demuestra interoperabilidad certificada con TAK/CalTopo/APRS, ni aceptación por ninguna agencia, ni que un marcador exportado represente una persona localizada. Exportar no eleva evidencia.

## Contratos normativos relacionados

Addons experimentales `cot-bridge-profile` y `interop-emergency-standards-profile` en schemas/addons/1.0.0/ ([catálogo de addons](../../schemas/addons/catalog.json)), decisión del puente CoT en [RFC 0004](../open-spec/rfc/0004-cot-tak-bridge-addon.md), [arquitectura de integración](../research/sar-integration.md), [perfiles multi-bearer](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) y [Interoperación CAP/EDXL](interop-emergency-standards.md).
