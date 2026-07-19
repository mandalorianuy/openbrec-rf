# Evidence packs

Un evidence pack vincula un claim a una implementación física o experimental exacta. Es opcional para publicar la Open Spec, los manuales y los reference builds.

## Contenido mínimo

- versión de spec, SHA de software y configuración;
- build manifest y BOM con versiones/seriales cuando corresponda;
- entorno, jurisdicción, fecha y responsables del ensayo;
- protocolo, instrumentos y calibración;
- datos crudos o hashes/custodia cuando sean sensibles;
- resultados completos, fallos, incertidumbre y criterios pass/fail;
- claim permitido y sección explícita “qué no demuestra”.

Un pack puede elevar sólo la combinación probada a `bench-validated` o `field-validated`. No certifica componentes sustitutos, otra banda, firmware, antena, batería, topología, clima ni misión. La evidencia sintética se conserva con la implementación y se etiqueta `simulated`; no se presenta como evidencia física.

## Publicación y privacidad

Separar el índice público de datos sensibles o de distress. Publicar hashes, provenance, esquema y proceso de acceso cuando el material completo requiera custodia. Nunca inventar una inspección, aprobación, participante o resultado faltante.

Para el procedimiento de validación, usar [Validación y troubleshooting](../guides/validation-troubleshooting.md) y [Conformance](../open-spec/CONFORMANCE.md).
