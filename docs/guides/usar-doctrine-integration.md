# Integración con doctrina USAR

## Objetivo

Explicar cómo un deployment OpenBREC se integra a la doctrina real de búsqueda y rescate en estructuras colapsadas (USAR): estructura de mando, plan de comunicaciones, marcación de víctimas, coordinación con otros medios de búsqueda y ciclo operacional.

## Audiencia

Operadores y jefes de equipo USAR, enlaces de comunicaciones del incidente y responsables de introducir OpenBREC en un operativo.

## Prerrequisitos

Doctrina USAR de la organización vigente (ICS/INSARAG o equivalente nacional), un deployment planificado según [Planificación del deployment](deployment-planning.md) y transportes seleccionados con su base regulatoria ([Marco regulatorio](regulatory.md)).

## Capacidades necesarias

Planes humano y máquina operativos, mensajería con prioridades y SOS, persistencia local con replay, y la disciplina de estados de evidencia de la Open Spec. Nada de esto reemplaza la cadena de mando: OpenBREC es una herramienta dentro de ella.

## Alternativas permitidas

La doctrina de marcación y los formularios exactos son configurables por organización: INSARAG, FEMA US&R o equivalentes nacionales. OpenBREC no impone una; las anotaciones del operador se adaptan al sistema de marcación que use el equipo.

## Componentes e interfaces

- **ICS (Incident Command System):** OpenBREC se reporta al mando del incidente como un recurso técnico más. Sus responsables operan bajo la estructura ICS del equipo; el sistema no toma decisiones de mando.
- **Plan de comunicaciones (formulario ICS-205 o equivalente):** cada bearer/canal OpenBREC (plano humano, plano máquina, backhaul de federación) se declara en el plan de comunicaciones del incidente como una línea más, con su función, frecuencia/canal y responsable, igual que cualquier radio convencional.
- **Marcación de víctimas y estructuras:** las anotaciones y marcación INSARAG/FEMA las realiza y confirma un operador humano. OpenBREC las registra y transporta; nunca las genera automáticamente.
- **Coordinación con otros medios:** canes de búsqueda, escucha acústica técnica, cámaras/DVL y acceso físico son medios independientes. OpenBREC aporta indicios que se verifican con esos medios, y recibe de ellos prioridades de sector.

## Ciclo operacional

Adaptado del concepto operacional histórico del proyecto ([documento archivado](../legacy/01-concepto-operacional.md)) al vocabulario vigente de la Open Spec. El stack técnico anterior quedó `superseded`; lo que se conserva es la secuencia doctrinal:

1. **Size-up:** evaluación inicial, definición de sectores y autorización de operación por el mando. Incluye la base regulatoria de los transportes.
2. **Planificación:** sectores, vacíos hipotéticos, roles (operador de red, analista de evidencia, enlace con mando) y plan de comunicaciones ICS-205.
3. **Línea de base:** establecer el estado inicial de la red y del entorno antes de operar (nodos presentes, ruido, cobertura declarada como hipótesis, no como hecho).
4. **Despliegue:** instalación de nodos y ResponseCell según el reference build elegido; registro de geometría y configuración como evidencia.
5. **Operación:** mensajería del plano humano con prioridades y SOS, telemetría del plano máquina, y observaciones de beacons si existen. Todo con timestamps, provenance e incertidumbre.
6. **Fusión y priorización:** la fusión determinística separa observación, hipótesis y hecho consolidado, y puede abstenerse. La priorización de sectores la decide el operador con esa evidencia.
7. **Verificación cruzada:** todo indicio relevante se verifica con medios independientes (canes, acústica, cámara, acceso físico) antes de comprometer recursos de extracción.
8. **Repetición:** tras movimientos de escombros o cambios de fase del operativo, se reevalúa; las particiones se reconcilian por el plano de federación.
9. **Cierre:** exportación del evidence pack del incidente, registro de víctimas confirmado por operador, y purgado de identificadores sensibles según la política de retención.

## Regla de oro

**El silencio de radio o de sensores nunca demuestra ausencia de víctimas.** Ninguna capa del sistema infiere ausencia. La marcación y el registro de víctimas los confirma siempre un operador humano; la convergencia de fuentes independientes eleva prioridad, nunca certeza.

## Pasos

1. Asignar roles del equipo OpenBREC dentro de la estructura ICS del incidente.
2. Incorporar los canales/bearers al plan de comunicaciones ICS-205.
3. Configurar la taxonomía de anotaciones y marcación según la doctrina del equipo (INSARAG/FEMA u otra).
4. Ejecutar el ciclo operacional de la sección anterior en ejercicio antes de un operativo real.
5. Integrar los reportes de OpenBREC al flujo de información del puesto de mando.
6. Documentar lecciones aprendidas como evidencia, sin elevar claims no ensayados.

## Resultado esperado

OpenBREC opera como un medio técnico más dentro de la doctrina del equipo: comunicaciones declaradas en el plan del incidente, evidencia trazable hacia el mando y verificación cruzada obligatoria.

## Validación mínima

Ejercicio de simulacro documentado: ciclo operacional completo con datos sintéticos, replay del incidente desde archivos grabados y revisión de que ninguna inferencia automática marcó víctimas ni ausencias.

## Fallos comunes y recuperación

Ante pérdida del enlace con mando, operar localmente (offline-first) y reconciliar al recuperar federación. Ante saturación del canal, preservar SOS y tráfico humano prioritario. Ante discrepancia entre indicios y medios independientes, prevalece la verificación humana y se registra la discrepancia.

## Safety, privacidad y preservación

Los datos de víctimas y operadores son sensibles: retención limitada, minimización y stripping por defecto. La información vital se preserva y enruta antes que la minimización de privacidad, con control de acceso y auditoría, según la política de la spec.

## Estado de evidencia

La integración doctrinal descrita es `specified` como guía informativa; ningún ejercicio de campo la ha validado (`unverified` hasta que exista un field profile).

## Qué no demuestra

No demuestra interoperabilidad certificada con sistemas de mando de ninguna agencia, ni cumplimiento de requisitos INSARAG/FEMA de clasificación de equipos, ni mejora demostrada en tiempos de localización.

## Contratos normativos relacionados

[Perfiles multi-bearer](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json), [mensajería e interoperabilidad](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json), [Planificación del deployment](deployment-planning.md) y [Marco regulatorio](regulatory.md).
