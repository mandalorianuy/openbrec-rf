# Conformance

## Alcance

La conformidad OpenBREC describe compatibilidad con contratos versionados. No
es certificación, homologación, garantía operativa ni aprobación regulatoria.

## Clases

Se aceptan contribuciones de core, perfiles addon, adapters, reference builds,
evidence packs y extensiones. Cada una usa
`schemas/open-spec/conformance-submission.schema.json`, fija versiones exactas,
declara limitaciones y conserva resultados negativos.

## Niveles de evidencia

`unverified`, `specified`, `simulated`, `bench-validated` y `field-validated` son
una escalera de claims, no un score de calidad. `specified` exige contratos y
fixtures. `simulated` añade escenario y receipt determinístico. Los dos niveles
físicos requieren configuración exacta, protocolo, resultados, custodia,
entorno, jurisdicción y revisión; nunca se infieren desde CI. Los identificadores
de máquina correspondientes son `lab_validated` y `field_validated`.
`unsupported` es una disposición fuera de la escalera: indica que la capacidad
queda fuera del contrato, no que una prueba haya fallado.

## Ejecución

Ejecutar primero el gate del addon o clase aportada y luego:

```bash
python -m openbrec.verify open-spec-exit
```

Un fallo bloquea la publicación del aporte, no borra el material ni bloquea la
especificación abierta vigente. La recepción o preservación de posible distress
no se detiene por un fallo de autenticación: se conserva para review como no
verificado y no se eleva a hecho.
