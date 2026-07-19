# Programa documental OpenBREC — plan cerrado

Estado: **completado**. Este plan concentra la iniciativa en cinco entregables; la publicación de la Open Spec no depende de P1a ni de poseer, inspeccionar o certificar hardware.

- [x] **DOC-01 — Frontera y arquitectura de información.** Separar norma, implementación, guías, builds, evidence packs y field profiles; corregir contradicciones y congelar funcionalmente `1.0.0-draft.1` salvo correcciones.
- [x] **DOC-02 — README y entrada al proyecto.** Reescribir la presentación pública y establecer `docs/START_HERE.md` como ruta única por audiencia.
- [x] **DOC-03 — Manuales y guías prácticas.** Cubrir quickstart, planificación, energía, transportes, mensajería/SOS, beacons, federación, construcción/reutilización y troubleshooting bajo un contrato común.
- [x] **DOC-04 — Reference builds y validación.** Consolidar tres composiciones de solución, BOM por capacidades, aceptación y generación opcional de evidence packs.
- [x] **DOC-05 — Consistencia y publicación.** Validar navegación, enlaces, ejemplos, comandos offline, terminología y claims; entregar en un único PR.

## Definition of Done

Una persona nueva puede comprender, seleccionar, construir, probar y extender una solución desde el README. Los documentos enlazan a una autoridad inequívoca, las capacidades usan un vocabulario pequeño, los ejemplos comerciales son reemplazables y ninguna afirmación física se presenta sin evidencia.

## Residuales con disposición

| Residual | Disposición | Owner |
|---|---|---|
| Evidence packs físicos | Crear sólo cuando exista un ensayo real autorizado; no bloquea documentación. | Equipo que ejecuta el ensayo. |
| Field profiles | Publicar después de validación contextual y revisión operativa. | Responsable de cada deployment. |
| Traducciones | Mantener español como autoridad actual; aceptar traducciones versionadas sin duplicar norma. | Maintainers de documentación. |
| Compatibilidad de tokens históricos | Mostrar `lab_validated`/`field_validated` con etiquetas públicas canonicalizadas. | Maintainers de Open Spec. |

No se abren registros adicionales mientras una disposición y owner sean suficientes.
