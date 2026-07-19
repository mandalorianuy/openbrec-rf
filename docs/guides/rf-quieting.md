# RF quieting: aislamiento medido para mediciones específicas

## Objetivo

Reducir interferencia externa o separar emisiones propias durante una medición acotada, con el aislamiento siempre medido sobre el conjunto armado y bajo reglas BREC explícitas. Nunca se usa para afirmar ausencia de víctimas ni para bloquear comunicaciones de forma prolongada.

## Audiencia

Operadores técnicos de RF, responsables de calibración y planificadores del deployment.

## Prerrequisitos

Una medición concreta que lo justifique, ventana anunciada, kit de caracterización (SDR + fuente conocida) y la [base citable de evidencia](../research/rf-sensing-state-of-the-art.md). Material de diseño: [docs/legacy/10](../legacy/10-rf-quieting.md) `[superseded, fuente]`, [hardware/rf-quiet-kit.md](../../hardware/rf-quiet-kit.md) y ADR-003 (aislamiento medido, no presumido).

## Capacidades necesarias

El addon experimental [`rf-isolation-profile`](../../schemas/addons/1.0.0/rf-isolation-profile.schema.json): mediciones por banda con atenuación e incertidumbre (mínimo una), operador, fecha/ventana, hash de configuración y fotos por hash. Consts: `baseline_before_after_required: true` y `never_enclose_possible_victim_sector_without_analysis: true`.

## Escalera de alternativas (antes de aislar)

El aislamiento físico es la **última** opción. En orden de preferencia:

1. **Selección de canal:** mover el enlace propio a un canal limpio.
2. **Reducción de potencia:** bajar TX al mínimo funcional.
3. **Antena direccional:** rechazar la fuente interferente por geometría.
4. **Separación física:** alejar equipos o reubicar la medición.
5. **Cancelación por referencia:** restar la interferencia conocida en procesamiento.
6. **Cortina sectorial:** paneles conductores entre la fuente dominante y el sector (primera opción física: liviana, mantiene acceso, permite comparar orientaciones).
7. **Carpa parcial / recinto completo:** solo para calibración o laboratorio; montaje y medición exigentes.

## Componentes e interfaces

Kit de paneles conductores modulares (solape mínimo 200 mm, cintas/gaskets conductivas, entrada por fibra, alimentación por baterías internas), kit SDR + fuente conocida para caracterización, y el `IsolationProfile` como registro: banda/frecuencia, atenuación mediana y percentiles, posición Tx/Rx, polarización, costuras, piso y feedthrough, fotos y hash de configuración, fecha y operador.

## Pasos

1. Agotar la escalera de alternativas y documentar por qué no bastan.
2. Anunciar la ventana de quieting al mando y a los equipos.
3. Medir baseline **antes** de armar.
4. Armar la configuración y medirla como conjunto, por banda: **ningún dB se declara del tejido del vendor**; costuras, aperturas, suelo y multipath invalidan cifras nominales aplicadas al conjunto (ADR-003, IEEE Std 299 como método).
5. Registrar el `IsolationProfile` con su hash de configuración.
6. Ejecutar la medición objetivo; toda observación RF tomada bajo aislamiento registra `isolation_profile_ref`.
7. Desarmar, medir baseline **después** y comparar.
8. Abortar si el aislamiento interfiere la coordinación o dispositivos críticos.

## Reglas BREC

- Mantener comunicación de emergencia **independiente** del volumen aislado.
- Anunciar la ventana de quieting.
- Baseline antes y después, obligatoria (const del contrato).
- **Nunca envolver un sector con posible víctima sin análisis de impacto** (const del contrato).
- Toda observación RF bajo aislamiento referencia su `isolation_profile_ref`.
- Uso temporal; nunca bloqueo prolongado de comunicaciones.

## Resultado esperado

Mediciones con interferencia controlada y un registro de aislamiento medido, reproducible y auditable, sin ningún claim nominal no medido.

## Validación mínima

Fixtures válidos/inválidos del addon (rechazo de perfiles sin mediciones o sin baseline) y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

## Fallos comunes y recuperación

Ante atenuación menor a la esperada, revisar costuras, solapes y feedthroughs antes de culpar al material; corregir y remedir. Ante cambio de configuración, nuevo hash y nueva medición: un profile no cubre variantes no medidas. Ante imposibilidad de medir el conjunto, no declarar aislamiento: declarar `unverified`.

## Safety, privacidad y preservación

El aislamiento puede degradar comunicaciones ajenas y propias, incluidas las de emergencia: de ahí el canal independiente, la ventana anunciada y el abort. Nunca se infiere ausencia de víctima por silencio dentro o fuera del volumen aislado.

## Estado de evidencia

**Sin precedente SAR publicado**: no existe literatura de aislamiento RF en escenas de búsqueda y rescate; el mercado es forense/militar. El concepto completo es `specified` con un experimento de validación propio definido (conjunto armado medido por banda, baseline antes/después). Todo claim físico es `unverified` hasta ese experimento. Este resultado negativo de la búsqueda se declara como tal.

## Qué no demuestra

Una atenuación medida en una banda y configuración no demuestra atenuación en otra banda, otra geometría u otro montaje. El aislamiento no demuestra nada sobre presencia o ausencia de víctimas.

## Contratos normativos relacionados

Addon experimental [`rf-isolation-profile`](../../schemas/addons/1.0.0/rf-isolation-profile.schema.json) ([catálogo de addons](../../schemas/addons/catalog.json)), [hardware/rf-quiet-kit.md](../../hardware/rf-quiet-kit.md), ADR-003 en [docs/adr](../adr/ADR-003-measured-rf-quieting.md), [Observación RF pasiva](passive-rf.md) y [Marco regulatorio](regulatory.md).
