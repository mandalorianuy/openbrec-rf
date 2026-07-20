# Programa de colaboración institucional — validación física de OpenBREC

- Estado: programa abierto; no implica validación alguna por sí mismo
- Fecha: 2026-07-19
- Audiencia: universidades, laboratorios, institutos de investigación, escuelas de bomberos/defensa civil, clubes de radioaficionados
- Regla central: **la institución mide; el proyecto nunca eleva claims sin el evidence pack.** Todo resultado — incluidos los negativos — se conserva.

## Qué es OpenBREC en 5 líneas

OpenBREC es una Open Spec y plataforma de referencia **offline-first** para operaciones BREC/USAR (búsqueda y rescate en estructuras colapsadas): comunicaciones mesh, energía, sensores y evidencia con provenance que siguen funcionando cuando caen la nube, la red eléctrica y el backhaul. Todo el contenido está hoy en estado `specified` o `simulated`: **no existe validación física todavía** — exactamente el espacio donde una institución puede aportar. OpenBREC produce y transporta indicios; no diagnostica ni garantiza la presencia, ausencia o rescate de una persona: el silencio de radio o de sensores nunca es evidencia de ausencia.

## Por qué es un buen objeto de investigación y enseñanza

- **Spec abierta versionada** (`1.0.0-draft.1`, 8/8 gates) con contratos JSON Schema y fixtures válidos/inválidos: los estudiantes trabajan contra una norma real, no contra un juguete.
- **Simuladores con replay determinístico**: todo el pipeline (observación → MQTT → fusión → PostgreSQL → API → PWA) corre offline en una computadora común; los gates son ejecutables (`uv run --offline python -m openbrec.verify ...`).
- **Estados de evidencia honestos**: el proyecto distingue contractualmente `specified`, `simulated`, `bench-validated`, `field-validated` y `unverified` — un ejercicio de rigor de evidencia en sí mismo.
- **Problemas abiertos reales y delimitados**: el panorama SAR/USAR documentado muestra vacíos concretos (offline-first de escena, provenance con confianza, gestión de autonomía energética) y la tabla de la [investigación SOTA de RF sensing](../research/rf-sensing-state-of-the-art.md) dice, por tecnología, **qué medir para subir de nivel**.
- **Sin dependencias cloud ni costos de licencia**: todo el material es open source y offline-first.

## Qué gana la institución

- Material de cátedra real (contratos, gates, replay, threat model, reviews de seguridad) usable desde el primer día.
- Proyectos de grado y de laboratorio con **criterios objetivos de aceptación** (gates + evidence pack con criterios pass/fail).
- Publicaciones con **evidencia reproducible**: cada pack fija SHA de software, configuración, hardware, entorno, protocolo y datos crudos o sus hashes.
- Coautoría de evidence packs citables publicados en el índice del proyecto.
- Participación en la gobernanza de la spec vía [RFC](../open-spec/RFC-PROCESS.md) y [evidencia comunitaria](../open-spec/COMMUNITY-EVIDENCE.md) (draft → submitted → validated → accepted).
- Un problema de investigación original (lab L7): no existe literatura publicada de aislamiento RF en escenas SAR — quien lo mida primero produce la referencia.

## Qué gana el proyecto

La única cosa que hoy no tiene: **validación física**. Cada lab produce evidencia de la combinación exacta ensayada y eleva su estado — nada más. Los resultados negativos también son válidos y se conservan (`silent_deletion_allowed: false` en la gobernanza): un lab que demuestra que algo no funciona es un aporte, no un fracaso.

## Programa de laboratorios de validación

Ocho labs acotados, ordenados de menor a mayor equipamiento. Los costos y duraciones son **estimaciones** (precios de mercado de referencia a jul-2026; verificar antes de presupuestar). El protocolo de cada lab remite a la guía de dominio que ya define **qué medir**; el lab agrega el rigor de ejecución y el pack. Definition of done común: evidence pack completo según [docs/evidence-packs/README.md](../evidence-packs/README.md), que pase revisión por [COMMUNITY-EVIDENCE](../open-spec/COMMUNITY-EVIDENCE.md), con resultados negativos también válidos.

### L1 — Puente CoT/TAK (demo de integración)

