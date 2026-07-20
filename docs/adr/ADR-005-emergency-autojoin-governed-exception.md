# ADR-005: AP de emergencia con auto-join como excepción gobernada

- Estado: Accepted
- Fecha: 2026-07-19
- Decisor: project owner
- Alcance: addon experimental `emergency-autojoin-profile` (AP estilo Karma que responde a cualquier SSID sondeado, con portal cautivo de emergencia), bajo el carril `emergency_assumed_risk`

## Contexto

El caso que motiva la decisión es de vida: una víctima inconsciente o atrapada **no puede elegir red ni interactuar con su teléfono**. Un AP de emergencia que responde a cualquier SSID sondeado puede hacer que el teléfono se una solo y que el portal cautivo — que iOS/Android abren automáticamente al detectar un portal sin internet — convierta el dispositivo en baliza (sonido vía Web Audio, vibración vía Vibration API, flash de pantalla) y le entregue un mensaje de emergencia. La detección pura no necesita esto (los probe requests pasivos ya bastan, ADR-004); el auto-join aporta el **canal**.

La tensión con las red lines es real y se declara: responder a SSIDs arbitrarios es técnicamente evil-twin-like, y ADR-0001/`AGENTS.md` prohíben suplantación y funciones ofensivas; ADR-004 dejó a Lifeseeker y Wi2SAR fuera del perímetro exactamente por emulación activa engañosa. Además la eficacia real es baja y cayendo (los OS modernos se auto-unen cada vez menos a redes abiertas o imitadas) y es la acción legalmente más delicada del proyecto (interceptación-adyacente).

## Decisión

Se incluye **sólo como excepción gobernada**, nunca por defecto, como extensión del carril `emergency_assumed_risk` ya normativo (`multi-bearer-transport-profiles.json`): no es un borrado de la línea, es una aplicación acotada de una excepción que la spec ya contempla para decisiones vitales con riesgo asumido documentado.

Límites fijados (invariantes de contrato del addon):

- activación únicamente bajo `emergency_assumed_risk` con todos sus requisitos: doble autorización, envolvente RF y geografía exactas (geofence), monitoreo, expiración, stop condition y kill switch;
- portal etiquetado visiblemente como emergencia; sin captura de credenciales, sin inspección de contenido, sin rerouting del tráfico del dispositivo, sin identificación de personas;
- el ACK/apertura del portal nunca es `person_located`: es una observación con incertidumbre y verificación humana obligatoria;
- exclusión de la flota propia por roster y coordinación con el plan de comunicaciones del incidente (ICS-205);
- ningún perfil por defecto: el AP de emergencia no forma parte de ningún reference build ni se activa sin la gobernanza completa.

El mecanismo se documenta honestamente: no existe "push"; el portal lo abre el OS. En smartwatches el portal casi no funciona. La eficacia se declara `unverified` con un experimento definido (fracción de auto-join por generación de OS, en banco autorizado). Precedente legítimo de AP de emergencia con portal: Project OWL (ClusterDuck Protocol, open source). El RFC correspondiente se registra como RFC-0003 bajo `docs/open-spec/rfc/`.

## Consecuencias

- El addon entra como experimental (`status: experimental`, `accepted_at: null`) con fixtures válidos/inválidos que rechazan activación fuera de `emergency_assumed_risk`, captura de credenciales y claims de persona localizada.
- La guía `docs/guides/emergency-autojoin.md`, la review `docs/security/emergency-autojoin-review.md` y las entradas TM-020+ del threat model derivan de esta decisión.
- El perímetro de ADR-004 no cambia: Lifeseeker/Wi2SAR siguen excluidos; el auto-join se distingue de ellos contractualmente (sin captura, sin rerouting, portal etiquetado, gobernanza vital), y esa distinción es la que este ADR fija como revisable.
- El desgaste legal y reputacional del proyecto se acepta como riesgo residual declarado, mitigado por la gobernanza y por la prohibición de perfiles por defecto.

## Criterios de revisión

Revisar —y potencialmente retirar— este ADR si:

- el experimento de eficacia mide auto-join ~0 en las generaciones de OS vigentes (la capacidad dejaría de justificar su riesgo);
- cambia la regulación o la interpretación legal aplicable a la interceptación-adyacente en las jurisdicciones de uso;
- aparece evidencia de abuso del diseño por terceros que lo copien como evil twin real;
- un RFC propio modifica las red lines de ADR-0001 o el carril `emergency_assumed_risk`.
