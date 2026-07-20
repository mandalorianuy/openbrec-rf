# Panorama SAR/USAR 2023–2026 y posicionamiento de OpenBREC

- Estado: revisión documental de fuentes públicas; no autoriza claims de capacidad, compra, TX ni despliegue
- Fecha de corte: 2026-07-19
- Alcance: qué usan hoy los equipos SAR/USAR del mundo (comunicaciones, tracking, detección, coordinación, energía, datos, open source), el vacío resultante y el lugar honesto de OpenBREC
- Base: investigación con ~20 búsquedas web y lectura de fuentes primarias; las debilidades metodológicas se declaran al final
- Relación con otros documentos: complementa la [investigación SOTA de RF sensing](rf-sensing-state-of-the-art.md) (base citable de estados de evidencia por tecnología); este documento es la base citable del posicionamiento

## 1. Qué usa el mundo hoy, por dominio

### 1.1 Comunicaciones en escena

- **Voz LMR domina.** P25 (EE.UU.) y TETRA (Europa/resto del mundo) son los estándares consolidados de seguridad pública; son sistemas de voz con datos muy limitados ([Teltronic, comparativa P25/TETRA](https://www.teltronic.es/en/p25-and-tetra-comparative-analysis-of-the-two-technologies-that-revolutionized-critical-communications/), [Hytera](https://www.hytera.com/en/connect/blog/how-agencies-compare-p25-tetra-dmr-lte-ptt)). Cuando la infraestructura cae, la doctrina es repetidores portátiles, modo directo (talkaround), radioaficionados de apoyo y satelital.
- **Satelital cambió el piso en comando, no en la escena táctica.** Starlink es estándar de facto en respuesta a desastres en EE.UU. (inundaciones Texas Hill Country 2025, con baterías y solar: [Starlink Emergency Response](https://starlink.com/fm/emergency-response), [guía 2025](https://www.starsurf.com/starlink-emergency-disaster-recovery-guide/)); el direct-to-cell (T-Mobile + Starlink, aprobado por FCC 2025) empieza a dar SMS/alertas a teléfonos comunes ([The Silicon Review](https://thesiliconreview.com/2025/03/starlink-direct-cell-approval), [T-Mobile](https://www.t-mobile.com/news/network/how-t-mobile-keeps-people-connected-during-disasters)).
- **Mesh táctico comercial: real pero de élite.** goTenna Pro X2 (~US$849/unidad: [Firehouse](https://www.firehouse.com/technology/mobile-technology-accessories/product/21091795/gotenna-gotenna-releases-gotenna-pro-x-an-open-platform-interoperable-tactical-mesh-networking-device)), Silvus StreamCaster y Persistent Systems MPU5 (miles de USD por nodo) son MANET militar/policial; hay uso en desastres por la Guardia Nacional Aérea de EE.UU. ([Air & Space Forces](https://www.airandspaceforces.com/texas-air-national-guard-tacp-gotenna/)) y demostraciones SAR (Tough Stump Rodeo 2025: [Forterra](https://thelastmile.forterra.com/2025-key-event-recap-mobile-mesh-shines-in-search-and-rescue-demonstrations-at-2025-tough-stump-rodeo/)). Fuera del alcance del equipo SAR típico.
- **LoRa mesh comunitario: evidencia limitada pero real.** La European Cave Rescue Association (ECRA) publicó en 2026 un documento técnico oficial sobre comunicaciones subterráneas con Meshtastic ([ECRA Communications Meshtastic 1.00, PDF](https://caverescue.eu/wp-content/uploads/2026/03/ECRA-Communications-Meshtastic-1.00.pdf)) — la adopción institucional LoRa mesh más fuerte conocida. Hay guías de equipos voluntarios ([getupandgocamping](https://getupandgocamping.com/meshtastic-for-search-and-rescue-emergency-communication-in-the-wilderness/), [resilientcomms.org](https://www.resilientcomms.org/playbooks/volunteer-organization)). **Contrapunto:** análisis técnicos documentan que Meshtastic no es apto para comunicaciones life-safety (sin firma de mensajes, spoofing posible, congestión: [disk91](https://www.disk91.com/2024/technology/lora/critical-analysis-of-the-meshtastic-protocol/), [thecodersblog](https://thecodersblog.com/introduction-to-meshtastic-2026/), [vlad-avramut.com](https://vlad-avramut.com/articles/meshtastic-hardware-stability.html)); el propio proyecto se presenta como "community driven" ([meshtastic.org](https://meshtastic.org/docs/introduction/)).
- La brecha "sin infraestructura" hoy la cubren la voz directa, la radioafición (ARES/RACES, APRS: [ARRL ARES](https://arrl.org/ares), [aprs.world](https://aprs.world/guides/aprs-for-emergency-communications)) y cada vez más Starlink en el puesto de comando. **No hay ningún sistema mesh LoRa institucionalizado en SAR/USAR.**

### 1.2 Localización y tracking de rescatistas

- **TAK/ATAK domina el awareness donde hay datos móviles** (gobierno EE.UU., gratis): plugin SAR oficial 2026 ([civtak.org](https://www.civtak.org/2026/03/23/search-rescue-plugin-released/)), stack gratuito ATAK+UAS Tools+MediaMTX ([HSToday](https://www.hstoday.us/subject-matter-areas/unmanned-vehicles/the-free-drone-tech-stack-changing-public-safety/)), ecosistema open source FreeTAKTeam ([GitHub](https://github.com/FreeTAKTeam/openTAKpickList)); ATAK-CIV es open source gobernado por EE.UU. ([tak.gov](https://tak.gov/pages/sdks), [Hackaday](https://hackaday.com/2022/09/08/the-tak-ecosystem-military-coordination-goes-open-source/)).
- **CalTopo (ex-SARTopo)** es el estándar wilderness en EE.UU./Canadá ([caltopo.com/rescue](https://caltopo.com/rescue), [sartopo.com](https://sartopo.com/about/who-we-are/), [training](https://training.caltopo.com/firstresponse/course)): propietario y dependiente de conectividad para sincronización en vivo. En NZ/Australia existe SARTrack ([hamradio.my](https://hamradio.my/sartrack-from-ham-radio-hobby-to-life-saving-search-and-rescue-command-system/)).
- **GNSS-denied sigue abierto**: NIST PSCR lo lista como desafío activo ([NIST](https://www.nist.gov/ctl/pscr/first-responder-location-and-mapping-services)); TRX Systems NEON (inercial, caro, propietario) fue evaluado por DHS S&T ([docs TRX](https://docs.trxsystems.com/personnel-tracker/), [reporte DHS 2022](https://www.dhs.gov/sites/default/files/2022-02/TRX%20NEON%20Tech%20Demo%20Report_28Feb2022_Final-508.pdf)). En la práctica, la mayoría de los equipos USAR **no tiene** tracking dentro de estructuras: accountability manual (tableros, tags) y voz.

### 1.3 Detección de víctimas

- **Canes: herramienta primaria**, incluso con todos los avances ([Frontiers in Veterinary Science 2025](https://www.frontiersin.org/journals/veterinary-science/articles/10.3389/fvets.2025.1546412/full)).
- **Acústica/sísmica** (Delsar/Savox, Con-Space, Leader): estándar en equipos INSARAG-clasificados y los 28 task forces FEMA ([Savox](https://www.savox.com/products/fire-and-rescue-systems/delsar), [Con-Space](https://www.con-space.com/delsar/delsar-overview/), [Leader](https://www.leader-group.company/en/urban-search-and-rescue-equipment-usar)) — élite, no comunitario.
- **Radar through-wall/UWB**: Camero Xaver ([camero-tech.com](https://camero-tech.com/xaver-products/)), GSSI LifeLocator TRx (respiración hasta ~10 m: [GSSI](https://www.geophysical.com/products/lifelocator-trx)), Leader SCAN. Decenas de miles de USD; equipos pesados solamente.
- **RECCO**: difundido en montaña (pasivo, requiere reflector en la víctima y detector en el rescatista: [GearJunkie](https://gearjunkie.com/outdoor/recco-deep-dive-sar-teams), [recco.com](https://recco.com/technology/)).
- **Búsqueda celular activa (Lifeseeker/Centum)**: convierte el teléfono de la víctima en beacon sin cobertura; >35 usuarios finales, opción de línea Airbus Helicopters 2025, Florida State Guard 2026 ([Centum](https://centum.com/en/products/lifeseeker/), [HeliHub](https://www.helihub.com/2024/06/03/lifeseeker-data-shows-how-sar-uses-phone-signals-to-find-missing-people/), [HeliOps](https://www.heliopsmag.com/heliops/news/centum-announces-lifeseeker-selected-by-airbus-helicopters-as-a-linefit-option/)). Real, de nicho aerotransportado con presupuesto. En OpenBREC es referencia externa con boundary flag (emulación activa), nunca capacidad.
- **Drones**: adopción amplia y creciente ([MDPI Remote Sensing](https://www.mdpi.com/2072-4292/15/13/3266), [Wilderness & Environmental Medicine 2023](https://www.sciencedirect.com/science/article/pii/S1080603223001928)) con escasez de benchmarks ([SAREnv, MDPI Drones 2025](https://www.mdpi.com/2504-446X/9/9/628)).
- **Wi-Fi CSI / RF sensing pasivo**: solo academia y prototipos ([arXiv 2401.01388](https://arxiv.org/html/2401.01388v1), [Nature Sci Rep 2024](https://www.nature.com/articles/s41598-024-54077-x), [ScienceDirect 2023](https://www.sciencedirect.com/science/article/pii/S0952197623013556), prototipo estudiantil [CSI-SAR](https://csi-sar.vercel.app)); **ningún uso operacional conocido** — vacío literal entre academia y campo, coherente con la tabla de la [investigación SOTA de RF sensing](rf-sensing-state-of-the-art.md).

### 1.4 Coordinación y comando

- **INSARAG** define la metodología global: marcación física (spray), señales acústicas, OSOCC/UCC/RDC ([Guidelines Vol. II](https://preparecenter.org/wp-content/uploads/2021/03/INSARAG-Guidelines-V2-Manual-B-Operations.pdf), [ICMS-UCC Guide 2025](https://insarag.org/wp-content/uploads/2025/02/ICMS-UCC-Guide.pdf), [marking annex](https://www.bomberosbogota.gov.co/sites/default/files/documentos/INSARAG%20Guidelines%20Vol%20III%20-%20Annex%20B26%20-%20USAR%20Team%20Marking%20System%20and%20Signalling.pdf)); coordinación internacional por Virtual OSOCC ([vosocc.unocha.org](https://vosocc.unocha.org)).
- **SARCOP** (DHS/FEMA/NAPSG, gratis sobre ArcGIS): el avance real más importante en EE.UU. — 28 task forces, 100+ equipos, 170+ despliegues desde 2021; antes había "cuadernos de papel y planillas" ([DHS S&T 2024](https://www.dhs.gov/science-and-technology/news/2024/09/19/feature-article-sarcop-one-team-one-mission-one-map), [SARCOP Hub](https://sarcop.napsgfoundation.org), [NAPSG PDF](https://www.napsgfoundation.org/wp-content/uploads/2024/02/Pulling-Back-the-SARCOP-Curtain.pdf)). **Depende de ArcGIS y de conectividad**: es la solución "cuando hay nube".
- Wilderness: CalTopo + ICS/NIMS; marítimo: SAROPS (USCG: [USCG](https://www.dcms.uscg.mil/Our-Organization/Assistant-Commandant-for-Acquisitions-CG-9/International-Acquisition/sarops/), [Wikipedia](https://en.wikipedia.org/wiki/Search_and_Rescue_Optimal_Planning_System)).
- Entre agencias y países la realidad sigue mixta: papel, radios, hojas de cálculo y mensajería de consumo (WhatsApp reportado ampliamente, **sin fuente primaria sólida: anecdótico**).

### 1.5 Energía y logística

- Doctrina de **autosuficiencia con cache**: FEMA exige 72 h autosuficientes, operación 24/7, misión de 10–14 días; cache de ~45 t y >US$7M por equipo ([FEMA cache intro](https://www.fema.gov/doc/emergency/usr/task_force_doc_equip_cache_list_intro.doc), [Texas TF-1](https://texastaskforce1.org/1448-no-title/), [INSARAG docs](https://insarag-docs.readthedocs.io/_/downloads/en/latest/pdf/)).
- En la práctica: generadores en el BoO, baterías intercambiables, y cada vez más solar portátil + power stations ([Starlink Emergency Response](https://starlink.com/fm/emergency-response)).
- **Gestión de autonomía energética: vacío no disputado.** No se encontró ningún sistema estandarizado de presupuesto/monitoreo energético a nivel escena; se gestiona por logística humana.

### 1.6 Datos y evidencia

- Los estándares existen — **EDXL** ([OASIS](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=emergency), [Wikipedia](https://en.wikipedia.org/wiki/EDXL)), **CAP** (el más adoptado, en alerta pública), **NIEM** ([niemopen.org](https://niemopen.org)), **HXL**, **HDX** ([data.humdata.org](https://data.humdata.org)) — **pero no llegan a la escena**: la coordinación se hace por Virtual OSOCC + formularios INSARAG y por SARCOP/ArcGIS con esquemas propios. Son "estándares de escritorio", no de escombro.
- **Provenance/evidencia con confianza explícita: vacío transversal.** No existe nada equivalente a observación/hipótesis/hecho separados con fuentes y confianza adjuntas; lo más cercano es la distinción INSARAG "victim confirmed" vs "possible victim" — con spray y papel.

### 1.7 Open source en SAR

- **HOT**: la historia de éxito real, en la capa de mapas ([hotosm.org](https://www.hotosm.org/en/), [OSM wiki](https://wiki.openstreetmap.org/wiki/Humanitarian_OSM_Team)). **Sahana Eden**: gestión de emergencias con despliegues reales, no táctica ([sahanafoundation.org](https://sahanafoundation.org/eden/), [GitHub](https://github.com/sahana/eden)). **Ushahidi**: crowdsourcing de crisis ([ushahidi.com](https://www.ushahidi.com)). **Ecosistema TAK**: FreeTAKServer, CloudTAK ([cloudtak.io](https://cloudtak.io)) — la tracción open source táctica más importante, centrada en EE.UU. y dependiente de servidores.
- **Project OWL** (ganador IBM Call for Code 2018, LoRa "DuckLinks", Linux Foundation: [Linux Foundation](https://www.linuxfoundation.org/press/press-release/the-linux-foundation-open-sources-hardware-of-disaster-relief-project-that-won-first-call-for-code-global-challenge-led-by-ibm), [Wired](https://www.wired.com/story/ibm-call-to-code-winner-clusterducks/)): el precedente más cercano a OpenBREC. **Su tracción post-2020 es dudosa**: poca actividad pública reciente. Advertencia: ganar premios no equivale a adopción operacional.
- **Meshtastic**: la comunidad más viva en LoRa mesh off-grid, sin gobernanza SAR ni garantías de entrega (§1.1).

## 2. El vacío

No existe hoy un sistema que combine:

1. **Offline-first real a nivel escena táctica** (SARCOP, CalTopo, TAK y Sahana asumen sincronización con nube/servidor en algún punto; el mesh comercial asume hardware de US$850–5000/nodo).
2. **Hardware abierto barato** (goTenna/Silvus/NEON/Xaver/LifeLocator: propietarios y caros; Meshtastic: barato pero sin garantías ni capa de evidencia).
3. **Interoperabilidad por contratos** (EDXL/NIEM no llegan a la escena; SARCOP es monocultura ArcGIS; INSARAG interopera con papel y spray).
4. **Evidencia con provenance y confianza explícita** (nadie lo hace; vacío transversal genuino).
5. **Privacidad por diseño** (la búsqueda celular activa va en la dirección contraria; los sistemas gubernamentales recopilan centralmente).
6. **Honestidad de claims** (el marketing de radar through-wall y de mesh táctico sobre-promete sistemáticamente; la academia de Wi-Fi sensing reporta resultados que no se transfieren a campo — generalización cross-environment abierta: [Springer 2024](https://link.springer.com/chapter/10.1007/978-3-031-78354-8_13)).

## 3. Dónde encaja OpenBREC

Como **capa de respaldo e interoperabilidad de escena, no como competidor**:

- **Fallback:** cuando no hay ArcGIS/cloud/satélite (o fallaron), una capa mesh con contratos y evidencia sigue funcionando — el rol de "cuando todo lo demás falla" que hoy ocupan la radioafición y el papel.
- **Complemento:** exportar observaciones con provenance hacia SARCOP/TAK/Virtual OSOCC, no reemplazarlos.
- **Nicho realista:** equipos voluntarios, brigadas comunitarias y países sin task forces tipo FEMA (mantener un solo task force cuesta ~US$2.4M/año: [CFSI appropriations](https://cfsi.org/wp-content/uploads/2026/05/USAR-Appropriations.pdf)). Es el nicho menos disputado.
- **Lugar honesto para RF sensing:** observación de baja confianza dentro del pipeline de evidencia (observación ≠ hecho), nunca "detector de víctimas"; coherente con la regla del proyecto de no inferir ausencia por silencio RF.

## 4. Mapeo a capacidades del proyecto

| Vacío / necesidad del panorama | Pieza OpenBREC que responde |
|---|---|
| Sin mesh institucionalizado ni garantías sobre LoRa comunitario | Overlay OpenBREC con envelopes firmados, prioridad SOS, dedup y anti-loop sobre bearers reemplazables ([perfiles multi-bearer](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json), guía [Transportes](../guides/transports.md)); Meshtastic es un bearer, nunca "la red" ni una garantía |
| Accountability manual y sin awareness offline | Plano humano con mensajería/SOS y GIS offline (`offline-mapping-profile`, guía [GIS offline](../guides/offline-mapping.md)) |
| Estándares que no llegan a la escena | Contratos abiertos versionados + perfil de interop EDXL/CAP (`interop-emergency-standards-profile`, guía [Interoperación CAP/EDXL](../guides/interop-emergency-standards.md)) como puente de exportación |
| Sin provenance ni confianza explícita | Pipeline observación/hipótesis/hecho con estados de evidencia, provenance obligatoria, registro de víctimas solo por operador (`victim-record`, guía [Registro de víctimas](../guides/victim-tracking.md)), evidence packs |
| Gestión de autonomía energética inexistente | Perfiles y presupuestos de energía (`energy-budget`, guía [Energía](../guides/energy.md)) |
| RF sensing entre academia y campo | Addons experimentales con invariantes y estados honestos (ADR-004; guías de dominio; [SOTA RF sensing](rf-sensing-state-of-the-art.md)) y la excepción gobernada `emergency-autojoin-profile` (ADR-005) |
| Coordinación particionada entre celdas/organizaciones | Federación eventual con reconciliación append-only (guía [Federación](../guides/federation.md)) |

## 5. Barreras de adopción reales

Por qué un equipo USAR clasificado **no** usaría OpenBREC hoy:

1. **Doctrina y certificación:** INSARAG IEC/IER ([insarag.org/iec](https://insarag.org/iec/background-of-insarag-external-classification-iec/), [OCHA overview](https://www.unocha.org/publications/report/world/insarag-external-classification-iec-overview-snapshot-1-december-2023)) y FEMA US&R se ganan con equipo y procesos aprobados; un sistema no certificado no entra al checklist ni a la cadena de mando.
2. **Confianza y liability:** nadie arriesga una operación de vida o muerte en hardware de US$30 sin validación de campo publicada; el propio ecosistema Meshtastic reconoce no ser apto para life-safety (§1.1). OpenBREC hereda ese escepticismo hasta tener evidence packs de despliegues reales.
3. **El presupuesto no es el problema de la élite:** FEMA da ~US$1.2M/año por task force ([CFSI](https://cfsi.org/wp-content/uploads/2026/05/USAR-Appropriations.pdf)); les falta confiabilidad, capacitación e integración con SARCOP/TAK, no hardware barato. El argumento de costo solo aplica al nicho voluntario/comunitario/países en desarrollo.
4. **SARCOP y TAK ya cubrieron el common operating picture donde hay conectividad**, gratis y con respaldo institucional; el espacio de OpenBREC es exactamente donde esos sistemas se apagan.
5. **Regulación de RF:** duty cycle LoRa (1 % en EU868) capa el tráfico; cualquier RF sensing activo exige coordinación de espectro — coherente con la regla del proyecto de no TX activo en SDR y con el [marco regulatorio](../guides/regulatory.md).
6. **La lección Project OWL:** idea casi idéntica (mesh LoRa para desastre), premio global, sin tracción operacional sostenida. La adopción la da la doctrina y la comunidad de práctica, no la tecnología.

## 6. Qué tendría que pasar para que un equipo real lo adopte

1. **Evidence packs de despliegues reales** (ejercicios primero): la trayectoria P1a de banco → campo sigue siendo el único camino que eleva claims (hoy todo es `specified`/`simulated`).
2. **Validación comunitaria de los addons experimentales** vía [`docs/open-spec/COMMUNITY-EVIDENCE.md`](../open-spec/COMMUNITY-EVIDENCE.md): review y evidencia de terceros antes de cualquier promoción.
3. **Exportación real hacia el ecosistema existente:** conectores documentados a CAP/EDXL y a SARCOP/TAK/Virtual OSOCC (el perfil de interop hoy es `specified`, sin gateway implementado).
4. **Una comunidad de práctica, no solo código:** ejercicios con equipos voluntarios del nicho realista, SOPs, formación y feedback incorporado por RFC — la variable que decidió el destino de Project OWL.

## 7. Notas metodológicas y debilidades

- El PDF de la ECRA sobre Meshtastic no pudo leerse completo; su descripción proviene del snippet del buscador.
- No hay fuente primaria sólida sobre uso de WhatsApp/apps de consumo en coordinación USAR internacional: marcado como anecdótico.
- Los datos de ventas/despliegues de goTenna, Silvus, Camero y Lifeseeker provienen en gran parte de marketing del fabricante: claims no auditados.
- No hay estudios cuantitativos de penetración tecnológica en equipos USAR fuera de EE.UU./Europa; la evidencia "típico vs élite" en América Latina, África y Asia es indirecta.
