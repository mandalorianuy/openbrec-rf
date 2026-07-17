# Review P0-03 — mensajería segura, SOS append-only y transporte hostil

- Fecha: 2026-07-17
- Task: P0-03
- SHA evaluado: `c6a3dc15ccf045dac60148080870a5f44eb2027c`
- Implementación: rol `privacy-safety-reviewer` (Codex)
- Review funcional: rol `core-replay-maintainer` (revisión de replay separada)
- Autoridad de ejecución y merge: owner del repositorio
- Veredicto: accepted para P0 simulado

## Evidencia revisada

Los receipts de `human-message-security`, `sos-state-replay` y
`transport-policy` pasan sobre el mismo SHA, con `dirty: false`, errores y
warnings vacíos. `validate_receipt` confirmó SHA, checkout limpio, runtimes,
lockfiles, inputs y hash canónico de output. La suite completa pasa 88 tests y
los artefactos se conservan en `evidence/p0/p0-03/`.

El fixture sintético congela los tres hashes de resultado y contiene forged,
replayed, revoked, late, duplicate, malicious transport, nonce reuse, sequence
rollback y default-secret cases. Ningún caso hostil se quitó del denominador.

## Boundary aceptado

- `HumanMessage` usa AES-256-GCM y firma Ed25519 sobre JCS. El AAD liga todos los
  campos semánticos de incidente, celda, actor, dispositivo, destinatario, tipo,
  secuencia y TTL; outputs públicos se revalidan con JSON Schema.
- Identidad por incidente usa bindings actor-dispositivo-clave, enrolamiento
  local con confirmación de fingerprint, mínimos derechos para peers desconocidos
  y caché local de revocación sin dependencia de red.
- La pérdida simulada revoca el binding, rota la clave grupal al epoch 2 y permite
  operar al dispositivo reemplazado offline. La clave anterior no autentica.
- Reutilización de nonce, rollback de secuencia, replay, firma forjada, binding
  revocado, TTL expirado, secret default/shared y rol insuficiente producen
  eventos de seguridad y disposición explícita.
- Distress inválido o tardío se preserva con hash y razón en
  `review_quarantine`; no se descarta ni se convierte en mensaje autenticado.
- El estado SOS deriva seis eventos append-only. `gateway.received` es técnico,
  `operator.seen` humano y `operator.accepted` exige ambos antecedentes, firma y
  rol; un adapter hostil obtiene cero aceptaciones falsas.
- Un mismo mensaje protegido cruza tres bearers simulados y genera tres receipts.
  La deduplicación conserva un evento lógico, rechaza loop, raw bridge y payload
  alterado, y valida un `TransportPolicyDecision` activo.

## Evidencia negativa y límites

Los key bytes se derivan de labels públicos bajo namespace `simulated-only` para
producir vectores determinísticos. Son intencionalmente inseguros fuera del
replay y no prueban entropy, secure element, keystore, wipe, HSM, resistencia a
captura o custodia. Tampoco se ejecutaron firmware, protobufs, RF, MQTT de campo,
Meshtastic, MeshCore, Reticulum, LoRaWAN, terminal real, comprensión humana ni
federación.

P0-R001/P0-R008 mantienen específicos/versiones de bearer para P0-04. P0-R007
mantiene custodia física y terminal robado para P1a. P0-R010 queda resuelto sólo
para la porción P0-03. P0-R012 prohíbe reutilizar vectores sintéticos como
credenciales operativas.

## Decisión

P0-03 cumple su Definition of Done simulada y se acepta como `3 / 9`. P0-04
queda elegible por dependencia, pero no se inicia en este closeout. Esta decisión
no habilita hardware, TX, adapter real, campo ni claim de entrega o rescate.
