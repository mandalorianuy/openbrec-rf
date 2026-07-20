# Review de seguridad — AP de emergencia con auto-join (`emergency-autojoin-profile`)

- Fecha: 2026-07-19
- Alcance: addon experimental `emergency-autojoin-profile` (AP estilo Karma con portal cautivo de emergencia; diseño contractual, sin runtime)
- Autoridad: ADR-005, red lines de ADR-0001 y `AGENTS.md`, carril `emergency_assumed_risk` de la spec de transportes, marco legal de `docs/guides/regulatory.md`
- Veredicto: aceptado como diseño `specified` bajo excepción gobernada; eficacia `unverified`; ningún AP queda implementado por esta review

## Alcance

Revisión de diseño del contrato que modela la excepción gobernada por la cual un AP responde a cualquier SSID sondeado para entregar un portal de emergencia (mensaje + baliza acústica/lumínica) a dispositivos de víctimas que no pueden actuar. Es la capacidad legalmente más delicada del proyecto: engaño activo al dispositivo, interceptación-adyacente. Su inclusión es decisión del project owner (ADR-005) como extensión acotada del carril `emergency_assumed_risk`, no como borrado de la línea anti evil-twin.

## Amenazas

| ID | Amenaza | Precondiciones | Impacto |
|---|---|---|---|
| EAJ-T1 | Abuso como evil twin real: la misma técnica (responder a cualquier SSID) se usa para captura, phishing o tracking fuera del caso vital. | Hardware AP disponible; gobernanza omitida o perfil copiado sin las consts. | Daño a terceros, ilicitud, colapso de la confianza en el proyecto. |
| EAJ-T2 | Captura de credenciales por terceros que copien el diseño: el portal publicado sirve de plantilla para un portal falso con login. | Diseño público; ausencia de etiquetado/verificación en la copia. | Compromiso de credenciales de víctimas o terceros; el proyecto queda asociado. |
| EAJ-T3 | Perturbación de redes de la escena: el AP atrae o confunde dispositivos de rescatistas, equipos del incidente o infraestructura sobreviviente. | Activación sin coordinación con el plan de comunicaciones (ICS-205); geofence mal acotado. | Degradación de las comunicaciones de la propia operación de rescate. |
| EAJ-T4 | Falsa confianza por ACK de portal: una apertura de portal se lee como persona localizada, viva o consciente; o un dispositivo de la flota propia se lee como víctima. | UI/fusión que trate la conexión como hecho; exclusión de flota no aplicada. | Desvío de recursos, falsa confirmación life-safety, abandono de otros sectores. |
| EAJ-T5 | Desgaste legal del proyecto: una activación documentada se interpreta como intercepción/suplantación ilegal y contamina jurídicamente todo el repositorio. | Jurisdicción sin excepción de socorro clara; registro incompleto de la gobernanza. | Riesgo legal para operadores y para la continuidad del proyecto. |

## Controles

- **Gobernanza `emergency_assumed_risk` completa, sin atajos**: doble autorización, envolvente RF y geografía exactas (geofence), monitoreo, expiración, stop condition y kill switch local; la activación fuera de ese carril no valida (invariante de contrato).
- **Consts del schema**: sin inspección de contenido, sin rerouting, sin captura de credenciales, sin identificación de personas; el ACK del portal nunca es `person_located`; ningún perfil por defecto incluye el AP.
- **Etiquetado visible del portal como emergencia**: cualquier persona que lo reciba sabe qué es y quién lo opera; reduce la confundibilidad con phishing y documenta la buena fe.
- **Exclusión de flota por roster** y verificación humana obligatoria antes de cualquier acción derivada de una conexión.
- **Coordinación ICS-205** previa a la activación (guía `usar-doctrine-integration.md`): el AP entra al plan de comunicaciones del incidente como emisor declarado.
- **Kill switch local** independiente de red, con abort criteria declarados en la guía (interferencia, expiración, stop condition, orden de cualquiera de los dos autorizantes).
- **Eficacia declarada `unverified`** con experimento de medición definido (fracción de auto-join por generación de OS, banco autorizado): si mide ~0, ADR-005 se revisa y la capacidad se retira.

## Riesgo residual

- La técnica es dual-use por naturaleza: las consts del contrato no impiden que un tercero copie el mecanismo sin la gobernanza; el control real es social/legal, no técnico.
- La eficacia puede ser demasiado baja para justificar el riesgo en escena real; hasta el experimento, toda activación asume esa incertidumbre.
- La interpretación legal de la interceptación-adyacente bajo excepción vital sigue pendiente jurisdicción por jurisdicción; `emergency_assumed_risk` nunca es autorización legal.
- Los falsos positivos (flota propia, terceros) dependen de disciplina de roster bajo estrés: control procedimental, no contractual total.

## Declaración de madurez

Review de **diseño** sobre contrato `specified`; capacidad `unverified` en eficacia y sin runtime. Nada de esta review habilita implementación, hardware ni activación en campo.
