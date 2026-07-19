# Contribuir a OpenBREC

Gracias por contribuir. OpenBREC es una Open Spec con reference implementation: la norma, la evidencia y las implementaciones son carriles distintos y no se mezclan. Antes de empezar leé el [README](README.md), la [arquitectura](docs/architecture.md) y el [código de conducta](CODE_OF_CONDUCT.md).

## Criterio de idioma

- **Documentación humana:** español (guías, manuales, README, este archivo).
- **Contratos, código e identificadores:** inglés (schemas, campos, nombres de gates, comentarios de código).
- **Commits y PRs:** inglés o español; la historia del repo usa ambos.

## Tooling

```bash
uv sync --frozen
uv run --offline python scripts/validate_docs.py
uv run --offline python scripts/validate_bundle.py
uv run --offline python -m openbrec.verify open-spec
uv run --offline python -m unittest discover tests -q
```

Los tests usan `unittest` de stdlib; algunos se saltan con mensaje explícito si falta una herramienta del entorno (docker, pnpm) — esos skips son esperados. `validate_docs.py` exige que los links internos, ejemplos JSON/YAML y comandos citados en la documentación pública resuelvan.

## Cambios normativos (Open Spec)

Un cambio a contratos, invariantes o perfiles es normativo y exige:

1. Nueva versión de spec si es incompatible; los paths normativos incluyen versión.
2. Fixtures válidos **e inválidos** actualizados, con catálogo sha256.
3. Vectores de compatibilidad cuando el cambio migra datos o tokens existentes.
4. Gates y tests en verde; un fallo bloquea la publicación del aporte, no la spec vigente.

Los cambios normativos se proponen por el [proceso RFC](docs/open-spec/RFC-PROCESS.md) (template, estados y registro append-only de decisiones). El procedimiento completo de publicación está en [docs/open-spec/PUBLISHING.md](docs/open-spec/PUBLISHING.md) y las clases de contribución en [docs/open-spec/CONFORMANCE.md](docs/open-spec/CONFORMANCE.md). Los addons experimentales entran bajo `schemas/addons/` con su catálogo y `accepted_at: null`.

## Nuevo adapter, transporte o sensor

1. Entra como perfil o adapter reemplazable, versionado y con upstream fijado; nunca como requisito normativo ni por marca.
2. Se declara `unverified` hasta que exista evidencia reproducible. `simulated` exige escenario y receipt determinístico.
3. Respeta las reglas duras: los plugins publican observaciones y nunca escriben hechos consolidados; la fusión puede abstenerse; provenance e incertidumbre se conservan; un SOS con firma inválida se preserva para review.
4. El derivador de claves simulado de `lab-sim` está prohibido fuera de ese perfil.

El camino completo está en [docs/guides/implementing-the-spec.md](docs/guides/implementing-the-spec.md).

## Evidencia física

La evidencia física es un carril separado de la norma: se publica como [evidence pack](docs/evidence-packs/README.md) de la combinación exacta (versión, configuración, hardware, entorno, protocolo, resultados, límites) y sólo eleva esa combinación. P1a está en pausa declarativa: no se aceptan cambios de gates P1a hasta que exista hardware real disponible.

## Red lines (no se aceptan)

- Funciones ofensivas de Wi-Fi/radio: jamming, deauth, captura de credenciales o similares.
- TX activo en SDR en la fase inicial, ni TX fuera de los modos regulatorios normativos.
- Control autónomo de vuelo UAS.
- Estados de evidencia inflados: presentar simulación o CI como evidencia física/humana.
- Almacenar contenido de paquetes, credenciales o identificadores permanentes por defecto.
- Dependencias cloud obligatorias.

## Seguridad

Para vulnerabilidades, usá el canal privado de [SECURITY.md](SECURITY.md); no abras un issue público.
