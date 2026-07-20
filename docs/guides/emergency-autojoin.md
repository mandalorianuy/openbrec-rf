# AP de emergencia con auto-join gobernado

## Objetivo

Definir la excepción gobernada por la cual un AP de emergencia responde a cualquier SSID sondeado por teléfonos cercanos (comportamiento estilo Karma) para convertir el teléfono de una víctima que **no puede actuar** en una baliza acústica/lumínica vía portal cautivo — solo bajo el carril `emergency_assumed_risk`, nunca por defecto.

## Audiencia

Autoridades de incidente, operadores técnicos y responsables legales/privacidad que deban decidir o ejecutar la activación.

## Cuándo aplica

Únicamente cuando hay vida en riesgo y la víctima no puede elegir red ni interactuar (inconsciente, atrapada, sin capacidad de respuesta). Para **detección** pura no hace falta: los probe requests pasivos ya aportan presencia (ver [Observación RF pasiva](passive-rf.md)). El auto-join aporta el **canal**: convertir el teléfono en baliza (sonido, vibración, flash) y entregar un mensaje de emergencia.

## Prerrequisitos

Autoridad de incidente identificada, decisión vital documentada, hardware AP con configuración exacta registrada, y el [Marco regulatorio](regulatory.md) leído: esta es la acción legalmente más delicada del proyecto (interceptación-adyacente: engaño activo al dispositivo).

## Capacidades necesarias

El addon experimental `emergency-autojoin-profile` (schemas/addons/1.0.0/) y el modo regulatorio `emergency_assumed_risk` de la [spec de transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) con **todos** sus requisitos, sin excepción:

- **doble autorización** (dos responsables, registradas);
- **envolvente RF exacta**: canal, potencia, SSID(s) respondidos y geografía (geofence) exactos;
- **monitoreo** continuo de lo que el AP recibe y emite;
- **expiración** automática (TTL corto);
- **stop condition** declarada de antemano;
- **kill switch** local, inmediato y verificable.

`emergency_assumed_risk` **nunca equivale a autorización legal**: registra una decisión vital bajo incertidumbre regulatoria documentada.

## Alternativas permitidas

Antes de activar el auto-join, agotar en orden: observación pasiva de probes (sin TX engañosa), mensajería y balizas propias del despliegue, y los medios de búsqueda de la doctrina. El precedente legítimo de AP de emergencia con portal es Project OWL (ClusterDuck Protocol, open source, desastres: https://github.com/ClusterDuck-Protocol); es referencia de diseño, no validación de eficacia del auto-join.

## Componentes e interfaces

AP de emergencia que responde a cualquier SSID sondeado, portal cautivo **etiquetado visiblemente como emergencia** con el mensaje y las acciones de baliza, registro de la activación (autorizaciones, geofence, expiración) y exclusión de la flota propia por roster. Mecanismo honesto: no existe "push" — iOS/Android detectan el portal sin internet y **lo abren automáticamente**; la página puede emitir sonido (Web Audio), vibración (Vibration API) y flash de pantalla, además del mensaje. En smartwatches el portal casi no funciona.

## Qué no hace

- Sin inspección de contenido del tráfico del dispositivo.
- Sin rerouting ni salida a internet del tráfico del dispositivo.
- Sin captura de credenciales ni formularios de login.
- Sin identificación de personas (ningún dato personal se solicita ni persiste).
- El ACK/apertura del portal **no confirma persona localizada**: es una observación con incertidumbre, nunca un hecho.

## Pasos

1. Confirmar el caso de vida y agotar las alternativas pasivas.
2. Obtener la doble autorización y registrar la decisión con envolvente RF, geografía, expiración y stop condition exactos.
3. Aplicar exclusión de flota: roster de los dispositivos propios y de terceros conocidos en escena.
4. Coordinar con el plan de comunicaciones del incidente (ICS-205; ver [Integración con doctrina USAR](usar-doctrine-integration.md)): el AP puede perturbar redes de la escena.
5. Activar con monitoreo y kill switch al alcance; ventana anunciada.
6. Registrar toda conexión como observación con incertidumbre; verificación humana obligatoria antes de cualquier acción de rescate.
7. Al vencer la expiración o cumplirse la stop condition: kill switch, cierre y registro.

## Resultado esperado

Un canal de baliza/mensaje hacia teléfonos que se unieron solos, gobernado, acotado, monitoreado y registrado, con su incertidumbre intacta.

## Validación mínima

Fixtures válidos/inválidos del addon (rechazo de activación fuera de `emergency_assumed_risk`, de captura de credenciales y de claims de persona localizada) y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

Replay determinístico de la lógica del pipeline (activación gobernada, perfil expirado rechazado, doble autorización, exclusión de flota, ACK del portal no promovido, abstención sin asociaciones):

```bash
uv run --offline python -m openbrec.verify rf-sensing-autojoin
```

## Eficacia honesta y experimento

La eficacia real es **baja y cayendo**: los teléfonos modernos cada vez se auto-unen menos a redes abiertas o imitadas. Estado: `unverified`. Experimento definido para medirla (banco autorizado, nunca en escena): fracción de auto-join y de apertura de portal por generación de OS y fabricante, con dispositivos de laboratorio; publicable como evidence pack acotado.

## Fallos comunes y recuperación

Ante falsos positivos (el equipo propio y terceros en escena también se conectan): exclusión de flota por roster y verificación humana; una conexión no prioriza un sector por sí sola. Ante perturbación de redes de la escena: coordinación ICS previa y abort. Ante smartwatch o dispositivo que no abre el portal: declarar la limitación; no asumir canal establecido.

## Abort criteria

Abortar de inmediato ante: interferencia con comunicaciones de emergencia propias o ajenas, expiración del TTL, cumplimiento de la stop condition, orden de cualquiera de los dos autorizantes, o evidencia de uso fuera de la envolvente registrada. El kill switch es local y no depende de red.

## Safety, privacidad y preservación

Es la acción legalmente más delicada del proyecto: engaño activo a dispositivos ajenos, interceptación-adyacente. Vive del lado de la excepción vital, no del lado pasivo de la línea metadata-vs-contenido ([Recepción pasiva y marco legal](regulatory.md#recepción-pasiva-y-marco-legal)). Minimización total: el portal no pide datos, no persiste identificadores y su etiquetado de emergencia es visible para cualquier persona que lo reciba.

## Estado de evidencia

Contrato y gobernanza: `simulated` — el addon `emergency-autojoin-profile` tiene replay determinístico propio (gate `rf-sensing-autojoin`, receipt en `evidence/rf-sensing/`) que verifica la lógica del pipeline y la gobernanza (doble autorización, expiración, exclusión de flota, ACK no promovido, rechazos visibles). Eficacia del auto-join y del portal como baliza: `unverified` (degradada por OS modernos; sin medición propia ni literatura SAR; la campaña no ejerce ni mide radio). Nada de esta guía promete readiness de campo.

## Qué no demuestra

Una conexión o un ACK de portal no demuestra persona localizada, viva ni consciente; el silencio (ningún dispositivo se une) nunca demuestra ausencia de víctimas. La activación bajo `emergency_assumed_risk` no demuestra autorización legal.

## Contratos normativos relacionados

Addon experimental `emergency-autojoin-profile` en schemas/addons/1.0.0/ ([catálogo de addons](../../schemas/addons/catalog.json)), [perfiles multi-bearer y modos regulatorios](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json) (`emergency_assumed_risk`), [Marco regulatorio](regulatory.md), [Observación RF pasiva](passive-rf.md) y [Integración con doctrina USAR](usar-doctrine-integration.md).
