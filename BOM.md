# OpenBREC RF — Bill of Materials

Versión 0.2 · 14 de julio de 2026

Esta BoM es escalonada: un equipo puede comenzar con Wi‑Fi/BLE/CSI económico y agregar drones, aislamiento RF, SDR, BFI, UWB o mmWave sin cambiar el núcleo. Los enlaces de Uruguay son publicaciones o búsquedas de disponibilidad; deben confirmarse chipset, conectores, homologación, stock y garantía antes de comprar.

## Compra inicial recomendada

Para el primer banco de pruebas: 6–8 ESP32-S3 con antena externa, un mini PC/Raspberry Pi 5, dos adaptadores Wi‑Fi con monitor mode probado, dos nRF52840, un router OpenWrt, dos RTL-SDR, antenas omni/panel, cable coaxial corto de baja pérdida, energía portátil y cajas IP65. El dron y el kit RF Quieting deben entrar después de obtener baselines estáticos reproducibles.

## Reglas de procurement

- Comprar primero una unidad de cada radio y validar driver, monitor mode, CSI y conectores.
- No asumir que dos productos con el mismo nombre usan el mismo chipset.
- Preferir conectores externos U.FL/IPEX o SMA/RP-SMA documentados.
- Medir pérdida de cable y patrón efectivo; no comprar ganancia extrema sin beamwidth conocido.
- Mantener repuestos de nodos y cables; el hardware de campo es consumible.
- Para drones, cumplir reglamentación UAS, políticas del incidente y procedimientos del operador.
- Para textiles RF, evaluar muestras y costuras antes de comprar superficie completa.

