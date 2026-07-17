# Review P0-04 — comparación multi-bearer gobernada

- Fecha: 2026-07-17
- Task: P0-04
- SHA evaluado: `7e01320ec9520316add7a7d2915fbb1426106bc1`
- Implementación: rol `radio-transport-maintainer` (Codex)
- Review safety/privacy: rol `privacy-safety-reviewer` (revisión separada)
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `transport-comparison` y `malicious-transport` pasan sobre el
mismo SHA, con `dirty: false`, errores y warnings vacíos. `validate_receipt`
confirmó SHA, checkout limpio, runtimes, lockfiles, inputs y hash canónico de
output. La suite completa pasa 94 tests y los artefactos se conservan en
`evidence/p0/p0-04/`.

El workload fija versiones y commits oficiales para
[Meshtastic v2.7.26.54e0d8d](https://github.com/meshtastic/firmware/releases/tag/v2.7.26.54e0d8d),
[MeshCore companion-v1.16.0](https://github.com/meshcore-dev/MeshCore/releases/tag/companion-v1.16.0)
y [Reticulum 1.3.8](https://github.com/markqvist/Reticulum/releases/tag/1.3.8).
Las propiedades modeladas también se limitaron por la
[documentación de routing de Meshtastic](https://meshtastic.org/docs/overview/mesh-algo/),
el [FAQ oficial de MeshCore](https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md)
y el [manual de Reticulum](https://reticulum.network/manual/). Cada source pin,
licencia, fecha, limitación y coeficiente sintético queda dentro del fixture.

## Boundary aceptado

- Un `OpenBRECEnvelope` protegido y validado por JSON Schema entra primero a una
  frontera común. Los tres adapters reciben exactamente su mismo hash y sólo
  agregan metadata de camino modelada; no interpretan identidad ni estado SOS.
- Se ejecutan 27 combinaciones determinísticas: tres modelos, tres
  `TransportProfile` y escalas de 12, 40 y 100 nodos. Cada corrida incluye SOS,
  estado y ubicación, más 23 eventos de movilidad, relay loss, path churn,
  flood, partición y carry declarados por seed y penalidad sintética común.
- Los 4.104 mensajes del denominador terminan explícitamente como 3.138
  entregados modelados o 966 fallidos modelados. Ningún fallo se quita del
  denominador.
- Cada resultado publica PDR, p50/p95/p99, airtime, retries, duplicates,
  convergencia, energía modelada y metadata disclosure, ligado a bearer,
  versión, commit, perfil, escala y `support_status: unverified`.
- SOS se ordena antes de entrar al bearer; hay cero inversiones de prioridad,
  cero raw/flood bridges y cero divergencias de input común.
- Los 11 casos hostiles producen 11 disposiciones `rejected` o
  `review_quarantine`, con cero pérdida silenciosa y cero
  `operator.accepted` falsos. Posible distress inválido se preserva para review.
- `global_winner` es nulo. No se emiten claims de rango, hops físicos,
  capacidad RF, consumo real, autonomía ni field readiness.

## Evidencia negativa y límites

Los coeficientes son supuestos determinísticos de OpenBREC para ejercitar
contratos y comparabilidad; no son benchmarks ni mediciones de los proyectos
upstream. No se ejecutaron firmware, protobufs/frames nativos, RNode, radios,
antenas, coexistencia, jamming, terminales, MQTT de campo ni RF irradiada o
conducted. Tampoco se probaron rangos, cantidad real de hops, saturación,
energía física o soporte de hardware.

P0-R001 pasa a controlado para la simulación y continúa planificado para P1a:
wire behavior y hardware siguen `unverified`. P0-R008 queda controlado por pins
inmutables y reapertura obligatoria en P0-09/P1 si cambia una fuente. P0-R002 y
TM-004 mantienen fuera de P0 regulación, TX, coexistencia y resistencia a
interferencia. TM-014 permanece High porque los bearers pueden compartir
espectro, energía, hardware o política aunque el modelo lógico sea correcto.

## Decisión

P0-04 cumple su Definition of Done simulada y se acepta como `4 / 9` (`44.4%`).
P0-05 queda elegible por dependencia, pero no se inicia en este closeout. Esta
decisión no habilita hardware, TX, campo ni selección universal de bearer.
