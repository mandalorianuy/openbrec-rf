# Roadmap — OpenBREC RF

**Última actualización: 2026-07-20.** Este es el roadmap vigente del proyecto.
El roadmap de la encarnación previa (Wi-Fi-CSI) quedó archivado en
[`docs/legacy/06-roadmap.md`](docs/legacy/06-roadmap.md) y no tiene autoridad.
[`DELIVERY_BOARD.md`](DELIVERY_BOARD.md) se conserva como audit trail
histórico de la ejecución M0/P0/Open Spec.

## Estado actual

- **Open Spec `1.0.0-draft.1` completa: 8 / 8 gates** (energía, transportes,
  mensajería/SOS, beacons, federación, builds, evidence packs y validación
  documental), verificable offline con `uv run --offline python -m openbrec.verify open-spec`.
- **Todo el contenido normativo está en estado `specified` o `simulated`.**
  No existe validación física (`bench-validated` / `field-validated`) de
  ningún componente.
- **P1a (evidencia física de banco): 0 / 8, en pausa declarativa.** No se
  aceptan cambios de gates P1a hasta que exista hardware real disponible.
- El sistema de referencia (API, worker, PWA) corre local con datos
  sintéticos y funciona end-to-end en lab-sim: observación → MQTT →
  worker → fusión determinística → PostgreSQL → API de lectura → PWA
  (ver `docs/guides/quickstart-offgrid.md`).

## Fases ejecutadas

1. **Fase 0 — Reconciliación del repo (hecha, 2026-07-19).** La encarnación
   Wi-Fi-CSI previa quedó archivada en `docs/legacy/` con banners de
   `superseded`; este roadmap reemplaza al histórico.
2. **Fase 1 — Deuda técnica y tooling (hecha, 2026-07-19).** Tests robustos
   al entorno (skips explícitos), pinning de dependencias de la PWA,
   alineación de migraciones SQL, guard del derivador de claves simulado y
   canal de reporte en `SECURITY.md`.
3. **Fase 2 — Pipeline software end-to-end (hecha, 2026-07-19).** Conectado
   observación → MQTT → worker → fusión determinística → Postgres → API de
   lectura → PWA, todo con datos sintéticos y tests de integración locales.
4. **Fase 3 — Extensiones de spec (hecha, 2026-07-19).** Addons
   experimentales en estado `specified`: registro de víctima/triage
   confirmado por operador, interop EDXL/CAP, GIS offline, ciclo de vida de
   claves offline, disciplina de reloj; más guías regulatoria y de doctrina
   USAR.
5. **Fase 4 — Documentación humana (hecha, 2026-07-19).** README como portada
   real, `START_HERE` por rol, arquitectura unificada, guía de implementación
   de la spec, FAQ, glosario y `CONTRIBUTING` alineado a la maquinaria
   actual.
6. **Fase 5 — Gobernanza abierta ligera y cierre (hecha, 2026-07-19).**
   Proceso RFC mínimo para la spec (`docs/open-spec/RFC-PROCESS.md`) y
   barrido final de consistencia.
7. **Fase 6 — Reintegración de RF sensing como addons (hecha, 2026-07-19).**
   Los dominios de la encarnación previa (CSI, metadata pasiva, SDR
   receive-only, drones como geometría, RF quieting, RuView) vuelven como seis
   addons experimentales (29 totales) con invariantes de safety como consts,
   guías de dominio, investigación SOTA citable
   (`docs/research/rf-sensing-state-of-the-art.md`), ADR-004, cinco reviews de
   seguridad de diseño y el primer RFC de la spec
   (`docs/open-spec/rfc/0001-rf-sensing-addons.md`, `accepted`). Lifeseeker y
   Wi2SAR quedan fuera del perímetro como referencias externas con boundary
   flag. Los estados de evidencia se asignaron sin elevar claims: CSI/Kismet/
   SDR en SAR real son `unverified`; RF quieting es `specified` sin literatura.
8. **Fase 7 — Simuladores de replay RF y offline finding (hecha, 2026-07-19).**
   Simuladores determinísticos de replay (`openbrec/rf_sensing.py`, fixtures en
   `fixtures/replay/rf-sensing/`) que elevan `csi-link-observation`,
   `passive-rf-observation` y `offline-finding-observation` de `specified` a
   `simulated` (gates `rf-sensing-csi/-passive/-multimodal/-offline-finding`),
   verificando como invariantes el silencio≠ausencia, la abstención, la
   corroboración solo multi-modal y la privacidad (HMAC rotativo, cero payload).
   Gate `ruview-model-format` (fallback visible, nunca null silencioso). Nuevo
   addon `offline-finding-observation` (30 totales, RFC-0002 `accepted`):
   detección pasiva de redes crowdsourced (Apple Find My, Google Find Hub,
   Samsung) como indicio débil, con guía `docs/guides/offline-finding.md`.
