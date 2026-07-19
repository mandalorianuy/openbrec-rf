# Publicación del bundle

## Contenido

Cada versión publica schemas, perfiles, fixtures, guías, matriz, comandos de
conformidad, residual registers, licencia y checksums. El bundle debe funcionar
sin cloud ni acceso a servicios del proyecto.

## Versionado

Los paths normativos incluyen la versión de spec. Un cambio incompatible exige
una nueva versión y vectores de compatibilidad. Los adapters fijan upstream y se
revalidan cuando firmware, schema o protocolo cambia. Todo cambio normativo se
propone y registra por el [proceso RFC](RFC-PROCESS.md).

## Release gate

La publicación requiere `open-spec-exit`, tests, árbol limpio y receipt sobre el
SHA exacto. Los documentos son fuente; una web generada, un anuncio, un badge o
un tag sin esos artefactos no constituye publicación normativa.

## Frontera abierta

No hay paywall, certificación de vendor ni hardware obligatorio. P1a es un
carril opcional y separado para evidence packs físicos; su ausencia no bloquea
la especificación y su ejecución requiere autoridad y activos propios.
