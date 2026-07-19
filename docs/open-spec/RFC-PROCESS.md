# Proceso RFC de la Open Spec

Este documento define el proceso mínimo para proponer, evaluar y registrar
cambios a la especificación OpenBREC. Es deliberadamente liviano: mientras el
proyecto tenga un solo mantenedor, el proceso existe para que las decisiones
queden registradas y el disenso se conserve, no para crear burocracia.

## Qué amerita RFC y qué no

**Amerita RFC:**

- Un cambio normativo: modificar un contrato, invariante, perfil o gate ya
  publicado (p.ej. campos de un schema, reglas de fusión, estados de
  evidencia).
- Un nuevo dominio normativo o un nuevo addon experimental
  (`schemas/addons/`).
- Cualquier cambio incompatible que exija nueva versión de spec o vectores de
  compatibilidad.

**No amerita RFC** (PR directo con tests/gates en verde):

- Fixes editoriales: typos, enlaces, claridad de redacción sin cambio de
  significado normativo.
- Fixtures adicionales que no cambian contratos (más casos válidos/inválidos
  del mismo schema).
- Código de la implementación de referencia que no altera contratos
  publicados.

## Template de propuesta

Un RFC es un documento Markdown (issue o archivo bajo
`docs/open-spec/rfc/NNNN-titulo.md`) con estas secciones:

1. **Problema:** qué falta o qué está mal, con evidencia.
2. **Propuesta:** el cambio concreto (schema, invariante, gate, perfil).
3. **Compatibilidad:** si es compatible hacia atrás; si no, qué versión nueva
   exige y qué vectores de migración acompañan.
4. **Alternativas consideradas:** al menos una, y por qué se descarta.
5. **Impacto en evidencia y estados:** qué estados de evidencia toca, qué
   fixtures y gates cambian, y si eleva o reduce algún claim (nunca se eleva
   un claim físico sin evidence pack, según
   [PUBLISHING.md](PUBLISHING.md)).

## Estados

Los estados del RFC se alinean con el proceso de
[evidencia comunitaria](COMMUNITY-EVIDENCE.md):

1. `draft`: en redacción, aún no pide decisión.
2. `submitted`: propuesto formalmente; abierto a comentario.
3. `validated`: con fixtures válidos/inválidos, gates y tests en verde sobre
   la propuesta.
4. Cierre (append-only, uno solo):
   - `accepted`: incorporado a la spec (versión y catálogo actualizados).
   - `rejected_with_record`: rechazado con la razón registrada; el documento
     se conserva para no repetir el error.
   - `superseded`: reemplazado por otro RFC; el historial completo se
     conserva.

## Quién decide hoy

Con un solo mantenedor, el decisor es el **project owner**
([ADR-0001](../adr/ADR-0001-core-scope-authority-and-red-lines.md)). Sus
obligaciones bajo este proceso:

- Registrar cada decisión en un registro **append-only** (el propio archivo
  del RFC con su estado final y fecha; `silent_deletion_allowed: false`:
  ningún RFC ni decisión se borra silenciosamente).
- Preservar el disenso: los comentarios en contra quedan vinculados al RFC
  aunque la decisión sea aceptarlos o rechazarlos.
- No decidir contra las red lines de `CONTRIBUTING.md` ni de ADR-0001; esas
  sólo cambian por RFC propio.

## Cómo escala

Cuando haya dos o más mantenedores activos, este proceso se reemplaza por RFC
propio que defina: composición del grupo decisor, quorum o consenso,
mecanismo de desempate y período mínimo de comentario antes de cerrar un
`submitted`. Hasta que ese RFC exista y sea `accepted`, rige este documento.
