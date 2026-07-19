# Sensing por Wi-Fi CSI y radio-tomografía

## Objetivo

Definir cómo un deployment OpenBREC declara, captura y valida observaciones de radio-tomografía por CSI (channel state information) de Wi-Fi, con estados de evidencia honestos y abstención obligatoria.

## Audiencia

Integradores de sensores, analistas de evidencia y evaluadores que necesiten saber exactamente qué demuestra — y qué no — un enlace CSI.

## Prerrequisitos

Zona/tiempo definidos, baseline de ambiente vacío ejecutada, política de review y retención, transporte máquina disponible y la base citable de evidencia: [estado del arte de RF sensing](../research/rf-sensing-state-of-the-art.md).

## Capacidades necesarias

`Observation` con provenance e incertidumbre, el addon experimental [`csi-link-observation`](../../schemas/addons/1.0.0/csi-link-observation.schema.json), `baseline_ref` obligatoria, `limitations` y `capabilities_absent` declarados, y abstención/`unknown` permitidos. La fusión es determinística y nunca convierte silencio en ausencia.

## Alternativas permitidas

Toolchains comunitarios, todos ejemplos reemplazables y capability-driven (ninguno es requisito de conformidad):

- **ESP32 + esp-csi:** 20 MHz, amplitud-only. La fase queda corrupta por CFO/SFO sin coherencia de reloj; el perfil declara `amplitude_only: true` y AGC gain lock documentado.
- **Nexmon CSI (Raspberry Pi 3B+/4/5):** hasta 80 MHz, más capaz; mismo régimen de baseline y evidencia.
- **Atheros / Intel 5300:** toolchains envejecidos; solo replay académico, no despliegue.
- **RuView** (opcional, version-pinned, reemplazable): proveedor de firmware/streaming/modelos vía el addon `ruview-observation`. Sus salidas son observaciones experimentales con clase `unknown` obligatoria; nunca `victim_detected`. Ver ADR-001 y la evaluación pineada en [docs/legacy/08](../legacy/08-ruview-evaluation.md) `[superseded, fuente]`.

IEEE 802.11bf-2025 (ratificado 2025-09-26) estandariza la sesión de medición/feedback, no algoritmos. Sin silicio comercial, la interoperabilidad cross-vendor es `specified`.

## Componentes e interfaces

Pareja Tx/Rx declarada, canal/ancho de banda (20/40/80 MHz), `antenna_profile_id`, métricas namespaced (`csi.change_score`), `baseline_ref`, adapter que publica observaciones y nunca escribe hechos consolidados. Consts del contrato: `silence_means_absence: false`, `automatic_person_detection_allowed: false`. Evidencia máxima declarable: `bench-validated`.

## Pasos

1. Declarar toolchain, hardware, canal, ancho de banda, geometría y perfil de antena exactos.
2. Ejecutar la **baseline de ambiente vacío** y registrarla como `baseline_ref`; sin baseline no hay observación válida.
3. Capturar y transformar a observaciones con incertidumbre; en ESP32 operar amplitud-only.
4. Separar observación, hipótesis y hecho consolidado; permitir abstención.
5. Combinar con otras modalidades sin convertir la falta de una en evidencia negativa.
6. Validar con el protocolo de la sección siguiente antes de declarar cualquier estado superior a `simulated`.

## Protocolo de validación

Rescatado del plan de validación histórico ([docs/legacy/04](../legacy/04-validacion.md) `[superseded, fuente]`), en vocabulario vigente:

**Etapas (en orden, ninguna salteable):**

1. Cámara o entorno controlado sin escombros.
2. Muros simples de ladrillo, hormigón y metal.
3. Caja de escombros instrumentada con maniquí, dispositivos y actuadores respiratorios.
4. Campo de entrenamiento con operadores ciegos al ground truth.
5. Comparación multimodal con canes, acústica, cámara y radar comercial.

**Métricas:** sensibilidad por tipo de evidencia; falsos positivos por hora; error de zona/posición; tiempo a primer indicio; estabilidad frente a movimiento de rescatistas; robustez tras cambio de antena y geometría; disponibilidad y autonomía; **tasa de abstención correcta**; tiempo de despliegue y carga cognitiva.

**Diseño experimental:** separar entrenamiento y prueba por día, configuración de escombros, operador y posición de nodos. **Prohibido** aceptar resultados basados solo en random split. La transferencia entre entornos es el fallo más documentado de la literatura.

## Resultado esperado

Observaciones CSI explicables, con baseline, abstención visible y un estado de evidencia que la [tabla de la investigación](../research/rf-sensing-state-of-the-art.md) sostiene.

## Validación mínima

Fixtures válidos/inválidos de los addons y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

## Fallos comunes y recuperación

Ante drift o cambio de geometría, rehacer baseline y bajar confianza/abstenerse. Ante AGC no bloqueado o fase inestable, declarar la limitación y operar amplitud-only. Ante modelo que no separa multi-persona, declarar `simulated` con evidencia negativa (39–56 % de separación en commodity) y no ofrecer conteo.

## Safety, privacidad y preservación

El CSI puede observar personas sin su consentimiento y es dual-use (vigilancia encubierta). Se minimiza retención, se registra provenance y se prohibe la detección automática de personas. El dato de producción a escala (92,6 % de accuracy de movimiento en hogares, 8,4 % de falsa alarma no-humana residual) confirma que ni siquiera a escala masiva el silencio o la detección son certeza.

## Estado de evidencia

| Capacidad | Estado |
|---|---|
| Interop cross-vendor (802.11bf) | `specified` |
| Presencia/movimiento (ESP32/Nexmon) | `bench-validated` comunitario |
| Respiración 1 persona LOS estática | `bench-validated` (condiciones ideales) |
| Through-wall / escombros | `simulated` |
| Multi-persona / conteo | `simulated` (evidencia negativa) |
| RTI red dedicada (20–30 nodos) | `bench-validated` (entorno controlado) |
| Uso en rescate real | `unverified` (cero casos documentados) |

Nada en esta guía supera la [tabla de evidencia de la investigación](../research/rf-sensing-state-of-the-art.md).

## Qué no demuestra

Un cambio de canal no demuestra persona, identidad ni vitalidad; el silencio CSI nunca demuestra ausencia. No demuestra conteo, pose, signos vitales ni rendimiento bajo escombros reales.

## Contratos normativos relacionados

Addons experimentales [`csi-link-observation`](../../schemas/addons/1.0.0/csi-link-observation.schema.json) y [`ruview-observation`](../../schemas/addons/1.0.0/ruview-observation.schema.json) ([catálogo de addons](../../schemas/addons/catalog.json)), [Observation](../../schemas/core/1.0.0/observation.schema.json), [Beacons](beacons.md) y [RF quieting](rf-quieting.md) para observaciones tomadas bajo aislamiento.
