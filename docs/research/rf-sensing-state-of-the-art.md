# Estado del arte de RF sensing para BREC/USAR (2023–2026)

- Estado: revisión documental; no autoriza implementación, compra, TX ni selección final de hardware
- Fecha de corte: 2026-07-19
- Alcance: Wi-Fi CSI/radio-tomografía, metadata pasiva, SDR receive-only, drones como geometría de sensing, RF quieting, marco legal y ciberseguridad defensiva
- Condición: este documento es la base citable de los estados de evidencia asignados en las guías de dominio (`csi-sensing`, `passive-rf`, `sdr-beacons`, `drone-geometry`, `rf-quieting`). Ningún claim puede elevarse por encima de esta tabla sin nueva evidencia.

## 1. IEEE 802.11bf (WLAN sensing)

- IEEE 802.11bf-2025 fue ratificado el 26 de septiembre de 2025. Estandariza la sesión de medición y el feedback de sensing; **no** estandariza algoritmos de detección, clasificación ni localización. Fuente: https://standards.ieee.org/ieee/802.11bf/11574/
- Sin silicio comercial disponible a la fecha de corte, la interoperabilidad CSI cross-vendor es `specified`: el contrato puede definirse, pero no hay pares de equipos que lo ejecuten.
- Consecuencia editorial: toda capacidad CSI basada en toolchains actuales se declara por toolchain y configuración exactos, nunca como "Wi-Fi sensing" genérico.

## 2. Toolchains CSI comunitarios

- **ESP32 + esp-csi** (Espressif, activo): CSI a 20 MHz; la fase queda corrupta por CFO/SFO sin coherencia de reloj entre Tx/Rx, por lo que el uso honesto es amplitud-only con AGC gain lock documentado. Fuente: https://github.com/espressif/esp-csi
- **Nexmon CSI** en Raspberry Pi 3B+/4/5: hasta 80 MHz, más capaz que ESP32. Fuente: https://github.com/seemoo-lab/nexmon_csi
- **Atheros CSI tool** e **Intel 5300 CSI tool**: envejecidos (hardware fuera de mercado, mantenimiento mínimo); útiles para replay académico, no como camino de despliegue. Fuente Intel 5300: https://github.com/dhalperi/linux-80211n-csitool
- Presencia/movimiento básico con estos toolchains: `bench-validated` comunitario (reproducido en banco por múltiples grupos; no ensayado por este proyecto).

## 3. Respiración, through-wall y multi-persona

