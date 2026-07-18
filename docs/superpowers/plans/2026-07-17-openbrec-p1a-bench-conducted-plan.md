# OpenBREC P1a — plan de banco y conducted

- Estado: aprobado para secuenciación; ejecución física no autorizada
- Fecha: 2026-07-17
- Autoridad de secuencia: `DELIVERY_BOARD.md`
- Baseline requerido: P0 cerrado en `520c4719f9b2e078069d96cc64ef9099be5d3807`
- Alcance: P1a-01–P1a-08, hardware exacto, banco, conducted, UX y energía
- Progreso: `0 / 8` tasks aceptadas (`0%`)
- Estado inmediato: P1a-01 no iniciada; compra/préstamo no autorizado
- Red line: TX radiado prohibido en P1a

## 1. Objetivo y autoridad

Convertir las hipótesis P0 en evidencia física acotada sin confundir banco con
campo. Este plan autoriza sólo secuenciación, contratos, gates, fixtures
sintéticos y receipts. Toda compra, préstamo, uso de hardware, ensayo conducted,
captura real o estudio humano requiere una autorización explícita y trazable
según `config/p1a/authorization-policy.json`.

Precedencia:

1. `AGENTS.md` y ADR-0001 fijan las red lines.
2. `DELIVERY_BOARD.md` habilita una única task.
3. Este plan fija orden, aceptación y stop conditions.
4. `schemas/p1a/capability-manifest.schema.json` fija identidad/custodia física.
5. Las specs hijas gobiernan radio, energía, beacons y UX.
6. `docs/governance/p1a-residuals.json` gobierna incertidumbre pendiente.

## 2. Fronteras comunes

- Todo asset comienza y permanece `unverified` hasta su task de ensayo.
- Un manifest describe una unidad inspeccionada, no una familia comercial.
- El serial no se publica en claro; se conserva evidencia hash y custodia.
- Compra/préstamo, hardware, conducted, personas y captura real son gates
  independientes; una autorización no habilita las demás.
- P1a usa dummy load, cableado o recinto con aislamiento medido. No usa radiación
  exterior intencional ni `emergency_assumed_risk`.
- Resultados negativos, unidades descartadas y fallos quedan reviewables.
- La vida y preservación de evidencia tienen prioridad; no se infiere ausencia.

## 3. Secuencia de tasks

### P1a-01 — activos exactos y capability manifests

- Owner: `hardware-custody-owner`
- Reviewers: `release-reviewer`, cada owner técnico y `privacy-safety-reviewer`
- Dependencias: P0-09 aceptada; autorización explícita de cada asset
- Entregables: una unidad autorizada por categoría, receipt de custodia,
  inspección exacta, manifest normativo, pin/advisory review y descarte gobernado
- Validación: `python -m openbrec.verify p1a-assets --evidence-dir evidence/p1a/p1a-01`
- Aceptación: 9/9 categorías con exactamente un asset inspeccionado; cero
  placeholders; todo `unverified`; cero compra/préstamo sin authorization ID
- Stop: presupuesto/owner ausente, SKU/revisión/serial evidence ausente, asset no
  inspeccionado, firmware flotante o soporte promovido
- Evidencia: `evidence/p1a/p1a-01/`

### P1a-02 — radio conducted multi-bearer

- Owner: `radio-transport-maintainer`
- Dependencia: P1a-01 aceptada y autorización conducted específica
- Entregables: setup exacto, LoRaWAN/Meshtastic/MeshCore/RNode, frame SOS,
  airtime/goodput/overhead, near-far, co-site, path churn, downgrade y claves
- Validación: gate `p1a-radio-conducted`
- Aceptación: cero radiación exterior intencional; denominadores completos;
  support sólo por combinación asset/firmware/PHY/perfil ensayada
- Stop: aislamiento no medido, default secret, contador/nonce inseguro, SOS que no
  cabe, interferencia o cualquier claim global
- Evidencia: `evidence/p1a/p1a-02/`

### P1a-03 — comprensión de terminal offline

- Owner: `product-ux-reviewer`
- Dependencias: P1a-01 y autorización humana/consent aprobadas
- Entregables: protocolo versionado, 8 operadores, 8 personas no preparadas,
  evidencia anonimizada y resultados negativos
- Validación: gate `p1a-terminal-comprehension`
- Aceptación: SOS/ACK/aceptación operacional diferenciados; degradación, gaps y
  abstención comprendidos según umbrales pre-registrados
