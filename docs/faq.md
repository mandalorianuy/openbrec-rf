# Preguntas frecuentes

Respuestas cortas y honestas. Los términos marcados están en el [Glosario](glossary.md); la vista técnica completa en [Arquitectura](architecture.md).

## ¿Esto detecta personas?

No. OpenBREC produce y transporta **indicios con incertidumbre explícita**: observaciones de beacons (acústicos, de movimiento, térmicos) y mensajes de personas. La fusión combina esos indicios con reglas determinísticas y puede **abstenerse** (`unknown`) cuando la evidencia no alcanza. Ningún resultado confirma presencia ni ausencia: el silencio de radio, la falta de movimiento, calor o detección nunca son evidencia de ausencia. Registrar a una persona localizada (`VictimRecord`) es siempre una decisión humana ([Registro de víctimas](guides/victim-tracking.md)).

## ¿Puedo usarlo hoy en un operativo real?

No sin validación física propia. Todo el proyecto está en estado `specified` o `simulated`: la spec está completa (8 / 8 gates) y el pipeline de software corre con datos sintéticos, pero **no existe ninguna validación de banco ni de campo** (P1a 0 / 8, en pausa declarativa). Simulación y CI no acreditan cobertura, autonomía, sensibilidad, seguridad eléctrica ni cumplimiento regulatorio. Para usar una composición en campo haría falta un [evidence pack](evidence-packs/README.md) de esa combinación exacta.

## ¿Qué hardware necesito?

Ninguno para evaluar la spec: contratos, fixtures, replay, gates y el pipeline lab-sim corren offline en una computadora común. Para construir, OpenBREC es **capability-driven**: se compone con el hardware disponible (radios LoRa, SBC, teléfonos, baterías) mediante adapters reemplazables; no exige fabricante, SKU, frecuencia ni topología. Las rutas de solución documentadas son los [reference builds](reference-builds/README.md).

## ¿Por qué ya no Wi-Fi/CSI?

La encarnación previa del proyecto (radio-tomografía Wi-Fi CSI, Kismet, SDR, drones) quedó archivada en [`docs/legacy/`](legacy/README.md) con estado `superseded` y sin autoridad normativa. El proyecto vigente es una Open Spec de comunicaciones, energía y evidencia offline-first; los documentos legacy se conservan sólo como contexto histórico.

## ¿Y el Wi-Fi CSI / los drones / Kismet? ¿Volvieron?

Sí, pero como **addons experimentales**, no como capacidades (ADR-004, 2026-07-19). Los seis dominios de la encarnación previa se reintegraron con contratos propios e invariantes de safety verificables; sus estados de evidencia honestos son:

- **CSI presencia/movimiento y respiración en condiciones ideales:** `bench-validated` comunitario acotado; through-wall/escombros y multi-persona son `simulated` con evidencia negativa (39–56 % de separación en commodity).
- **Metadata pasiva (probes, BT, rtl_433, DroneID):** `bench-validated` comunitaria; Kismet como herramienta SAR es `unverified`.
- **SDR receive-only (406 MHz, DF coherente):** `bench-validated` comunitario; en SAR operacional `unverified`.
- **Drones como geometría de sensing:** `specified`/`simulated`; sin casos SAR documentados para payloads RF abiertos.
- **RF quieting:** `specified` — no existe literatura publicada de aislamiento RF en escena SAR.
- **CSI/Kismet/SDR/RTI en rescate real:** `unverified` (cero casos documentados a 2026-07-19).

Lifeseeker y Wi2SAR **no** son capacidades OpenBREC: son referencias externas con boundary flag (emulación activa, contra las red lines). Guías: [CSI](guides/csi-sensing.md), [RF pasiva](guides/passive-rf.md), [SDR](guides/sdr-beacons.md), [drones](guides/drone-geometry.md), [RF quieting](guides/rf-quieting.md); base citable: [investigación SOTA](research/rf-sensing-state-of-the-art.md).

## ¿Funciona sin internet?

Sí; es el punto del diseño. Todas las funciones críticas — mensajería, energía, beacons, persistencia, replay, federación — operan localmente. La validación del repo también es offline: `uv sync --frozen` una vez con red, y después todos los gates y tests corren con `uv run --offline`. El pipeline lab-sim descarga imágenes Docker pineadas la primera vez y luego funciona sin red.

## ¿Qué pasa con un SOS con firma inválida?

Se preserva para review, nunca se descarta. En BREC la vida viene primero: un posible distress no verificable se conserva como no verificado, con acceso, auditoría, retención y disposición explícitos, y no se eleva a hecho. Un fallo de autenticación tampoco detiene la recepción.

## ¿Un ACK de radio significa que leyeron mi mensaje?

No. El lifecycle de `HumanMessage` distingue creación, aceptación del adapter, transmisión, recepción técnica, visualización y **aceptación operativa**, que es un acto humano. Un ACK técnico no implica lectura, comprensión ni aceptación.

## ¿Necesito un transporte específico? ¿Meshtastic o Reticulum?

Ninguno es obligatorio ni hay ganador universal. Los bearers son reemplazables: Meshtastic, MeshCore, Reticulum/RNode, LoRaWAN privado o carry bundle. La elección depende de topología, densidad, movilidad, energía, seguridad y regulación. Ver [Transportes](guides/transports.md).

## ¿Puedo transmitir por radio con esto?

Sólo dentro de los modos regulatorios normativos: `receive_only`, `conducted_only` o `jurisdiction_validated`. La excepción vital `emergency_assumed_risk` es acotada (doble autorización, parámetros y geografía exactos, expiración, kill switch) y nunca equivale a autorización legal. No hay TX activo en SDR ni funciones ofensivas de radio. La orientación por jurisdicción está en el [Marco regulatorio](guides/regulatory.md) — informativa, no asesoría legal.

## ¿Cómo reporto un problema de seguridad?

Por el canal definido en [SECURITY.md](../SECURITY.md) (GitHub Security Advisories del repositorio). No abras un issue público para vulnerabilidades.

## ¿Cómo contribuyo?

Leé [CONTRIBUTING.md](../CONTRIBUTING.md). En resumen: los cambios normativos exigen nueva versión, fixtures y vectores de compatibilidad; los nuevos adapters nacen `unverified`; la evidencia física se publica separada de la norma; y no se aceptan funciones ofensivas ni claims de evidencia inflados.
