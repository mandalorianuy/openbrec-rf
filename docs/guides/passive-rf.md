# Observación RF pasiva de metadata

## Objetivo

Capturar metadata de emisiones ajenas (sin transmitir ni interactuar) como observaciones con provenance, minimización de privacidad en el borde y límites legales explícitos.

## Audiencia

Integradores de collectors, responsables de privacidad y operadores que registren actividad de dispositivos en la escena.

## Prerrequisitos

Modo regulatorio `receive_only` declarado ([Marco regulatorio](regulatory.md)), política de retención, HMAC rotativo por incidente provisionado y la [base citable de evidencia](../research/rf-sensing-state-of-the-art.md).

## Capacidades necesarias

El addon experimental [`passive-rf-observation`](../../schemas/addons/1.0.0/passive-rf-observation.schema.json), `Observation` con incertidumbre, stripping en el borde y retención gobernada. Consts del contrato: `subject_ref` es HMAC rotativo (nunca MAC cruda), `payload_retained: false`, `content_interception: false`, `active_emulation: false`.

## Alternativas permitidas

Kismet (release 2025-09-R1) como ejemplo reemplazable de collector; cualquier toolchain que cumpla el contrato sirve. Fuentes típicas:

- probe requests Wi-Fi y advertisements BLE (degradados por MAC randomization: los identificadores rotan y la vinculación temporal es frágil);
- rtl_433 (sensores ISM) y rtl_adsb (ADS-B), nativos en toolchains actuales;
- DJI DroneID vía AntSDR, para awareness del espacio aéreo del incidente.

## Boundary explícito: referencias externas excluidas

Lifeseeker (CENTUM, emula una celda celular ≈ IMSI catcher) y Wi2SAR (artículo ACM MobiCom 2026, AP mimético ≈ evil twin) son **referencias externas con boundary flag**, nunca capacidades OpenBREC: ambas implican transmisión activa engañosa, contradicen las red lines del proyecto y salen del marco legal de recepción pasiva. Todo colector OpenBREC vive del lado pasivo de la línea metadata-vs-contenido; el resumen legal y las citas están en [Recepción pasiva y marco legal](regulatory.md#recepción-pasiva-y-marco-legal).

## Componentes e interfaces

Collector pasivo, adapter que strippea en el borde (solo rasgos mínimos: tecnología, banda, RSSI con incertidumbre, timestamp), `subject_ref` por HMAC rotativo, `isolation_profile_ref` opcional si la observación se tomó bajo [RF quieting](rf-quieting.md), y almacenamiento con retención gobernada.

## Pasos

1. Declarar fuentes, bandas y toolchain con su configuración exacta.
2. Provisionar HMAC rotativo por incidente; prohibir persistencia de MAC cruda.
3. Configurar stripping en el borde: descartar payloads y todo contenido antes de persistir.
4. Emitir observaciones con provenance e incertidumbre; declarar MAC randomization como limitación.
5. Aplicar retención limitada y purgado al cierre del incidente.
6. Ejecutar replay con datasets sintéticos (presencia, ruido, rotación de identificadores).

## Resultado esperado

Un registro de actividad de dispositivos minimizado, pseudonimizado y legalmente acotado, que alimenta hipótesis sin identificar personas.

## Validación mínima

Fixtures válidos/inválidos del addon (rechazo de MAC cruda y de payload retenido) y gate de dominio:

```bash
uv run --offline python -m openbrec.verify addon-fixtures
```

Replay determinístico del dominio (JSONL sintético tipo Kismet → observaciones pseudonimizadas, con stripping verificado y rotación de `subject_ref`):

```bash
uv run --offline python -m openbrec.verify rf-sensing-passive
```

## Fallos comunes y recuperación

Ante MAC randomization, declarar menor confianza de vinculación y nunca "rellenar" identidad. Ante captura accidental de contenido, descartar en el borde y registrar la excepción. Ante duda legal sobre una fuente, suspenderla y volver a `receive_only` estricto hasta revisión.

## Safety, privacidad y preservación

La metadata de dispositivos es dato personal potencial: minimización, hash rotativo y retención limitada son obligatorios, no opcionales. El precedente reportado de multa por tracking Wi-Fi (Enschede 2021, ~600 000 €, verificar fuente primaria) ilustra el riesgo de salirse de la línea. La excepción de distress (18 U.S.C. §2511(2)(g)) y el interés vital (GDPR art. 6.1.d) se citan en [regulatory.md](regulatory.md#recepción-pasiva-y-marco-legal) sin que esta guía constituya asesoría legal.

## Estado de evidencia

Recepción de probes/BT y decodificación rtl_433/ADS-B: `bench-validated` (comunitario). Vinculación de identidad bajo MAC randomization: degradada, declarada como limitación. Kismet como herramienta de rescate: `unverified` (sin casos SAR documentados). Kismet en SAR y toda integración OpenBREC de este dominio: `specified`/`simulated` hasta evidence pack. El addon `passive-rf-observation` (contrato + replay determinístico con pseudonimización y stripping verificados) queda en `simulated` (gate `rf-sensing-passive`, receipt en `evidence/rf-sensing/`).

## Qué no demuestra

Actividad de dispositivo no demuestra persona viva, identidad ni ubicación exacta; el silencio de dispositivos nunca demuestra ausencia de víctimas (un teléfono puede estar apagado, sin batería o destruido).

## Contratos normativos relacionados

Addon experimental [`passive-rf-observation`](../../schemas/addons/1.0.0/passive-rf-observation.schema.json) ([catálogo de addons](../../schemas/addons/catalog.json)), [Observation](../../schemas/core/1.0.0/observation.schema.json), [Marco regulatorio](regulatory.md) y [RF quieting](rf-quieting.md).
