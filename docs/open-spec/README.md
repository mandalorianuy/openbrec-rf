# OpenBREC Open Spec 1.0.0-draft.1

Este directorio es el punto de entrada humano al bundle normativo abierto. La
especificación, schemas, perfiles, fixtures, guías y matriz se publican bajo
`Apache-2.0` y pueden validarse completamente offline.

Un resultado conformante acredita el contrato y el escenario nombrado. **No acredita**
hardware físico, cobertura RF, autorización regulatoria, autonomía energética,
seguridad eléctrica, comprensión humana, detección de personas ni readiness de
campo.

## Usar la especificación

- [Conformance](CONFORMANCE.md): clases, comandos y niveles de evidencia.
- [Evidencia comunitaria](COMMUNITY-EVIDENCE.md): enviar, revisar, rechazar,
  conservar y superseder contribuciones.
- [Publicación](PUBLISHING.md): bundle offline, versionado, checksums y releases.
- [Reference builds](reference-builds/README.md): construir, reutilizar o combinar.
- [Matriz de funcionalidades](../decision-matrices/open-spec-functionality-matrix.json):
  valor BREC, evidencia, alternativa, hardware, privacidad, safety, esfuerzo y
  aceptación sin score agregado ni ganador universal.

El comando de cierre normativo es:

```bash
python -m openbrec.verify open-spec-exit
```

Los evidence packs físicos son opcionales y sólo pueden elevar la combinación
exacta que documentan. Nunca convierten una referencia en requisito universal.
