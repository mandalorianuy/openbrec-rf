# Gateway autónomo de ResponseCell

## Alcance

Unidad local federable que funciona sin área, incidente, hub, cloud o backhaul.
La federación coordina; nunca reemplaza la autoridad local.

## Plano funcional

`logs/identidad/policy locales → resumen mínimo firmado → gateway outbound-only → peer/carry`

El MQTT local, claves de celda y payload crudo no cruzan la frontera.

## BOM por capacidades

- core local con log, trust y policy cache;
- gateway outbound-only opcional;
- custodia local durable y carry cifrado.

## Reutilización

Un servidor de incidente, equipo portátil o gateway heterogéneo existente puede
ocupar un rol si conserva namespaces por celda y peering explícito.

## Verificación

Retirar cada superior, inyectar hub hostil, probar trust stale y reconciliar
duplicados/conflictos sin overwrite, LWW ni pérdida silenciosa.

## Límites

No acredita capacidad masiva ni autoridad central. Exportar claves, aceptar SOS,
ordenar TX o sobrescribir el log desde un hub detiene el perfil.