- **Objetivo:** demostrar observaciones OpenBREC visibles en ATAK sin servidor ni internet (UDP multicast SA) y con persistencia vía OpenTAKServer.
- **Valida:** camino de integración #1 ([sar-integration](../research/sar-integration.md)), addon `cot-bridge-profile`; interop ATAK hoy `unverified`.
- **Equipamiento (estimación):** 1 laptop + 1 máquina vieja o Raspberry Pi (~USD 0–80); ATAK-CIV es gratis. Sin compra de hardware de radio.
- **Duración estimada:** 1–2 semanas.
- **Protocolo:** guía [Integración con el ecosistema SAR](../guides/ecosystem-integration.md); gate existente `interop-cot` como base sintética.
- **Produce:** evidence pack de interop ATAK (combinación exacta ATAK-CIV + OpenTAKServer + mapper) → eleva el puente a `bench-validated` para esa combinación.

### L2 — Comunicaciones LoRa en banco

- **Objetivo:** medir alcance, pérdida y latencia del pipeline de mensajería/SOS sobre nodos reales.
- **Valida:** perfiles de transporte y mensajería (hoy `specified`/`simulated`).
- **Equipamiento (estimación):** 2–3 nodos LoRa/Meshtastic (~USD 15–30 c/u), antenas, laptop.
- **Duración estimada:** 2–4 semanas.
- **Protocolo:** guías [Transportes](../guides/transports.md) y [Mensajería y SOS](../guides/messaging-sos.md); medir con replay de duplicados/reordenamiento como referencia sintética.
- **Produce:** evidence pack de enlace y mensajería → `bench-validated` para el set exacto de nodos/canal/región.

### L3 — CSI sensing en banco

- **Objetivo:** reproducir con evidencia propia la detección de presencia/movimiento por amplitud CSI con baseline obligatoria, y la matriz de detección por material de pared.
- **Valida:** `csi-link-observation` (hoy `bench-validated` solo comunitario).
- **Equipamiento (estimación):** 2 ESP32-S3 (~USD 10 c/u), fuentes, muros de prueba (ladrillo/hormigón/madera según disponibilidad).
- **Duración estimada:** 4–8 semanas.
- **Protocolo:** [Sensing por Wi-Fi CSI](../guides/csi-sensing.md) — protocolo de 5 etapas, 9 métricas incluida tasa de abstención correcta, prohibición de random split.
- **Produce:** evidence pack de etapas 1–2 (cámara y muros) → `bench-validated` acotado; etapas 3+ (caja de escombros) como continuación opcional.

### L4 — RF pasiva y offline finding

- **Objetivo:** medir rango y tasa de falsos positivos de la detección pasiva (probes/BT, advertisements Find My `0x12` / Find Hub `0xFEAA`), incluida la exclusión de la flota propia.
- **Valida:** `passive-rf-observation` y `offline-finding-observation` (hoy `bench-validated` comunitario / `specified`).
- **Equipamiento (estimación):** 1–2 ESP32 o nRF52 (~USD 10–25 c/u) + laptop; teléfonos propios como fuentes.
- **Duración estimada:** 2–4 semanas.
- **Protocolo:** guías [Observación RF pasiva](../guides/passive-rf.md) y [Redes de localización crowdsourced](../guides/offline-finding.md); MAC randomization activa como condición de ensayo.
- **Produce:** evidence pack de detección y privacidad (HMAC rotativo, cero payload) → `bench-validated` para la combinación exacta.

### L5 — Recepción SDR de balizas 406 MHz

- **Objetivo:** decodificar tramas Cospas-Sarsat de una baliza de test o simulador de señal y medir tasa de decodificación vs. condiciones.
- **Valida:** `sdr-receive-profile` (decodificación `bench-validated` comunitaria; SAR operacional `unverified`).
- **Equipamiento (estimación):** RTL-SDR Blog V4 (~USD 35–40), antena, baliza de test o generador de señal (bajo `conducted_only` si hay TX de prueba).
- **Duración estimada:** 2–4 semanas.
- **Protocolo:** guía [Recepción SDR de balizas](../guides/sdr-beacons.md).
- **Produce:** evidence pack de decodificación → `bench-validated` para receptor/antena exactos. Extensión opcional: DF con array coherente (KrakenSDR).

### L6 — Energía: claims vs. medición