## Nivel MVP

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| Drop node | ESP32 WiFi+BLE board | ESP32-WROOM-32 USB-C | 4 | 10-20 | Use existing | [UY](https://www.mercadolibre.com.uy/wroom32-placa-de-desarrollo-esp32-wifi--bluetooth-usb-c/up/MLUU2820929900?pdp_filters=item_id%3AMLU701714144) | [Oficial/US](https://www.sparkfun.com/sparkfun-thing-plus-esp32-wroom-usb-c.html) | Useful for passive RSSI/BLE and early CSI; not preferred for the final design. |
| Drop node | ESP32-S3 with external antenna | Seeed XIAO ESP32S3 or ESP32-S3 board with U.FL/w.FL | 8 | 8-25 | Recommended | [UY](https://listado.mercadolibre.com.uy/esp32-s3-antena-externa) | [Oficial/US](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) | Preferred low-cost CSI/drop node; buy spares. |
| Gateway | Edge computer | Raspberry Pi 5 8GB or used x86 mini PC | 1 | 100-250 | Required | [UY](https://listado.mercadolibre.com.uy/raspberry-pi-5) | [Oficial/US](https://www.raspberrypi.com/products/raspberry-pi-5/) | A used Intel N100/NUC-class PC may be better when several USB radios are used. |
| Storage | SSD/NVMe | 500GB durable SSD | 1 | 35-70 | Required | [UY](https://listado.mercadolibre.com.uy/ssd-nvme-500gb) | [Oficial/US](https://www.amazon.com/s?k=500gb+nvme+ssd) | Avoid relying on microSD for continuous captures. |
| WiFi capture | USB WiFi radios | 2.4/5GHz adapters with tested Linux monitor mode and external connectors | 2 | 35-100 | Required | [UY](https://listado.mercadolibre.com.uy/adaptador-wifi-monitor-mode-antena-externa) | [Oficial/US](https://www.alfa.com.tw/products/awus036axml) | Validate driver/monitor injection-independent receive performance on the exact kernel. AXML is an advanced tri-band option, not the only choice. |
| BLE/802.15.4 | USB multiprotocol dongle | Nordic nRF52840 Dongle | 2 | 12-20 | Recommended | [UY](https://listado.mercadolibre.com.uy/nrf52840-dongle) | [Oficial/US](https://www.nordicsemi.com/Products/Development-hardware/nRF52840-Dongle) | Supports BLE, Thread, Zigbee/802.15.4 experiments. |
| Network | Portable router/AP | OpenWrt-capable dual-band router | 1 | 50-150 | Required | [UY](https://listado.mercadolibre.com.uy/router-openwrt) | [Oficial/US](https://openwrt.org/toh/start) | Use dedicated rescue SSID and controlled CSI traffic; do not impersonate existing networks. |
| Network | Unmanaged PoE switch | 5-8 port gigabit PoE | 1 | 50-120 | Recommended | [UY](https://listado.mercadolibre.com.uy/switch-poe-gigabit) | [Oficial/US](https://www.amazon.com/s?k=8+port+gigabit+poe+switch) | Ethernet/PoE is preferred for fixed scout nodes. |
| Power | USB-C PD power bank | 20 | 000-30 | 000mAh with 65W output | 3 | [UY](45-100) | [Oficial/US](Required) | https://listado.mercadolibre.com.uy/power-bank-65w-20000mah |
| Mechanical | Weather-resistant project boxes | IP65 plastic non-metallic boxes | 8 | 10-25 | Required | [UY](https://listado.mercadolibre.com.uy/caja-estanca-ip65) | [Oficial/US](https://www.amazon.com/s?k=ip65+plastic+project+box) | Metal boxes require external antennas and careful grounding. |
| Antenna | Omnidirectional WiFi antennas | Matched dual-band 2.4/5GHz 3-5dBi RP-SMA | 8 | 8-20 | Required | [UY](https://listado.mercadolibre.com.uy/antena-wifi-dual-band-rp-sma) | [Oficial/US](https://www.amazon.com/s?k=dual+band+2.4+5ghz+rp-sma+antenna) | Use matched pairs for 2x2 MIMO radios. |
| Antenna | Directional panel/patch | 2.4/5GHz 8-12dBi panel with known beamwidth | 2 | 25-80 | Recommended | [UY](https://listado.mercadolibre.com.uy/antena-panel-wifi-dual-band) | [Oficial/US](https://www.amazon.com/s?k=dual+band+directional+panel+antenna+rp-sma) | Provides sector discrimination; not automatically better than omni. |
| Antenna | Low-loss coax and adapters | LMR-195/LMR-240 short leads + SMA/RP-SMA/U.FL adapters | 1 kit | 50-120 | Required | [UY](https://listado.mercadolibre.com.uy/cable-lmr-240-sma) | [Oficial/US](https://www.amazon.com/s?k=lmr-240+sma+cable+kit) | Measure/record cable loss. Avoid long RG174 runs. |
| Mounting | Tripods and clamps | Camera/light tripods with marked azimuth | 4 | 20-60 | Recommended | [UY](https://listado.mercadolibre.com.uy/tripode-luz-fotografia) | [Oficial/US](https://www.amazon.com/s?k=light+stand+tripod+clamp) | Repeatable orientation is essential for directional scans. |

## Nivel Field

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| Spectrum receiver | Low-cost SDR | RTL-SDR Blog V4 + dipole kit | 2 | 40-60 | Recommended | [UY](https://listado.mercadolibre.com.uy/rtl-sdr-v4) | [Oficial/US](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) | Receive-only spectrum baselines and event detection. |
| Spectrum transceiver | Wideband SDR | HackRF One | 1 | 300-400 | Optional | [UY](https://listado.mercadolibre.com.uy/hackrf-one) | [Oficial/US](https://greatscottgadgets.com/hackrf/one/) | Phase 1 must enforce receive-only. TX requires a separate authorized laboratory procedure. |
| Cyber platform | Multi-radio WiFi appliance | WiFi Pineapple Mark VII | 1 | 120-250 | Optional dev | [UY](https://listado.mercadolibre.com.uy/wifi-pineapple) | [Oficial/US](https://shop.hak5.org/products/wifi-pineapple) | Use only passive recon/telemetry integration. Not fail-safe or suitable as the operational core. Disable offensive modules. |
| Antenna | 2.4GHz biquad antenna | DIY or commercial 8-12dBi biquad | 4 | 10-50 | Research | [UY](https://listado.mercadolibre.com.uy/antena-biquad-2.4ghz) | [Oficial/US](https://www.amazon.com/s?k=2.4ghz+biquad+antenna) | Promising for directional ESP32 CSI links; characterize each build. |
| Antenna | Wideband log-periodic | 400MHz-6GHz SMA antenna | 1 | 50-150 | Recommended | [UY](https://listado.mercadolibre.com.uy/antena-log-periodica-sma) | [Oficial/US](https://www.amazon.com/s?k=log+periodic+antenna+400mhz+6ghz) | Use with SDR for sector scans; gain varies by band. |
| Timing | GNSS receiver with PPS | u-blox-compatible USB/UART GNSS PPS | 2 | 30-100 | Optional | [UY](https://listado.mercadolibre.com.uy/gps-pps-ublox) | [Oficial/US](https://www.sparkfun.com/categories/4) | Useful for clock discipline across separated nodes; PTP over Ethernet may be simpler. |
| Power | Portable LiFePO4 station | 300-700Wh with USB-C/DC/AC | 1 | 300-800 | Recommended | [UY](https://listado.mercadolibre.com.uy/estacion-energia-lifepo4) | [Oficial/US](https://www.amazon.com/s?k=lifepo4+portable+power+station+500wh) | Power gateway, PoE switch and charging during long operations. |
| Mechanical | Rugged transport case | IP67 hard case with foam | 2 | 80-250 | Required | [UY](https://listado.mercadolibre.com.uy/maletin-estanco-rigido) | [Oficial/US](https://www.amazon.com/s?k=ip67+hard+case+foam) | Separate RF kit from batteries and tools. |

## Nivel Advanced

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| WiFi 6E capture | Tri-band 2x2 adapter | ALFA AWUS036AXML | 2 | 100-180 | Experimental | [UY](https://listado.mercadolibre.com.uy/awus036axml) | [Oficial/US](https://www.alfa.com.tw/products/awus036axml) | External RP-SMA antennas; validate monitor mode/BFI capture on Linux before procurement at scale. |
| BFI lab | WiFi 6/6E AP and controlled clients | AP with explicit beamforming + 3-4 Linux clients | 1 set | 600-1500 | Research | [UY](https://listado.mercadolibre.com.uy/router-wifi-6e) | [Oficial/US](https://arxiv.org/abs/2309.04408) | BFI is a lab plugin until cross-environment robustness is demonstrated. |
| UWB | Anchors/tags | DWM3000/DW3000 development boards | 6 | 35-100 | Optional | [UY](https://listado.mercadolibre.com.uy/dwm3000) | [Oficial/US](https://www.qorvo.com/products/p/DWM3000) | Useful for locating OpenBREC nodes/rescuers, not passive victim detection. |
| Presence cross-check | mmWave evaluation kit | TI IWR6843AOP or comparable | 1 | 250-600 | Optional | [UY](https://listado.mercadolibre.com.uy/radar-mmwave) | [Oficial/US](https://www.ti.com/tool/IWR6843AOPEVM) | Independent presence evidence; integration should remain plugin-based. |
| RF switching | Antenna switch matrix | Receive-capable RF switch or HackRF Opera Cake | 1 | 100-250 | Research | [UY](https://listado.mercadolibre.com.uy/rf-switch-sma) | [Oficial/US](https://greatscottgadgets.com/hackrf/operacake/) | Allows repeatable multi-antenna scans; verify isolation and band limits. |
| Compute | AI edge accelerator | Coral USB / Hailo / small NVIDIA device | 1 | 80-700 | Optional | [UY](https://listado.mercadolibre.com.uy/acelerador-ia-usb) | [Oficial/US](https://www.coral.ai/products/accelerator/) | Do not add until CPU baselines and model requirements justify it. |

## Nivel Drone

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| Airframe | Open autopilot development drone | Holybro X500 v2 + Pixhawk 6C/6X or comparable PX4/ArduPilot kit | 1 | 900-1800 | Recommended R&D | [UY](https://listado.mercadolibre.com.uy/pixhawk-drone-kit) | [Oficial/US](https://docs.px4.io/main/en/complete_vehicles/holybro_x500_v2.html) | Open MAVLink integration; validate payload, C.G., flight time and local aviation requirements. |
| Payload release | Servo gripper / release | PWM or MAVLink-controlled normally-locked release with independent mechanical safety | 2 | 25-150 | Required for drop tests | [UY](https://listado.mercadolibre.com.uy/drone-payload-release) | [Oficial/US](https://docs.px4.io/main/en/payloads/gripper.html) | Double-confirm release; bench-test under maximum payload and shock. |
| Payload | OpenBREC Drop Pod enclosure | 3D-printed or molded self-righting IP54/IP65 pod, 150-350g target | 6 | 25-80 | Required | [UY](https://listado.mercadolibre.com.uy/caja-estanca-ip65) | [Oficial/US](https://www.printables.com/search/models?q=self%20righting%20enclosure) | Use non-metallic body, external antenna, impact isolators and visible ID. |
| Localization | Fiducials / UWB for dropped nodes | AprilTag panels plus UWB tags for GNSS-denied localization | 1 kit | 80-450 | Recommended | [UY](https://listado.mercadolibre.com.uy/uwb-dwm3000) | [Oficial/US](https://www.qorvo.com/products/p/DWM3000) | Do not trust consumer GNSS alone near walls and rubble. |
| Industrial option | Heavy-lift/winch drone | DJI FlyCart 30 or locally supported equivalent | 1 | 15000-30000+ | Optional scale | [UY](https://listado.mercadolibre.com.uy/drone-carga-industrial) | [Oficial/US](https://www.dji.com/flycart-30/specs) | For trained/certified teams; separate commercial integration from the open reference airframe. |
| Indoor option | Protected micro/FPV drone | Ducted or full prop-guard platform with low-light camera | 1 | 500-2500 | Optional | [UY](https://listado.mercadolibre.com.uy/drone-fpv-protector-helices) | [Oficial/US](https://www.flyability.com/elios-3) | Reference category only; enclosed void flight remains high risk and may be cost intensive. |

## Nivel RF Quieting

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| Structure | Pop-up frame / large tent | 3x3m non-conductive frame with removable RF curtains | 1 | 150-500 | Research | [UY](https://listado.mercadolibre.com.uy/gazebo-plegable-3x3) | [Oficial/US](https://www.amazon.com/s?k=10x10+pop+up+canopy+frame) | Frame is not shielding; performance depends on fabric, seams and floor. |
| Shielding | RF shielding fabric | Conductive fabric specified for 0.8-6GHz; buy samples before full kit | 35-60 m2 | 15-60/m2 | Research | [UY](https://listado.mercadolibre.com.uy/tela-bloqueo-rf) | [Oficial/US](https://mosequipment.com/products/titanrf-faraday-fabric) | Vendor attenuation claims must be independently measured in the assembled configuration. |
| Seams | Conductive hook/loop, tape and gaskets | Wide overlaps, conductive tape, zipper/gasket samples | 1 kit | 100-400 | Required for enclosure | [UY](https://listado.mercadolibre.com.uy/cinta-cobre-conductiva) | [Oficial/US](https://www.amazon.com/s?k=conductive+fabric+tape+emi+shielding) | Seams and penetrations dominate leakage. |
| Feedthrough | Fiber and filtered power panel | Battery-inside default; optional fiber Ethernet and filtered DC feedthrough | 1 | 100-800 | Recommended | [UY](https://listado.mercadolibre.com.uy/conversor-fibra-ethernet) | [Oficial/US](https://www.amazon.com/s?k=emi+filtered+feedthrough+panel) | Avoid bringing unfiltered copper cables through the enclosure. |
| Reference option | Commercial portable shielded enclosure | Select Fabricators or equivalent measured portable enclosure | 1 | 5000-25000+ | Optional scale | [UY](https://listado.mercadolibre.com.uy/jaula-faraday-tela) | [Oficial/US](https://select-fabricators.com/portable-shielded-enclosures/) | Commercial reference for teams requiring measured attenuation and repeatable seams. |

## Nivel RuView

| Categoría | Componente | Especificación | Cant. | USD unitario | Prioridad | Uruguay | Oficial / US | Notas |
|---|---|---|---:|---:|---|---|---|---|
| CSI integration | RuView-compatible ESP32-S3 nodes | ESP32-S3 with external antenna and ADR-018 compatible firmware | 4-8 | 10-30 | Recommended experiment | [UY](https://listado.mercadolibre.com.uy/esp32-s3-antena-externa) | [Oficial/US](https://github.com/ruvnet/RuView/tree/main/firmware/esp32-csi-node) | Pin firmware version and preserve raw CSI for independent replay. |

## Notas de antenas externas

- **ESP32:** utilizar placas con U.FL/IPEX nativo o variante de módulo prevista para antena externa. No soldar una antena paralela a una PCB antenna sin retirar/seleccionar correctamente el matching RF.
- **MIMO:** conservar pares de antenas equivalentes y separación/orientación documentadas.
- **Coaxial:** mantener los pigtails cortos; LMR-195/240 para recorridos mayores, evitando RG174 largo.
- **Direccionales:** panel, biquad o log-periódica aportan discriminación angular, no una mejora universal. Cada observación debe registrar antena, azimut, elevación y pérdida.
- **Drones:** separar antenas de motores, ESC, GNSS y video; medir el ruido con hélices desmontadas, motores armados y vuelo estacionario.

## Presupuestos orientativos

| Configuración | Rango orientativo | Alcance |
|---|---:|---|
| Banco MVP RF | USD 700–1.500 | Wi‑Fi/BLE/CSI/SDR básico y gateway. |
| Field kit robusto | USD 2.000–5.000 | Más nodos, energía, antenas, cajas y repuestos. |
| Drone open R&D | USD 1.200–3.000 | Airframe PX4/ArduPilot, release y Drop Pods. |
| RF Quieting experimental | USD 1.000–4.000 | Cortinas/paneles, estructura, medición y feedthroughs. |
| Advanced | USD 5.000–20.000+ | Wi‑Fi 6E/BFI, UWB, mmWave, AI edge y mayor instrumentación. |
| Industrial heavy logistics | USD 15.000–30.000+ | Dron de carga/winch y soporte profesional. |
