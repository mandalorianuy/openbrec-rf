# ADR-0001: alcance del core, autoridad y red lines

- Estado: Accepted
- Fecha: 2026-07-17
- Decisor: project owner
- Alcance: M0 core y fronteras con addons

## Contexto

OpenBREC RF contiene diseño, schemas tempranos, perfiles y Compose, pero todavía no constituye una plataforma ejecutable. Varias autoridades históricas se superponen y el verificador original sólo comprueba estructura básica. Antes de generar contratos o servicios es necesario fijar qué pertenece al core, qué documentos mandan y qué límites no pueden atravesarse de forma implícita.

Los schemas existentes preceden al catálogo normativo M0. Aunque declaran Draft 2020-12 y versiones `1.0.0`, no tienen evidencia completa de metaschema, fixtures, compatibilidad ni consumidores generados. Corregirlos in place destruiría el baseline necesario para evaluar compatibilidad.

## Decisión

### Autoridad

La precedencia dentro del repositorio es:

1. `AGENTS.md` para safety, evidencia, offline-first y reglas operativas del agente.
2. ADRs `Accepted` para decisiones transversales o difíciles de revertir.
3. Especificaciones aprobadas para comportamiento, límites y criterios de aceptación.
4. JSON Schema Draft 2020-12 registrado en el catálogo core para la forma normativa de datos.
5. `DELIVERY_BOARD.md` para orden y estado de ejecución.
6. Diseño técnico, roadmap, BOM y documentos históricos como contexto no normativo cuando exista conflicto.

Una autoridad inferior no puede habilitar una capacidad bloqueada por otra superior. Todo conflicto nuevo se detiene y resuelve mediante ADR o enmienda explícita antes de implementar.

Este ADR usa numeración fundacional de cuatro dígitos porque las especificaciones ya lo citan como `ADR-0001`. Los ADR históricos de tres dígitos se preservan sin renombrar ni reinterpretar.

### Frontera del core M0

El core M0 incluye únicamente:

- catálogo contractual, `DomainEvent`, provenance, handling y schemas core;
- validación normativa, modelos generados y compatibilidad;
- accepted log, quarantine, vault, ledger y audit;
- replay adapter/core, canonicalización, reconciliación y receipts;
- runtime mínimo offline, simulador sintético y proyección explicable;
- interfaces de adapters basadas en capacidades.

El core no conoce protocolos de radio, fabricantes, fuentes de energía ni modalidades de beacon concretas. Los plugins sólo emiten observaciones contractuales y nunca escriben directamente hechos consolidados.

Energía, LoRaWAN, Meshtastic, MeshCore, Reticulum/RNode, SOS, federación, terminales y beacons son addons. Pueden aportar schemas mediante el mecanismo de extensión futuro, pero su implementación permanece bloqueada hasta demostrar el exit completo de M0.

### Baseline legacy

Los seis archivos JSON existentes directamente bajo `schemas/` se registran en `schemas/legacy/catalog.json` como `legacy-unverified` con path, `$id`, versión declarada y SHA-256 de bytes. Durante M0:

- no se mueven, corrigen ni regeneran;
- un cambio de bytes falla el gate de catálogo;
- su versión declarada no constituye una afirmación de compatibilidad;
- adopción, reemplazo o deprecación exige fixtures históricos y decisión SemVer posterior.

Los contratos normativos nuevos se registrarán separadamente bajo `schemas/core/` a partir de M0-02.

### Red lines

- Safety before capability y life-safety before routine privacy minimization, sin eliminar necesidad, proporcionalidad, auditoría o revisión.
- Ninguna función ofensiva, jamming, deauthentication, suplantación o captura de credenciales.
- Ningún TX activo en M0 ni control de vuelo.
- Ninguna dependencia cloud obligatoria ni acceso de red en replay/startup offline.
- Ninguna inferencia de ausencia por silencio, pérdida de nodo o sensor negativo.
- Ningún secreto, payload crudo o identificador directo en claro fuera de preservación life-safety autorizada.
- Ningún input descartado, corregido o reintentado silenciosamente.
- Ningún modelo ML sin versión, incertidumbre, OOD y abstención; M0 debe funcionar sin ML.
- Ningún claim de hardware `supported` sin evidencia propia reproducible.

### Toolchain y política offline

- Python queda fijado en `3.12.13`, compatible con la autoridad Python 3.12 del proyecto. `uv.lock` es el lockfile Python; M0-01 no agrega dependencias externas y usa `unittest` de stdlib.
- Node queda fijado en `24.18.0`, rama LTS vigente al decidir. `pnpm` queda fijado en `11.9.0`; `pnpm-lock.yaml` es el lockfile JavaScript. M0-01 no agrega paquetes JavaScript.
- `.python-version`, `.node-version`, `pyproject.toml`, `package.json` y ambos lockfiles son parte del baseline.
- Descarga de runtimes y dependencias pertenece al provisioning. Los gates `offline-startup`, replay y generación `--check` operan sólo con runtimes, caches y artefactos ya fijados; una resolución de red durante esos gates es fallo.
- Toda actualización de runtime, package manager, generador o dependencia modifica lockfiles, documenta licencia y exige regenerar evidencia.

Referencias de versión consultadas el 2026-07-17:

- Python 3.12.13: https://www.python.org/downloads/release/python-31213/
- Node.js release schedule y LTS: https://nodejs.org/en/about/previous-releases

## Consecuencias

- Los schemas legacy quedan disponibles para review sin confundirse con contratos normativos aprobados.
- M0-02 puede crear contratos sin romper silenciosamente consumidores históricos.
- El core conserva independencia de hardware y transportes; las alternativas multi-bearer siguen abiertas.
- Los gates iniciales pueden declarar alcance limitado sin aparentar validación funcional completa.
- La prioridad life-safety aumenta la obligación de sellado, acceso auditado, TTL y borrado verificable.

## Criterios de revisión

Revisar este ADR sólo si cambia la misión, la frontera core/addon, la prioridad life-safety, el formato normativo o la política de ejecución offline. Un nuevo bearer, sensor o fuente energética no justifica por sí solo modificarlo.
