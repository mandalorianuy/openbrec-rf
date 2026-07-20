# Arquitectura de integración con el ecosistema SAR (CoT/TAK, Meshtastic MQTT, CAP/EDXL, CalTopo, APRS)

- Estado: revisión documental de fuentes públicas (julio 2026); no autoriza implementación, claims de interoperabilidad probada, compra ni TX
- Fecha de corte: 2026-07-19
- Alcance: caminos técnicos de integración entre OpenBREC y las plataformas que el mundo SAR/USAR ya usa, con priorización valor/esfuerzo
- Relación: extiende el [panorama SAR y posicionamiento](sar-landscape.md) (§3 "complemento, no competidor") con la arquitectura concreta de cada puente; los estados de evidencia siguen la misma disciplina que la [investigación SOTA de RF sensing](rf-sensing-state-of-the-art.md)
- Ítems no verificados (declarados): types CoT internos del plugin SAR de AFRL; fecha del último commit de OpenTAKServer; NMEA nativo en WinTAK; existencia de cualquier API de Virtual OSOCC/ICMS

## 1. Puente CoT/TAK — prioridad 1

**Qué es.** Cursor on Target (CoT) es XML simple (`<event><point/><detail/></event>`) con atributos `uid`, `type`, `time`, `start`, `stale`; es el formato de awareness de ATAK/WinTAK/iTAK, estándar de facto en SAR táctico.

