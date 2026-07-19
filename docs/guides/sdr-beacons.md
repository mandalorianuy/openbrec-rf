# Recepción SDR de balizas y dirección de llegada

## Objetivo

Definir el perfil receive-only de SDR para decodificar balizas de socorro 406 MHz Cospas-Sarsat y estimar dirección de llegada (DF) con arrays coherentes, coordinado con la doctrina de búsqueda existente.

## Audiencia

Operadores técnicos, integradores de SDR y enlaces con equipos que ya ejecutan búsqueda de ELT/EPIRB/PLB.

## Prerrequisitos

Modo regulatorio `receive_only` en campo (TX solo en banco bajo `conducted_only`, ver [Marco regulatorio](regulatory.md)), SDR con configuración declarada y la [base citable de evidencia](../research/rf-sensing-state-of-the-art.md).

## Capacidades necesarias

El addon experimental [`sdr-receive-profile`](../../schemas/addons/1.0.0/sdr-receive-profile.schema.json): `mode: receive_only_in_field` como const, casos de uso declarados y `demodulate_third_party_traffic: false`. La recepción en campo nunca transmite; cualquier prueba con TX ocurre en banco con carga fantasma o recinto medido.

## Alternativas permitidas

- **Decodificación 406 MHz:** decoders open-source (SDR++ con decoder 406, codecs Python comunitarios) para ELT/EPIRB/PLB del sistema Cospas-Sarsat. Ejemplos reemplazables.
- **DF con array coherente:** KrakenSDR (5 canales coherentes, 100 MHz–1 GHz, cubre 406 MHz) como ejemplo reemplazable; cualquier array coherente calibrado sirve.
- **Ocupación de espectro / interferencia:** survey pasivo para el plan de comunicaciones del incidente.

## Componentes e interfaces

SDR + antena declarados, perfil de recepción versionado, observaciones con provenance e incertidumbre, y coordinación doctrinal: la búsqueda de balizas 121,5/406 MHz tiene doctrina propia (Civil Air Patrol, ICAO). El SDR de OpenBREC aporta recepción y DF a esa doctrina; no la reemplaza ni declara hallazgos por su cuenta.

## Pasos

1. Declarar el perfil receive-only: bandas, ganancia, calibración y casos de uso.
2. Validar en banco la decodificación con baliza de test o grabación conocida (bajo `conducted_only` si hay TX de prueba).
3. Calibrar el array DF y medir error angular en geometría conocida antes de operar.
4. Registrar toda decodificación como observación con incertidumbre; nunca como hecho consolidado.
5. Coordinar con la autoridad del incidente y la doctrina CAP/ICAO para búsqueda y confirmación.
6. Documentar qué se midió para elevar evidencia: tasa de decodificación vs. distancia, error angular, condiciones exactas.

## Resultado esperado

Observaciones de balizas con decodificación y/o bearing trazables, integradas al plan de búsqueda del incidente sin claims operacionales no ensayados.

## Validación mínima

Fixtures válidos/inválidos del perfil (rechazo de `mode` distinto de receive-only en campo y de demodulación de tráfico de terceros) y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

## Fallos comunes y recuperación

Ante decodificación parcial de una trama 406, publicar los bits válidos con incertidumbre, nunca completar campos por inferencia. Ante bearing inestable por multipath en escombros, declarar la limitación, tomar múltiples posiciones y abstenerse si la geometría no soporta triangulación. Ante saturación del frontend, declararlo y reducir ganancia; no confundir intermodulación con baliza.

## Safety, privacidad y preservación

Receive-only elimina el riesgo de interferencia propia, pero una baliza detectada es un dato vital: preservar la observación cruda y su timestamp aunque falle la decodificación completa, y escalarla de inmediato al mando. No demodular tráfico de terceros (const del contrato).

## Estado de evidencia

Decodificación 406 MHz con SDR: `bench-validated` (comunitario). DF con array coherente: `bench-validated`, con uso de campo comunitario en foxhunting. Uso de SDR open-source en SAR operacional: `unverified` (cero rescates reales atribuidos). Todo lo demás: `specified`/`simulated`.

## Qué no demuestra

Detectar una baliza no demuestra superviviente (las balizas se activan por impacto o agua), y no detectarla nunca demuestra ausencia de personas: las balizas personales no son equipamiento universal.

## Contratos normativos relacionados

Addon experimental [`sdr-receive-profile`](../../schemas/addons/1.0.0/sdr-receive-profile.schema.json) ([catálogo de addons](../../schemas/addons/catalog.json)), [perfiles multi-bearer y modos regulatorios](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json), [Observation](../../schemas/core/1.0.0/observation.schema.json) y [Marco regulatorio](regulatory.md).
