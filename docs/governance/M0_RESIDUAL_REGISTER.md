# Registro gobernado de residuales M0

- Estado: activo
- Owner de registro: `release-reviewer`
- Regla: ningún residual puede quedar sólo como comentario; debe estar `resolved`, `controlled`, `planned` o `blocked`
- Cierre: requiere artefacto verificable y actualización append-only de este registro

## Estados

- `resolved`: causa eliminada y evidencia disponible.
- `controlled`: limitación aceptada con control permanente y gate que evita degradación.
- `planned`: solución asignada a una task aprobada, owner, gate y stop condition.
- `blocked`: no existe aún una ruta segura; impide avanzar la dependencia indicada.

## Registro

| ID | Residual | Estado | Owner | Resolución o plan | Gate/artefacto | Stop condition |
|---|---|---|---|---|---|---|
| M0-R001 | El entorno Python 3.12 de M0-01 no incluía PyYAML y el receipt estructural no validaba perfiles YAML. | resolved en M0-02 | contract-maintainer | `PyYAML==6.0.3` quedó fijado en `uv.lock`; el gate se ejecuta mediante `uv run --offline`. | `evidence/m0/bundle-structure/m0-02-receipt.json` con `warnings: []` | Reabrir y bloquear el gate si reaparece la advertencia o existe drift del lockfile. |
| M0-R002 | `datamodel-code-generator==0.38.0` fue retirado por un rediseño incompleto. | resolved en M0-02 | contract-maintainer | Se rechazó 0.38.0 y se fijó 0.37.0, recomendada por el propio aviso de distribución. | `uv.lock`, `contracts-gen --check` | No actualizar hasta una versión no retirada, revisión de diff y fixtures completos. |
| M0-R003 | JSON Schema no demuestra orden lexicográfico de causas, monotonicidad de secuencia, receta UUIDv5 ni correspondencia exacta entre hash e ID. | planned para M0-04 | core-replay-maintainer | Implementar validador semántico determinístico antes de accepted log/replay. | gates `core-replay`, `determinism` y `security`; fixtures de colisión, desorden y secuencia regresiva | M0-04 no cierra y ningún replay se declara determinístico sin estos vectores. |
| M0-R004 | JSON Schema valida formato temporal, pero no ordena `window_start < window_end`, `captured_at <= received_at`, expiración o retención. | planned para M0-04 | core-replay-maintainer + privacy-safety-reviewer | Validación semántica con `Decimal`/UTC y receipts de fallo; políticas de TTL en handling. | gates `core-replay`, `review-quarantine` y `life-safety-preservation` | No aceptar eventos con relaciones temporales imposibles ni borrar material sin receipt. |
| M0-R005 | Pydantic y TypeScript no expresan todos los constraints Draft 2020-12. | controlled permanente | contract-maintainer | JSON Schema con `FormatChecker` es autoridad y corre antes de modelos; 36 fixtures válidos y 126 inválidos prueban el boundary. | `schema`, `fixtures`, `contracts-gen --check` | Un consumidor generado nunca puede reemplazar la validación normativa. |
| M0-R006 | Los contratos core permanecen `experimental` hasta que el runtime y los gates finales demuestren su consumo operacional. | planned para M0-06 | release-reviewer | Mantener estado explícito; promover sólo mediante revisión de release y receipts del M0 exit. | `schema-compat`, `offline-startup`, replay y reporte M0 exit | No marcar `supported` ni planificar P0 mientras M0 no cierre. |
| M0-R007 | El nuevo grafo de dependencias todavía no tiene SBOM, licencia y vulnerability receipt del commit final. | planned para M0-06 | release-reviewer | Generar SBOM, licencias y escaneo separado con lockfiles exactos. | gates `security`, `sbom` y `licenses` | M0 exit bloqueado ante vulnerabilidad no gobernada, licencia incompatible o evidencia ausente. |
| M0-R008 | `$ref` relativos deben resolverse sin red pese a que cada schema tiene `$id` canónico. | controlled permanente | contract-maintainer | El registry local crea aliases sólo para archivos catalogados; ambos generadores reciben el directorio local y `contracts-gen` corre offline. | `schema` y `contracts-gen --check` con `uv run --offline` | Cualquier ref remoto/no registrado o intento de descarga falla el gate. |
| M0-R009 | El contrato de EvidenceVault no elige todavía cifrado at-rest ni custodia de claves. | planned para M0-04 con dependencia de security review | privacy-safety-reviewer | Implementar boundary sustituible y mantener perfil de campo `unverified` hasta decisión criptográfica aprobada. | `life-safety-preservation`, threat model y security review | Ningún perfil de campo ni claim de vault seguro puede aprobarse sin la decisión. |
| M0-R010 | Los fixtures TypeScript podían quedar sólo representados como declaraciones sin comprobar asignabilidad. | resolved en M0-02 | contract-maintainer | Se genera `fixture-check.ts` desde los 36 fixtures válidos y se compila con TypeScript estricto y `noEmit`. | `contracts-gen --check`, `typescript_checked: true` | Drift, `any` implícito o error de asignabilidad falla la generación. |

## Regla de actualización

Cada cambio conserva ID, estado anterior, fecha, evidencia y razón. Un residual `planned` que llega a su task sin solución pasa a `blocked`; no se difiere automáticamente a otra fase. Los resultados negativos se adjuntan al mismo ID y nunca se eliminan.