**Cómo conecta.** Transportes estándar: TCP plano **8087**, TCP/TLS **8089**, WebUI/API **8443** ([myTeckNet](https://mytecknet.com/tak-security-best-practices/), [node-red-contrib-tak-registration](https://flows.nodered.org/node/node-red-contrib-tak-registration), [TAK Server Configuration Guide 5.2 (PDF)](https://static1.squarespace.com/static/5404b7d2e4b0feb6e5d9636b/t/6756e17b053bbe305668a08f/1733747077204/TAK_Server_Configuration_Guide_5.2.pdf)), y **UDP multicast SA 239.2.3.1:6969**: ATAK se autodescubre en LAN sin ningún servidor ([uas-forge TAK Integration Guide](https://uas-forge.com/tak-guide/)). Consecuencia clave: un puente MQTT→CoT puede emitir multicast y cualquier ATAK de la LAN lo ve sin TAK Server ni internet.

**Servidor on-premise (opcional, para persistencia/chat/Data Packages):** OpenTAKServer (activo, corre en Raspberry Pi/Ubuntu, soporta ATAK ≥4.8, WinTAK, iTAK, CloudTAK, PyTAK: [repo](https://github.com/brian7704/OpenTAKServer), [docs](https://docs.opentakserver.io/); "under active development", último commit no verificado) en vez de FreeTAKServer (funciona pero estancado: último commit 29-oct-2024, [commits](https://github.com/FreeTAKTeam/FreeTAKServer/commits), [REST API](https://freetakteam.github.io/FreeTAKServer-User-Docs/API/REST_API_PublicDoc/)). TAK Server oficial: binarios vía [tak.gov](https://tak.gov/products) con cuenta aprobada; corre 100 % offline una vez instalado.

**Librería del puente:** PyTAK (snstac, Apache-2.0, actualizado jul-2026; asyncio, URLs `tcp://`/`tls://`/`udp://`/multicast: [PyTAK](https://www.snstac.com/pytak), [quickstart](https://pytak.readthedocs.io/en/stable/quickstart/), [org snstac](https://github.com/orgs/snstac/repositories)). Precedentes de gateway directamente reutilizables como patrón de mapping: **aprscot** (APRS→CoT), **inrcot** (inReach→CoT), **LINCOT** (gpsd→CoT, con fan-out NMEA para WinTAK), DroneCOT, adsbcot, aiscot. PyCoT original archivado; fork activo [COASsoft/PyCoT](https://github.com/COASsoft/PyCoT).

**Qué fluye.** Saliente: posiciones/estados de equipos, observaciones y hechos consolidados como marcadores CoT. Entrante (opcional): marcadores del operador ATAK como observaciones con provenance externa declarada.

**Qué se pierde/degrada.** No hay taxonomía oficial USAR de types CoT verificable (la base está en el [CoT Developer Guide, NPS/MITRE, PDF de referencia](https://nps.edu/documents/104517539/109705106/COT+Developer+Guide.pdf/cb125ac8-1ed1-477b-a914-7557c356a303); el plugin SAR de AFRL para ATAK-CIV, mar-2026, no publica sus types — [CivTAK](https://www.civtak.org/2026/03/23/search-rescue-plugin-released/), no verificado). Recomendación: `usericon` propio + `detail/remarks` estructurado (el patrón de FTS `ManageEmergency`). La semántica de estados de evidencia OpenBREC (observación/hipótesis/hecho, confianza, abstención) **no existe en CoT**: viaja como texto estructurado en remarks y se degrada a anotación.

**Requisitos.** Ninguno legal; red LAN local o TAK Server propio.

**Estado de evidencia.** El addon `cot-bridge-profile` y su mapper de referencia: `simulated` (gate `interop-cot`, replay determinístico lab-sim sin sockets). El camino como diseño de integración: `specified` (investigación citada). Interoperabilidad probada con ATAK: `unverified` hasta evidence pack.

## 2. Meshtastic MQTT — prioridad 2

**Qué es.** El módulo MQTT oficial de Meshtastic ([docs](https://meshtastic.org/docs/configuration/module/mqtt/)): un nodo con WiFi/Ethernet (o Client Proxy vía teléfono) reenvía paquetes mesh↔broker; uplink/downlink por canal, TLS, root topic propio, broker propio recomendado.

**Cómo conecta.** OpenBREC ya usa Mosquitto local: el gateway ESP32 publica en el mismo broker; el puente consume/publica. Con **JSON mode** la integración es trivial — pero JSON **no cifrado y no soportado en nRF52** (Rak4631, T-Echo: gran parte del hardware LoRa barato); con gateway ESP32 no hay problema, si no, hay que consumir protobuf (`ServiceEnvelope`). Con "Encryption Enabled" apagado, todo sale en claro al broker aunque el canal tenga clave; con broker propio puede quedar cifrado y descifrarse en el puente con la clave del canal.

**Qué se pierde.** E2E si JSON/encryption-off; identidad reducida a node ID de 4 bytes sin verificación; los ACKs de aplicación y la lógica de retransmisión mesh no cruzan limpios; el downlink compite por el duty cycle del canal (los docs advierten no usar LongFast público).

**Estado de evidencia.** `specified`; el overlay OpenBREC sigue siendo la autoridad de identidad/prioridad (los perfiles multi-bearer ya declaran `node_id_is_actor_identity: false`).

## 3. Export CAP/EDXL — prioridad 3

**Qué es.** CAP 1.2 + EDXL-DE como formato canónico de exportación hacia autoridades y entre nodos propios. El addon existente `interop-emergency-standards-profile` lo define como `export_only` con `gateway_implemented: false` (guía [Interoperación CAP/EDXL](../guides/interop-emergency-standards.md)).

**Cómo conecta.** Offline es trivial: XML por MQTT/HTTP/archivo. El consumo gubernamental es **por convenio, no por API**: IPAWS-OPEN (FEMA) recibe CAP autenticado de autoridades con MOA ([FEMA IPAWS-OPEN](https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system/technology-developers/ipaws-open), [Interface Design Guide v4 draft (PDF)](https://content.govdelivery.com/attachments/USDHSFEMA/2024/09/11/file_attachments/2994434/IPAWS-OPEN-v4-02-06_InterfaceDesignGuide_Draft.pdf)); NWS CAP ([vlab.noaa.gov](https://vlab.noaa.gov/web/nws-common-alerting-protocol/cap-documentation)). Open source offline que ya habla CAP: [OpenBroadcaster](https://www.openbroadcaster.com/2024/10/open-source-cap-broadcaster-development-guide/), [cap-ipaws-bridge](https://github.com/Kadivendi/cap-ipaws-bridge) (patrón idéntico: ingesta IPAWS con failover a mesh), [OpenAlerting](https://openalerting.org).

**Estado de evidencia.** `specified`; sin gateway implementado ni interop probada con ninguna agencia.

## 4. CalTopo — prioridad 4

**Qué es.** La herramienta estándar wilderness (propietaria, SaaS). Tres vías de integración:

- **API Team oficial** ([Supported API for Teams](https://training.caltopo.com/all_users/team-accounts/teamapi)): service accounts HMAC-SHA256, REST `/api/v1/...`, CRUD de Marker/Shape, mapas modo `sar`. **Paga y SaaS; sin on-premise** (la app cachea offline, el backend no).
- **Locator "Live Track - Fleet, Email, Other"**: endpoint HTTP con connect key al que un servicio propio le hace POST de posiciones — **inyección de tracks en vivo** sin la API firmada completa ([blog CalTopo](https://blog.caltopo.com/2022/04/21/live-tracks-for-locators-and-trackable-devices/), [Live Team Tracking](https://training.caltopo.com/all_users/team-accounts/team-tracking), [ejemplo de puente externo](https://awareoutdoors.com/caltopo_bridge/)). Vía documentada preferida.
- **Import/export GPX/KML/CSV** nativo; wrapper comunitario no oficial [ncssar/caltopo_python](https://github.com/ncssar/caltopo_python); precedente CoT→CalTopo: [node-red-contrib-cot2xtopo](https://flows.nodered.org/node/node-red-contrib-cot2xtopo).

**Qué se pierde.** Todo depende de conectividad hacia el SaaS: es un camino de exportación "cuando vuelve la red", coherente con el rol complemento de OpenBREC.

**Estado de evidencia.** `specified`.

## 5. APRS — opcional

**Qué es.** Red de radioaficionados; consumida por SARTrack, CalTopo (locator APRS nativo) y aprs.fi sin que el receptor instale nada.

**Cómo conecta.** OpenBREC→APRS publicando **Objects** (p.ej. "VICTIM-01") vía [direwolf](https://github.com/wb2osz/direwolf) (soundcard TNC, digipeater, iGate); **aprscot** cierra el lazo APRS→TAK. APRS-IS ([aprs-is.net](https://www.aprs-is.net/)) tiene reglas estrictas (beacon rates, todo paquete puede ser gateado a RF).

**Requisitos.** **Licencia de radioaficionado para emitir RF**; APRS-IS puro sin RF es poco útil sin internet. En Uruguay hay comunidad ham activa.

**Estado de evidencia.** `specified`.

## 6. Matriz de priorización

| Camino | Valor | Esfuerzo | Decisión |
|---|---|---|---|
| 1. Puente CoT/TAK (multicast/TCP, PyTAK, OpenTAKServer en RPi) | Máxima tracción táctica real, 100 % offline | Bajo (PyTAK + consumidor MQTT; sin servidor para la demo) | **GO** — addon `cot-bridge-profile` |
| 2. Meshtastic MQTT | Ya comparte el broker con OpenBREC | Bajo | **GO** (gateway ESP32; vigilar trampas JSON/nRF52/cifrado) |
| 3. Export CAP/EDXL | Formato canónico hacia autoridad | Bajo (export-only ya `specified`) | **GO** (mantener export-only; IPAWS por convenio) |
| 4. CalTopo locator + GPX/KML | Estándar wilderness; tracks en vivo por POST | Bajo-medio (requiere SaaS/cuenta) | **GO** como exportación diferida |
| 5. APRS Objects (direwolf/aprscot) | Visibilidad gratis donde hay hams | Bajo | **OPCIONAL** (exige licencia ham para RF) |
| goTenna | — | — | **DESCARTADO**: línea consumer muerta, SDK sin mantener (mirror 2018-2019, [willcl-ark/gotenna-PublicSDK](https://github.com/willcl-ark/gotenna-PublicSDK)), empresa pivotada a defensa y adquirida por Forterra oct-2025 ([Forterra](https://www.forterra.com/posts/forterra-acquires-gotenna-advancing-autonomous-mission-systems-with-next-generation-communication-technology)); viola "open hardware friendly" |
| Virtual OSOCC / ICMS | Coordinación INSARAG | — | **DESCARTADO como integración**: plataforma web con contraseña, sin API pública documentada ([vosocc.unocha.org](https://vosocc.unocha.org), [insarag.org/vosocc](https://insarag.org/vosocc/)); camino realista: export CAP/EDXL + adjuntos que un oficial sube manualmente |
| SARCOP-write (applyEdits) | Alto (vocabulario destino casi 1:1) | Alto | **DIFERIDO**: la capa Waypoints v9 es pública en lectura ([FeatureServer/1](https://services.arcgis.com/0ZRg6WRC7mxSLyKX/arcgis/rest/services/SARCOP_Incident_Feature_Service_v9_Mobile_Editable_View/FeatureServer/1)) y su dominio (`detect`/`confirm`/`remains`/`search`/`ccp`…) mapea casi 1:1 con observación/hecho OpenBREC — excelente vocabulario destino —, pero la escritura exige ArcGIS Online + credenciales NAPSG; export de archivos primero |

## 7. Qué NO se integra y por qué

- **Nada que exija nube en el camino crítico:** SARCOP-write y la API CalTopo Team quedan como exportación diferida "cuando vuelve la red", nunca como dependencia operativa.
- **Nada propietario cerrado sin SDK público vivo:** goTenna.
- **Nada sin API:** Virtual OSOCC/ICMS (intercambio humano por formularios).
- **Ninguna integración que eleve estados de evidencia:** exportar una observación a ATAK/CalTopo/APRS no la convierte en hecho; el ACK de la plataforma externa no confirma persona localizada (invariante transversal, ver guía [Integración con el ecosistema](../guides/ecosystem-integration.md)).

## 8. Relación con los addons

- **`cot-bridge-profile`** (experimental, schemas/addons/1.0.0/): perfil del puente MQTT→CoT de la prioridad 1 — transportes (multicast SA, TCP, TLS), modelado `usericon` + remarks estructurado, dirección y límites (sin elevación de evidencia, provenance declarada). Este documento es su base de diseño; el mapper es trabajo posterior.
- **`interop-emergency-standards-profile`** (existente): queda como el camino CAP/EDXL (prioridad 3), `export_only`, sin gateway; los demás caminos no lo modifican.
