# RFC 0004: addon cot-bridge-profile (mapeo export-only a Cursor on Target / TAK)

- Estado: `accepted` (2026-07-19)
- Decisor: project owner, según [RFC-PROCESS](../RFC-PROCESS.md) (proceso unipersonal vigente; sus obligaciones de registro append-only y preservación de disenso aplican a este archivo)
- Decisión asociada: complementa [RFC-0001](0001-rf-sensing-addons.md) (interoperación de salida); hermana del addon `interop-emergency-standards-profile` (CAP/EDXL-DE)
- Comentarios en contra recibidos: ninguno (proceso unipersonal; esta sección se conserva para registrar disenso futuro)

## 1. Problema

ATAK/TAK Server es la plataforma táctica dominante en gran parte de la comunidad SAR/defensa: un equipo que ya opera con ATAK no va a mirar una segunda consola. Si OpenBREC no puede exportar sus observaciones, resultados de fusión, registros de víctima y mensajes a Cursor on Target (CoT), su evidencia queda invisible para el puesto de mando que sí usa el equipo. CoT es XML `<event><point/><detail/></event>` con atributos `uid/type/time/start/stale`; los transportes documentados son UDP multicast SA `239.2.3.1:6969` (sin servidor — cualquier ATAK en la LAN lo ve), TCP `8087` y TLS `8089`; existen servidores on-premise (OpenTAKServer, activo; FreeTAKServer, estancado), una librería de referencia (PyTAK) y precedentes de gateway (aprscot, inrcot, LINCOT). No existe taxonomía oficial USAR de `type` CoT: los tipos siguen el patrón `a-f-G-…` (affiliation-friendliness-dimension) y cada despliegue define sus `usericon`.

El riesgo normativo: un bridge mal gobernado convertiría indicios débiles en "personas localizadas" en el mapa del mando, o elevaría el nivel de evidencia por el solo hecho de exportar.

## 2. Propuesta

Agregar el addon experimental `cot-bridge-profile` (policy) a `schemas/addons/1.0.0/`, con `status: experimental` y `accepted_at: null`:

| Grupo | Decisión |
|---|---|
| Dirección | `direction: export_only` (const); `gateway_implemented: false` (const) — es spec de mapeo; el mapper de referencia es `lab-sim` (`reference_mapper_profile` const) |
| Transporte | `transport.mode` enum `udp_multicast_sa / tcp / tls`; multicast primero (`group 239.2.3.1`, `port 6969`); `tcp_port: 8087` y `tls_port: 8089` documentados como consts; `server_required: false` (const) |
| Mapeo | `uid_scheme: incident_scoped_deterministic`; `type_prefix` configurable (default honesto `a-f-G`) + `usericon` propio; `stale_ttl_seconds` declarado; `remarks_format: structured_json` (provenance, confidence y limitations viajan en `detail/remarks`) |
| `field_map` | `source_contract` enum (`observation`, `fusion-result`, `victim-record`, `human-message`) → `cot_target` (`uid`, `type`, `time`, `start`, `stale`, `point.*`, `detail.usericon`, `detail.remarks`) con transformaciones `copy / iso8601_utc / incident_rotating_hash` |
| Invariantes (const) | `person_identification_allowed: false`, `raw_payload_allowed: false`, `provenance_preserved: true`, `external_ack_means_person_located: false`, `silence_means_absence: false`, `evidence_level_elevation_by_export: false`, `cot_type_vocabulary: open_with_default_icons` (honesto: no hay taxonomía USAR oficial), `declared_evidence: specified` |

Acompañan: fixtures válidos/inválidos, siete rechazos nuevos en `tests/test_p0_01_contracts.py` y la documentación de dominio que se produce en paralelo.

## 3. Compatibilidad

Compatible hacia atrás. Ningún contrato core ni addon existente cambia de bytes; catálogo y `compatibility-baseline.json` se actualizan de forma aditiva (31 → 32 addons). La versión de spec se mantiene `1.0.0-draft.1`. El mapeo no introduce identificación de personas ni payload crudo: los `uid` se derivan con hash rotativo por incidente, coherente con los dominios de RF pasiva.

## 4. Alternativas consideradas

1. **No integrar con TAK**: descartada — deja la evidencia de OpenBREC fuera de la consola que el mando realmente mira.
2. **OpenTAKServer como backend**: no descartada — es la opción on-premise activa cuando se quieren feeds con servidor (TCP 8087 / TLS 8089); queda como decisión de despliegue, no del contrato.
3. **FreeTAKServer**: descartada como referencia — proyecto estancado; citado sólo para registro.
4. **Multicast puro sin servidor** (UDP SA 239.2.3.1:6969): adoptada como modo primario — cero infraestructura, offline-first real, cualquier ATAK en la LAN recibe; los modos TCP/TLS quedan declarados para cuando exista servidor.
5. **Taxonomía `type` propia cerrada**: descartada — no hay taxonomía USAR oficial; se declara `open_with_default_icons` y `usericon` propio en vez de fingir un estándar.

## 5. Impacto en evidencia y estados

- **Estado asignado: `specified`** (`declared_evidence` const). Es un contrato de mapeo sin gateway implementado. Cuando exista el mapper de referencia en `lab-sim`, su evidencia de implementación será `simulated` — el contrato permanece `specified` y **exportar nunca eleva el nivel de evidencia** (`evidence_level_elevation_by_export: false`).
- **Un ACK de TAK nunca confirma persona localizada** (`external_ack_means_person_located: false`), simétrico al invariante CAP (`cap_ack_means_operational_acceptance: false`) y al del portal autojoin (`portal_ack_means_person_located: false`). El silencio en el mapa TAK nunca es ausencia.
- **Fixtures y gates:** matriz estándar más rechazos de `direction` distinto de `export_only`, `gateway_implemented: true`, `person_identification_allowed`/`raw_payload_allowed`/`external_ack_means_person_located`/`evidence_level_elevation_by_export`/`silence_means_absence` en valores prohibidos. Gates `addon-contracts`, `addon-fixtures`, `schema-compat` y `contracts-gen --check` en verde.
- **Este RFC no habilita** runtime, gateway, servidor TAK ni campo; PyTAK se cita como librería de referencia para el futuro mapper lab-sim, junto a los precedentes aprscot/inrcot/LINCOT.
