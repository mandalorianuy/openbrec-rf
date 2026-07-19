# Review de seguridad — RF quieting (`rf-isolation-profile`)

- Fecha: 2026-07-19
- Alcance: addon experimental `rf-isolation-profile` (cortinas/carpas/recintos de atenuación RF en escena; diseño contractual, sin runtime)
- Autoridad: ADR-004, ADR-003 (aislamiento medido, no presumido), red lines de ADR-0001
- Base de evidencia: `docs/research/rf-sensing-state-of-the-art.md` §11 (resultado negativo: sin literatura SAR)
- Veredicto: aceptado como diseño `specified`; ningún claim físico de atenuación queda habilitado

## Alcance

Revisión de diseño del perfil de aislamiento RF. La investigación no encontró literatura publicada de aislamiento RF aplicado a escenas SAR: el dominio nace `specified` con experimento de validación propio definido y ese resultado negativo declarado. El perfil modela el conjunto armado medido por banda, nunca claims nominales de tejido.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| RFQ-T1 | Supresión accidental de comunicaciones de emergencia: la cortina/recinto atenúa el SOS de una víctima, la red del equipo o un canal de mando. | Aislamiento montado sobre un sector con tráfico vital; sin comms independientes; sin baseline. | Pérdida de un distress real (life-safety). |
| RFQ-T2 | Envolver un sector con posible víctima: el aislamiento silencia justo al teléfono que se busca, y el silencio resultante se malinterpreta. | Análisis previo ausente; presión por "probar el sensing". | Búsqueda ciega en el sector aislado. |
| RFQ-T3 | Claim de atenuación no medida: una cifra nominal de tela aplicada al conjunto (costuras, aperturas, suelo, multipath la invalidan — ADR-003). | Documentación o UI que cite atenuación sin medición. | Decisiones operativas sobre una premisa falsa. |
| RFQ-T4 | Dependencia operacional: el equipo pospone la búsqueda hasta "aislar primero". | Procedimiento que ponga el aislamiento como precondición. | Demora life-safety. |
| RFQ-T5 | Seguridad física del recinto: estructura, ventilación, cables y accesos en zona de escombros. | Montaje en escena inestable. | Riesgo físico para rescatistas. |

## Controles

- **Contrato `rf-isolation-profile`**: `measurements` con mínimo una medición por banda con atenuación **e incertidumbre** (sin medición no hay perfil válido); `baseline_before_after_required: true` como const; `never_enclose_possible_victim_sector_without_analysis: true` como const; operador, fecha/ventana anunciada, `config_sha256` y fotos por hash obligatorios.
- **Escalera de alternativas primero** (guía `rf-quieting.md`): canal → potencia → antena → separación → cancelación → cortina → recinto; el aislamiento es la última opción, nunca la primera.
- **Comms de emergencia independientes**: canal de emergencia fuera del volumen aislado y verificado antes de cerrar (ADR-003: uso temporal, canal independiente, prohibición de inferir ausencia).
- **Ventana anunciada y abort criteria**: uso temporal con ventana declarada a mando; criterios de aborto (distress entrante, degradación de comms, cambio de prioridades) en la guía.
- **Silencio ≠ ausencia**: ninguna observación tomada bajo aislamiento puede leerse como sector vacío; `isolation_profile_ref` en `passive-rf-observation` preserva el contexto en provenance.

## Riesgo residual

- El dominio entero es `specified` **sin literatura SAR**: no existe evidencia externa de que el aislamiento en escena aporte más de lo que arriesga; el experimento propio está definido pero no ejecutado.
- Los controles de comms independientes y análisis previo son procedimentales; dependen de disciplina operativa bajo estrés.
- La medición del conjunto (IEEE Std 299 como referencia de método) exige equipamiento y habilidad que el equipo puede no tener en escena.

## Declaración de madurez

Review de **diseño** sobre contrato `specified`, con resultado negativo de búsqueda bibliográfica declarado. No hay evidencia `bench` ni `field` de RF quieting en SAR, propia ni ajena. Nada de esta review habilita montaje, runtime ni campo.
