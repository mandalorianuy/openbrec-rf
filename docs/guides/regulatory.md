# Marco regulatorio de RF

## Objetivo

Orientar la selección de bandas, modos de operación y registros regulatorios de un deployment OpenBREC, sin sustituir la validación ante la autoridad regulatoria local.

## Audiencia

Responsables de deployment, operadores técnicos y autoridades de incidente que deban documentar la base regulatoria de las comunicaciones.

## Aviso

Esta guía es **informativa y no constituye asesoría legal**. La normativa de espectro cambia y varía por jurisdicción. Antes de transmitir, el operador debe validar banda, potencia, duty cycle y condiciones de uso con la autoridad regulatoria local o con asesoría competente, y registrar esa validación según el modo `jurisdiction_validated`.

## Prerrequisitos

Jurisdicción(s) de operación identificadas, transportes candidatos según [Transportes](transports.md), y una persona responsable de registrar la base regulatoria.

## Capacidades necesarias

Los cuatro `regulatory_modes` normativos de la Open Spec, un registro por implementación y los perfiles de transporte aplicables. No se requiere hardware para planificar: todo el ejercicio es documental.

## Alternativas permitidas

Los cuatro modos regulatorios definidos en la [spec de transportes multi-bearer](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json):

| Modo | Significado | Registro exigido |
|---|---|---|
| `receive_only` | Sin transmisión RF intencional por este perfil. | Capacidad local y configuración de recepción. |
| `conducted_only` | TX confinada a cable, carga fantasma o recinto blindado medido. | Límite de banco, atenuación y stop condition. |
| `jurisdiction_validated` | La implementación registra su base regulatoria local vigente. | Jurisdicción, revisor, fecha de evidencia y parámetros RF exactos. |
| `emergency_assumed_risk` | Decisión vital acotada y con expiración que acepta incertidumbre regulatoria documentada. | Doble autorización, envolvente RF exacta, geografía, monitoreo, expiración, stop condition y kill switch. |

`emergency_assumed_risk` **nunca equivale a autorización legal**: es un registro de decisión bajo riesgo asumido, no un permiso. El paso 6 de [Transportes](transports.md) describe su uso operativo; esta guía no lo duplica.

## Componentes e interfaces

Registro regulatorio por implementación (jurisdicción, revisor, fecha, parámetros), perfiles de transporte seleccionados, y field profiles cuando exista una validación contextual (hoy no hay ninguno: ver [field profiles](../field-profiles/README.md)).

## Pasos

1. Identificar la jurisdicción de operación y su autoridad de espectro.
2. Para cada transporte candidato, determinar banda, potencia, duty cycle/dwell time y condiciones de la tecnología (p.ej. LoRa/LoRaWAN en bandas ISM/SRD regionales).
3. Verificar cada parámetro con la fuente normativa local vigente; no confiar en documentación de fabricantes ni en esta guía como autoridad.
4. Seleccionar el modo regulatorio aplicable. Preferir `jurisdiction_validated`; usar `receive_only` o `conducted_only` en laboratorio.
5. Completar el registro exigido por el modo: jurisdicción, revisor, fecha de evidencia y parámetros RF exactos.
6. Si una emergencia vital exige operar bajo incertidumbre, aplicar `emergency_assumed_risk` con todos sus elementos (doble autorización, parámetros y geografía exactos, monitoreo, expiración, stop condition, kill switch) y documentar que no es autorización legal.
7. Revalidar el registro ante cambio de jurisdicción, banda, equipo o normativa.

## Marco general de bandas ISM/SRD por región

Conocimiento general estable (los detalles normativos exactos siempre se verifican localmente):

- **EU868 (Europa, ~868 MHz):** banda SRD; LoRaWAN opera típicamente con duty cycle regulatorio del 1 % por sub-banda (marco ETSI EN 300 220 / ERC REC 70-03). El duty cycle limita severamente el airtime de telemetría y downlink.
- **US915 (América, 902–928 MHz):** bajo FCC Part 15 no hay duty cycle regulatorio, pero sí dwell time (típicamente 400 ms) y requisitos de salto de frecuencia. Permite más airtime que EU868.
- **AU915, AS923 y otras regiones:** existen planes regionales de LoRaWAN; cada uno tiene sus propias condiciones de banda. Verificar siempre el plan regional aplicable.
- Los perfiles de transporte de la spec (Meshtastic, MeshCore, Reticulum/RNode, LoRaWAN privado) suelen operar en estas bandas ISM/SRD, pero la configuración exacta de cada dispositivo es responsabilidad del implementador.