9. **Fase 8 — AP de emergencia con auto-join gobernado (hecha, 2026-07-19).**
   Nuevo addon `emergency-autojoin-profile` (RFC-0003): AP estilo Karma que
   responde a cualquier SSID sondeado para convertir el teléfono de una víctima
   que no puede actuar en baliza vía portal cautivo. Incluido **sólo como
   excepción gobernada** bajo `emergency_assumed_risk` (ADR-005), nunca por
   defecto: doble autorización, geofence, expiración, kill switch; sin captura,
   sin rerouting, sin inspección de contenido; el ACK del portal nunca es
   persona localizada. Eficacia declarada `unverified` (degradada por OS
   modernos) con experimento de medición definido. Guía
   `docs/guides/emergency-autojoin.md`, review
   `docs/security/emergency-autojoin-review.md`, TM-020..TM-022.
10. **Fase 9 — Integración con el ecosistema SAR (hecha, 2026-07-19/20).**
    Posicionamiento (`docs/research/sar-landscape.md`) y arquitectura de
    integración priorizada (`docs/research/sar-integration.md`: puente CoT/TAK
    local #1, Meshtastic MQTT #2, export CAP/EDXL #3, CalTopo #4, APRS
    opcional; goTenna/Virtual OSOCC descartados con razón). Nuevo addon
    `cot-bridge-profile` (32 totales, RFC-0004 `accepted`) con mapper CoT
    lab-sim y gate `interop-cot`, que lo eleva a `simulated`; la interop ATAK
    real sigue `unverified`. Guía `docs/guides/ecosystem-integration.md`.
11. **Fase 10 — Colaboración institucional y onboarding (hecha, 2026-07-20).**
    Programa de validación física con universidades e instituciones:
    `docs/outreach/institutional-collaboration.md` (8 labs con protocolo,
    costos estimados y DoD: evidence pack por COMMUNITY-EVIDENCE, resultados
    negativos válidos) y `docs/outreach/pitch-onepager.md`. Onboarding
    individual revisado: START_HERE cubre los perfiles; se agregaron entradas
    a quickstart, ayuda/contribución e instituciones.

## Siguiente

- **Adopción vía labs institucionales:** `docs/outreach/institutional-collaboration.md`
  (programa de 8 labs de validación física para universidades, laboratorios,
  escuelas de bomberos/defensa civil y clubes de radioaficionados) y
  `docs/outreach/pitch-onepager.md`; es el camino activo para conseguir los
  evidence packs que el proyecto no puede producir solo.

- **Evidencia física P1a:** permanece en pausa declarativa; se retoma cuando
  exista hardware real disponible y autoridad para operarlo.
- **Validación comunitaria de addons:** los catorce addons experimentales de
  las Fases 3 y 6–9 esperan review y evidencia de terceros vía
  `docs/open-spec/COMMUNITY-EVIDENCE.md` antes de cualquier promoción.
- **Experimentos de evidencia por dominio RF:** banco CSI del build exacto,
  ensayo con MAC randomization activa, baliza 406 MHz de test, drop pod en
  ejercicio controlado y experimento propio de RF quieting — todos requieren
  autorización física propia y quedan fuera del carril software.
- **Más adapters y transportes:** nuevos perfiles reemplazables según el
  flujo de `CONTRIBUTING.md`, siempre sin convertir referencias en norma.

## Qué entra y qué sale del roadmap

**Entra:** trabajo ejecutable sin hardware externo — spec, schemas, fixtures,
simulación, software local del repo (API/worker/PWA) y documentación — que
mantenga la honestidad de evidencia (ningún claim por encima de `specified` /
`simulated` sin medición) y los principios de `AGENTS.md` (safety, offline-first,
privacy-minimizing, replayable).

**Sale (no se planifica aquí):** compra o uso de hardware, validación física
(P1a y sucesoras), TX activo en SDR, cualquier función ofensiva de radio y
dependencias cloud obligatorias. Esos carriles requieren autorización propia
y evidencia física real; P1a permanece congelada hasta entonces.
