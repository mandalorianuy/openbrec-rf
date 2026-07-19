# Roadmap — OpenBREC RF

**Última actualización: 2026-07-19.** Este es el roadmap vigente del proyecto.
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

## Siguiente

- **Evidencia física P1a:** permanece en pausa declarativa; se retoma cuando
  exista hardware real disponible y autoridad para operarlo.
- **Validación comunitaria de addons:** los once addons experimentales de las
  Fases 3 y 6 esperan review y evidencia de terceros vía
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