## Ejemplos iniciales de jurisdicción

Puntos de partida, no conclusiones. Todo lo específico se marca **verificar con la autoridad local**:

- **Uruguay — URSEC:** autoridad regulatoria de espectro. El proyecto no afirma qué bandas, potencias o licencias aplican; el operador debe consultar las resoluciones vigentes de URSEC antes de transmitir.
- **Argentina — ENACOM:** autoridad regulatoria. Existe marco para dispositivos de baja potencia en bandas libres; los valores exactos de banda y potencia deben verificarse en la normativa ENACOM vigente.
- **España / Unión Europea:** marco común europeo (Directiva RED 2014/53/UE para equipos, ERC REC 70-03 y normas ETSI para uso de espectro SRD). La transposición y condiciones nacionales se verifican con la autoridad de cada Estado miembro.

## Recepción pasiva y marco legal

La línea que gobierna a los colectores OpenBREC es **metadata vs. contenido**: recibir metadata de emisiones ajenas (presencia, tecnología, RSSI, identificadores rotados) es una cosa; interceptar contenido o interactuar activamente con equipos ajenos es otra, y queda fuera de alcance del proyecto.

Referencias de marco (orientación informativa, **verificar con la autoridad local**; esto no es asesoría legal):

- **Estados Unidos:** 18 U.S.C. §2511(2)(g) exceptúa de la prohibición de intercepción las comunicaciones electrónicas "readily accessible to the general public", incluidas las relacionadas con socorro (distress). Texto: https://www.law.cornell.edu/uscode/text/18/2511. La recepción pasiva de metadata se considera de riesgo bajo bajo este marco.
- **Unión Europea:** el GDPR art. 6.1.d admite el tratamiento cuando es necesario para proteger intereses vitales del titular (https://gdpr-info.eu/art-6-gdpr/), base potencial en contexto de rescate. Precedente disuasorio **reportado** (verificar fuente primaria antes de citar como hecho): multa de ~600 000 € al municipio de Enschede (Países Bajos, 2021) por tracking de Wi-Fi de personas en la vía pública (https://autoriteitpersoonsgegevens.nl/).
- **Uruguay:** Constitución art. 28 (inviolabilidad de las comunicaciones; la interceptación del contenido exige orden judicial) y Ley 19.574; el contenido de comunicaciones queda fuera de alcance salvo orden judicial (verificar texto vigente en https://www.impo.com.uy/).
- **Argentina:** verificar con ENACOM y la normativa de protección de datos aplicable; el proyecto no afirma posiciones específicas.

**Regla del proyecto:** todo colector OpenBREC vive del lado pasivo de esa línea. Los contratos lo hacen const: `content_interception: false`, `active_emulation: false`, `payload_retained: false`. Técnicas que la cruzan (emulación de celda ≈ IMSI catcher, AP mimético ≈ evil twin) son referencias externas excluidas, documentadas en [Observación RF pasiva](passive-rf.md).

## Resultado esperado

Un registro regulatorio trazable por implementación, con modo declarado, parámetros exactos y fecha de validación, listo para acompañar un field profile o un evidence pack.

## Validación mínima

Revisión documental del registro contra los `required_record` de la spec; el gate contractual de perfiles de transporte sigue en verde:

```bash
uv run --offline python -m openbrec.verify open-spec-transports
```

## Fallos comunes y recuperación

Ante duda sobre la vigencia normativa, volver a `receive_only` o `conducted_only` hasta validar. Ante cambio de jurisdicción en operación federada, cada celda registra su propia base regulatoria; ninguna validación se hereda entre jurisdicciones. Ante un `emergency_assumed_risk` vencido, detener TX y registrar el cierre.

## Safety, privacidad y preservación

Operar fuera de marco puede interferir servicios de emergencia ajenos y comprometer la operación propia. El registro regulatorio es evidencia auditable: conservarlo con la misma disciplina que cualquier evidencia del incidente.

## Estado de evidencia

Modos regulatorios y registros `specified`. Todo contenido jurisdiccional de esta guía es orientación informativa `unverified` hasta su validación local.

## Qué no demuestra

No demuestra cumplimiento legal, licencia, autorización ni compatibilidad electromagnética de ningún equipo. La ausencia de objeción de una autoridad tampoco constituye permiso.

## Contratos normativos relacionados

[Perfiles multi-bearer y modos regulatorios](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json), [guía de transportes](transports.md) y [field profiles](../field-profiles/README.md).