- **Objetivo:** medir la autonomía real de un build de referencia y compararla con su presupuesto energético declarado.
- **Valida:** perfiles de energía (`energy-budget`, hoy `specified`/`simulated`); ataca el vacío documentado de gestión de autonomía en escena ([sar-landscape §1.5](../research/sar-landscape.md)).
- **Equipamiento (estimación):** multímetro/medidor de consumo (~USD 20–100), el build a medir, cronometraje.
- **Duración estimada:** 2–3 semanas.
- **Protocolo:** guía [Energía](../guides/energy.md); tabla de cargas con suma, pérdidas, margen y reserva verificables.
- **Produce:** evidence pack de autonomía medida → `bench-validated` para el build exacto.

### L7 — RF quieting: el experimento que nadie publicó

- **Objetivo:** primera medición publicada de un conjunto de aislamiento RF armado en contexto SAR simulado: atenuación por banda con incertidumbre, baseline antes/después, y si mejora o no una detección de referencia.
- **Valida:** `rf-isolation-profile` (hoy `specified` — resultado negativo de literatura declarado en la [investigación SOTA §11](../research/rf-sensing-state-of-the-art.md)).
- **Equipamiento (estimación):** kit de paneles conductores o tela Faraday (~USD 100–400 según configuración), SDR + fuente conocida para caracterización (puede compartirse con L5).
- **Duración estimada:** 4–8 semanas.
- **Protocolo:** guía [RF quieting](../guides/rf-quieting.md): escalera de alternativas primero, medición del conjunto armado (nunca dB del vendor), reglas BREC.
- **Produce:** evidence pack con potencial de publicación original → `bench-validated` para el ensamblaje exacto; un resultado negativo (el aislamiento no ayuda) es igual de publicable y se preserva.

### L8 — Comprensión humana del terminal (opcional, ciencias humanas)

- **Objetivo:** ejecutar el protocolo ya diseñado de comprensión y operación del terminal offline con 8 operadores + 8 personas no preparadas.
- **Valida:** la dimensión humana de life-safety (que `accepted` no se lea como rescate garantizado ni el silencio como ausencia); alimenta el carril P1a y los gates de UX.
- **Equipamiento (estimación):** laptops con la PWA, espacio de ensayo, consentimientos — costo marginal; ideal para facultades de psicología, ergonomía o diseño.
- **Duración estimada:** 3–5 semanas (incluida aprobación ética si aplica).
- **Protocolo:** [docs/testing/p1a-terminal-comprehension-protocol.md](../testing/p1a-terminal-comprehension-protocol.md) (tareas, aceptación, stop conditions ya definidos).
- **Produce:** pack de ejecución del protocolo con evidencia de comprensión; no eleva un estado técnico pero desbloquea el carril humano de P1a.

## Cómo contribuir la evidencia

1. Elegir un lab y abrir conversación (issue o RFC `draft` si el protocolo necesita ajuste).
2. Fijar la combinación exacta: spec, SHA de software, hardware, entorno, jurisdicción.
3. Ejecutar el protocolo de la guía de dominio con los gates offline del repo como referencia sintética.
4. Armar el evidence pack según [docs/evidence-packs/README.md](../evidence-packs/README.md): resultados completos, fallos, incertidumbre, criterios pass/fail y "qué no demuestra".
5. Presentarlo por el flujo de [COMMUNITY-EVIDENCE](../open-spec/COMMUNITY-EVIDENCE.md): `submitted` → review de seguridad/privacidad/safety → decisión registrada (`accepted`, `rejected_with_record`, `superseded`).
6. Si `accepted`: el estado de la combinación exacta sube a `bench-validated`/`field-validated` con el pack como respaldo citable y la institución como coautora.

## Gobernanza y contacto

- Cambios a la spec: [proceso RFC](../open-spec/RFC-PROCESS.md) (decisor actual: project owner; disenso preservado append-only).
- Seguridad: [SECURITY.md](../../SECURITY.md) (canal de reporte y tiempos de respuesta).
- Contribuciones generales: [CONTRIBUTING.md](../../CONTRIBUTING.md); repositorio y issues en GitHub (mandalorianuy/openbrec-rf).
- Resumen de una página para circular: [pitch-onepager.md](pitch-onepager.md).
