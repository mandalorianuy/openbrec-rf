# Review de seguridad — sensing por Wi-Fi CSI (`csi-link-observation`, `ruview-observation`)

- Fecha: 2026-07-19
- Alcance: addons experimentales `csi-link-observation` y `ruview-observation` (diseño contractual; sin runtime)
- Autoridad: ADR-004, ADR-001 (RuView), red lines de ADR-0001 y `AGENTS.md`
- Base de evidencia: `docs/research/rf-sensing-state-of-the-art.md` §1–§6 y tabla §14
- Veredicto: aceptado como diseño `specified`/`simulated`; ninguna capacidad CSI operacional queda habilitada

## Alcance

Revisión de diseño de los contratos que modelan observaciones de CSI (pareja Tx/Rx, canal, amplitud, `change_score`, baseline) y las salidas de RuView como proveedor opcional version-pinned. No existe implementación de collector, firmware ni modelo ejecutable en el repositorio: esta review evalúa invariantes de contrato y boundaries, no comportamiento de runtime.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| CSI-T1 | Dual-use como vigilancia: la re-identificación de personas por "huella" de BFI/CSI está demostrada en literatura (KIT 2026 reporta ~99,5 % de re-identificación por patrón corporal, según referencia de la investigación). Un despliegue BREC podría reutilizarse para identificar o trackear personas fuera del incidente. | Collector CSI implementado con fase o features identificables; retención de series temporales; cruce con bases externas. | Vigilancia encubierta, daño a víctimas/rescatistas/terceros, riesgo legal y pérdida de confianza del proyecto. |
| CSI-T2 | Falsa ausencia: silencio de CSI (sin `change_score`) presentado como sector vacío. | UI o fusión que trate ausencia de señal como ausencia de persona; baseline inválida o ausente. | Abandono de un sector con víctima real (life-safety). |
| CSI-T3 | Falsa presencia/automatización: un clasificador (propio o RuView) emite "persona detectada" y desvía recursos. | Salida del modelo promovida a hecho; abstención ausente; claims elevados por encima de la evaluación pineada. | Desvío de recursos, alert fatigue, desconfianza operativa. |
| CSI-T4 | Spoofing físico: movimiento mecánico, ventiladores o maquinaria de rescate generan variación CSI que parece víctima; o un actor genera señal para distraer. | Sensores en entorno no controlado; baseline no actualizada; sin corroboración cruzada. | Candidatos falsos con confianza inflada. |
| CSI-T5 | Transferencia de entorno: modelo entrenado en hogar/lab aplicado a escombros sin revalidación (modo de fallo más documentado en la literatura). | Reuso de pesos/config entre geometrías; random split en evaluación. | Degradación invisible; evidencia negativa conocida (39–56 % de separación multi-persona en commodity). |

## Controles

- **Contrato `csi-link-observation`**: `silence_means_absence: false` y `automatic_person_detection_allowed: false` como consts (un payload que los viole no valida); `max_declared_evidence: bench-validated` como const, por lo que ningún payload puede declarar más que banco; `baseline_ref` obligatoria (línea base de ambiente vacío); `limitations` y `capabilities_absent` obligatorios; `amplitude_only` declarado por hardware (la fase en ESP32 queda corrupta por CFO/SFO — ver guía).
- **Contrato `ruview-observation`**: `experimental_only: true`, `outputs_are_victim_detected: false` y `unknown_class_required: true` como consts; `source_commit` pineado obligatorio y `model_version{hash, commit, format}` (ADR-001: integrar version-pinned, nunca elevar claims por encima de la evaluación pineada `90667d0…`).
- **Fusión y hechos**: los plugins publican observaciones, nunca hechos consolidados; corroboración exige dos sensores de dos tipos; `unknown` ante evidencia insuficiente (pipeline de evidencia del core).
- **Contra el dual-use (CSI-T1)**: el proyecto prohíbe la identificación de personas (red line X-04 de la matriz: biometría/identidad prohibida); el contrato modela `change_score` y métricas namespaced, no embeddings identificables; la prohibición de detección automática de personas es contractual, no sólo editorial. Residual: un implementador externo puede violar el boundary con el mismo hardware — mitigación parcial por licencia, documentación y revisión comunitaria.
- **Protocolo de validación** (guía `csi-sensing.md`, rescatado del legacy): abstención correcta, prohibición de random split, métricas por día/geometría/material.

## Riesgo residual

- La re-identificación por BFI es una propiedad del fenómeno físico, no del contrato: el control es de alcance (amplitude-only, métricas agregadas, prohibición de identificación) y no elimina la superficie si terceros implementan otro pipeline.
- Todo el material de sensores es sintético; los entornos reales de escombro exceden cualquier fixture. La abstención obligatoria contiene el daño pero reduce utilidad.
- RuView es autorreportado (claim "100 % presence" retractado por su autor); el pin contiene el riesgo de deriva, no el de calidad intrínseca.

## Declaración de madurez

Review de **diseño** sobre contratos `specified`/`simulated`. La evidencia externa es `bench-validated` comunitaria acotada (presencia/movimiento, respiración en condiciones ideales), `simulated` con evidencia negativa para through-wall y multi-persona, y `unverified` para uso SAR real (cero casos documentados). Nada de esta review habilita runtime, hardware ni campo.
