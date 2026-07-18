# Energía de sitio sustituible

## Alcance

Dominio energético local para cargas L0–L3. Solar, red, generador, vehículo y
reemplazo manual son fuentes opcionales; ninguna implica operación perpetua.

## Plano funcional

`fuente opcional → protección/control → almacenamiento → distribución protegida → cargas`

Cada rama puede aislarse y el estado energético se publica sin convertir una
estimación en garantía de autonomía.

## BOM por capacidades

- almacenamiento protegido con Wh utilizables declarados;
- distribución DC con fusible, polaridad y desconexión por rama;
- fuente de reposición opcional con controlador compatible.

## Reutilización

Una estación portátil, batería protegida o infraestructura existente puede
ocupar esos roles si declara límites, conectores, restart y modo de aislamiento.

## Verificación

Inspeccionar polaridad/protecciones, reproducir el load profile y ensayar
brownout, reserva SOS, apagado seguro y recuperación manual.

## Límites

No acredita 72 horas, sostenibilidad, vida útil ni seguridad del conjunto sin
medición exacta. Daño, temperatura anormal o backfeed inseguro detienen el uso.