- Respiración por CSI con resolución sub-bpm: reproducible **solo en condiciones ideales** (1 persona, estática, línea de vista, sistema calibrado) → `bench-validated` acotado a esas condiciones.
- Respiración o movimiento through-wall / bajo escombros: sin evidencia de banco pública concluyente en geometrías de escombro → `simulated`.
- Multi-persona / conteo con hardware commodity: `simulated` con **evidencia negativa**: separación de 39–56 % reportada en commodity (arXiv:2601.02177, https://arxiv.org/abs/2601.02177). La transferencia entre entornos es el modo de fallo más documentado.
- Dato de producción a escala (industria, >10 M de routers desplegados): 92,6 % de accuracy de movimiento en hogares reales y reducción de falsas alarmas no-humanas de 63,1 % a 8,4 % residual (arXiv:2506.04322, https://arxiv.org/abs/2506.04322). Lectura para BREC: incluso a escala masiva y en hogares (no escombros), queda un residual de falsa alarma no-humana → refuerza la regla "silencio ≠ ausencia" y la obligación de abstención.

## 4. Radio-tomografía (RTI)

- RTI estilo Patwari: error de localización ~1 m en entornos controlados con redes de 20–30 nodos dedicados → `bench-validated` en esas condiciones. Grupo SPAN, Universidad de Utah: https://span.ece.utah.edu/
- La transferencia entre entornos (reentrenamiento, cambio de geometría o material) es el fallo más documentado; ninguna cifra se traslada a escombros sin ensayo propio.

## 5. Uso de Wi-Fi CSI/RTI en rescate real

- Cero casos documentados de uso de Wi-Fi CSI o RTI en operaciones de rescate reales a la fecha de corte → `unverified` como capacidad operacional USAR. Toda guía del proyecto lo declara así.

## 6. RuView

- RuView (https://github.com/ruvnet/RuView, licencia MIT): claims autorreportados; el propio proyecto retractó una métrica de "100 % presence" y publica una evaluación temporal con 82,3 % held-out. Existe una brecha confirmada entre el formato JSONL del modelo distribuido y el loader RVF del sensing-server (`invalid magic` → salida nula).
- Evaluación del proyecto (commit pineado `90667d0f1d9f4dc129d999c7998d4036cac2e1b8`, 2026-07-14): [`docs/legacy/08-ruview-evaluation.md`](../legacy/08-ruview-evaluation.md) `[superseded, fuente]` y ADR-001.
- Decisión vigente: integrar version-pinned, opcional, reemplazable; sus salidas son observaciones experimentales, nunca `victim_detected`; los claims nunca se elevan por encima de la evaluación pineada.

## 7. Detección pasiva de teléfonos y metadata

- Recepción pasiva de probe requests Wi-Fi y advertisements BLE: `bench-validated`; degradada por MAC randomization (los identificadores rotan y la vinculación temporal es frágil). Nunca se persiste MAC cruda: HMAC rotativo por incidente.
- rtl_433 / rtl_adsb nativos en toolchains de monitoreo actuales amplían las fuentes pasivas (sensores ISM, ADS-B).
- DJI DroneID vía AntSDR: recepción de identificación remota de drones, útil para awareness del espacio aéreo del incidente.
- **Referencias externas con boundary flag (nunca capacidades OpenBREC):**
  - Lifeseeker (CENTUM): emula una celda celular para provocar registro de terminales — funcionalmente comparable a un IMSI catcher.
  - Wi2SAR (artículo ACM MobiCom 2026): AP mimético — comparable a evil twin.
  - Ambos implican transmisión activa engañosa; contradicen las red lines del proyecto (`active_emulation: false`, sin TX activo en la fase inicial) y el marco legal de recepción pasiva. Se citan solo para delimitar el boundary.

## 8. Kismet

- Kismet sigue vivo (release 2025-09-R1) con soporte nativo rtl_433/rtl_adsb, AntSDR DJI DroneID y funciones de alerta tipo SSIDCANARY. Fuentes: https://github.com/kismetwireless/kismet y https://www.kismetwireless.net/
- Como herramienta de rescate: sin casos documentados en SAR → `unverified`. En OpenBREC es un ejemplo reemplazable de collector de metadata pasiva.

## 9. SDR receive-only: 406 MHz y dirección de llegada

- Decodificación de balizas 406 MHz Cospas-Sarsat (ELT/EPIRB/PLB) con SDR: decoder en SDR++ (https://github.com/AlexandreRouma/SDRPlusPlus) y codecs Python comunitarios → `bench-validated`. Sistema Cospas-Sarsat: https://www.cospas-sarsat.int/
- Dirección de llegada (DF) con array coherente: KrakenSDR (5 canales coherentes, 100 MHz–1 GHz, cubre 406 MHz, https://krakensdr.com/) → `bench-validated`, con uso de campo comunitario en foxhunting.
- Doctrina de búsqueda de ELT 121,5/406 MHz: la de organizaciones como Civil Air Patrol (https://www.gocivilairpatrol.com/) e ICAO; el SDR se coordina con esa doctrina, no la reemplaza.
- Cero rescates reales atribuidos a SDR open-source → `unverified` en SAR operacional.

## 10. Drones en USAR

- Cámaras térmicas en drones USAR: `field-validated` (uso operacional consolidado).
- Payloads RF open-source en drones (sensing, relay, scan): `specified`/`simulated`; sin casos SAR documentados.
- Stack abierto maduro: PX4/MAVLink (https://docs.px4.io/main/en/payloads/ y https://docs.px4.io/main/en/flying/package_delivery_mission.html) y ArduPilot grippers (https://ardupilot.org/copter/docs/common-grippers-landingpage.html).
- Regulación: FAA SGI (Special Governmental Interest) y Public Safety Shielded Operations como ejemplo estadounidense (https://www.faa.gov/uas); cada jurisdicción exige verificación local.

## 11. RF quieting / Faraday en escena SAR — resultado negativo

- **Sin literatura publicada** de aislamiento RF (cortinas, carpas, recintos Faraday) aplicado a escenas SAR. El mercado existente es forense/militar.
- Consecuencia: el concepto se declara `specified` con experimento de validación propio definido (medición del conjunto armado por banda, baseline antes/después). No hay claim físico que elevar; el resultado negativo de la búsqueda bibliográfica se declara como tal.
- Referencia de método de medición: IEEE Std 299 (efectividad de blindaje). El material de diseño del proyecto: [`docs/legacy/10-rf-quieting.md`](../legacy/10-rf-quieting.md) `[superseded, fuente]` y ADR-003.

## 12. Marco legal de recepción pasiva

- **Estados Unidos:** 18 U.S.C. §2511(2)(g) exceptúa de la prohibición de intercepción las comunicaciones "readily accessible to the general public", incluidas las de socorro (distress) — texto verificado: https://www.law.cornell.edu/uscode/text/18/2511. La recepción pasiva de metadata es de riesgo bajo; la intercepción de contenido y cualquier suplantación activa quedan fuera de alcance.
- **UE:** GDPR art. 6.1.d (interés vital del titular) como base jurídica potencial en contexto de rescate: https://gdpr-info.eu/art-6-gdpr/. Precedente disuasorio **reportado** (verificar fuente primaria antes de citar como hecho): multa de ~600 000 € al municipio de Enschede (Países Bajos, 2021) por tracking de Wi-Fi de personas en la vía pública (autoridad: https://autoriteitpersoonsgegevens.nl/).
- **Uruguay:** Constitución art. 28 (inviolabilidad de las comunicaciones; solo pueden interceptarse por orden judicial) y Ley 19.574 — el contenido de comunicaciones exige orden judicial; la metadata pasiva es el límite operativo del proyecto (verificar texto vigente en https://www.impo.com.uy/).
- **Argentina:** verificar con ENACOM y normativa de protección de datos aplicable; el proyecto no afirma posiciones específicas.
- Regla del proyecto: todo colector OpenBREC vive del lado pasivo de la línea metadata-vs-contenido.

## 13. Ciberseguridad defensiva del puesto de mando

- Ransomware contra PSAPs/911 documentado (CISA, https://www.cisa.gov/; incidente de Pensacola 2024; threat report del IJIS Institute, https://www.ijis.org/) y ataques TDoS contra líneas 911 (CISA).
- Guías aplicables: FEMA/CISA "Planning Considerations for Cyber Incidents" y recomendaciones SAFECOM/ECPC.
- Consecuencia para OpenBREC: el hardening de la red de comando (segmentación, offline-first, cero dependencia cloud, replay verificable) sigue patrones `field-validated` de la comunidad de seguridad pública, no inventados por el proyecto.

## 14. Tabla de niveles de evidencia por tecnología

| Tecnología | Estado asignado | Base | Qué medir para subir de nivel |
|---|---|---|---|
| Interop CSI cross-vendor (802.11bf) | `specified` | §1: estándar ratificado sin silicio | Interop entre dos vendors con silicio bf real |
| Presencia/movimiento CSI (ESP32, Nexmon) | `bench-validated` (comunitario) | §2 | Replay propio + ensayo en banco del build exacto |
| Respiración CSI 1 persona LOS estática | `bench-validated` (condiciones ideales) | §3 | Ensayo acotado a las condiciones declaradas |
| CSI through-wall / escombros | `simulated` | §3 | Caja de escombros instrumentada con ground truth |
| Conteo/multi-persona CSI | `simulated` (evidencia negativa) | §3 | Nueva evidencia que supere 39–56 % de separación |
| RTI (red dedicada 20–30 nodos) | `bench-validated` (entorno controlado) | §4 | Transferencia a segunda geometría sin reentrenar |
| CSI/RTI en rescate real | `unverified` | §5: cero casos | Un despliegue documentado en ejercicio u operativo |
| RuView como proveedor | `specified` (adapter pineado) | §6, ADR-001 | Gates de replay + evaluación por día/geometría/material |
| Probes/BT pasivos (Kismet u otro) | `bench-validated` | §7–8 | Ensayo propio con MAC randomization activa |
| Kismet como herramienta SAR | `unverified` | §8 | Uso documentado en ejercicio SAR |
| Decodificación 406 MHz (SDR) | `bench-validated` | §9 | Ensayo con baliza de test en banco/campo controlado |
| DF con array coherente (KrakenSDR) | `bench-validated` | §9 | Error angular medido en geometría de incidente |
| SDR open-source en SAR operacional | `unverified` | §9 | Coordinación documentada con doctrina CAP/ICAO |
| Dron USAR con térmica | `field-validated` (externo) | §10 | N/A (capacidad ajena, fuera del core) |
| Payload RF open-source en dron | `specified`/`simulated` | §10 | Drop pod + eventos en ejercicio controlado |
| RF quieting en escena SAR | `specified` (sin literatura) | §11 | Experimento propio: conjunto armado medido por banda |
| Recepción pasiva de metadata (legal) | riesgo bajo (marco citado) | §12 | Revisión legal local por jurisdicción |
| Hardening de red de comando | `field-validated` (patrones ajenos) | §13 | Adopción y verificación en la red propia |