- Stop: consentimiento/reviewer ausente, muestra reducida o copy de garantía/
  ausencia
- Evidencia: `evidence/p1a/p1a-03/`

### P1a-04 — beacon tri-modal aislado

- Owner: `beacon-science-maintainer`
- Dependencias: P1a-01 y autorización de captura/retención
- Entregables: un beacon, calibración acústica/PIR/térmica, datasets controlados,
  OOD, provenance, falsos positivos/hora y disposition
- Validación: gate `p1a-beacon-single`
- Aceptación: métricas completas por entorno y clase, sin persona presente/
  ausencia automáticas; captures siguen authorization→review→preservation/delete
- Stop: captura no autorizada, clase/entorno omitido oculto o inferencia de vida
- Evidencia: `evidence/p1a/p1a-04/`

### P1a-05 — tres beacons y fallos correlacionados

- Owner: `beacon-science-maintainer`
- Dependencia: P1a-04 aceptada
- Entregables: tres unidades, overlap, movimiento, relay/source loss, spoofing,
  shared-cause y resultados negativos
- Validación: gate `p1a-beacon-multi`
- Aceptación: denominador 3/3, gaps visibles, cero confirmación/ausencia falsa y
  false alerts reportados sin promedio que oculte fallos
- Stop: reducir unidades, ocultar shared-cause o promover field readiness
- Evidencia: `evidence/p1a/p1a-05/`

### P1a-06 — caracterización energética exacta

- Owner: `energy-maintainer`
- Dependencias: P1a-01 y cargas físicas elegidas en P1a-02/P1a-04
- Entregables: load inventory L0–L3, potencia por estado, inrush, usable Wh, DoD,
  pérdidas, temperatura, envejecimiento, margen y source transitions
- Validación: gate `p1a-energy-characterization`
- Aceptación: cada carga/rail/estado medido; reserva SOS y shutdown; hysteresis y
  recuperación brownout trazables
- Stop: carga no inventariada, instrumento no calibrado o extrapolación solar
- Evidencia: `evidence/p1a/p1a-06/`

### P1a-07 — ensayo storage-only 72 horas

- Owner: `energy-maintainer`
- Dependencia: P1a-06 aceptada y configuración congelada
- Entregables: 72h sin generación, cadena L0/L1 real, margen 1.25×, power traces,
  fallos inyectados, reserva SOS y recuperación
- Validación: gate `p1a-energy-72h`
- Aceptación: 72h continuas con cero interrupción crítica y reserva final dentro
  del criterio pre-registrado
- Stop: cambiar cargas durante ensayo, generación auxiliar o esconder brownout
- Evidencia: `evidence/p1a/p1a-07/`

### P1a-08 — tres ResponseCells por cable/IP

- Owner: `core-replay-maintainer`
- Dependencias: P1a-02 y P1a-06 aceptadas
- Entregables: tres celdas aislables, gateway/carry bundle, recursos compartidos,
  partición, hub loss y reconciliación
- Validación: gate `p1a-wired-integration`
- Aceptación: cada celda opera sin superior; cero pérdida/overwrite; degradación
  visible; reconciliación determinística; cero TX radiado
- Stop: dependencia de hub, raw-frame bridge o claim de deployment de campo
- Evidencia: `evidence/p1a/p1a-08/`

## 4. Exit P1a

P1a termina sólo con `8 / 8` tasks aceptadas, manifests exactos, radio/security/
coexistence conducted, comprensión crítica, métricas beacon completas, 72 horas
storage-only y tres celdas cableadas autónomas. El exit produce una decisión
por perfil para P1b; nunca autoriza P1b automáticamente.

## 5. Métrica y estado gobernado

El único numerador es `tasks aceptadas / 8`:

- plan, schema, gate, shortlist, búsqueda de precios o autorización verbal no
  cuentan como task P1a aceptada;
- compra/préstamo sin manifest y receipt no cuenta;
- hardware disponible, flashing o un ensayo parcial no cuentan;
- CI de readiness no acredita hardware ni conducted;
- P0 no cuenta como progreso P1a;
- cerrar una task no inicia la siguiente.

Estado al aprobar este plan: `0 / 8` (`0%`). P1a-01 no iniciada. La próxima
acción posible es una autorización explícita de asset/custodia; este plan no la
sustituye.
