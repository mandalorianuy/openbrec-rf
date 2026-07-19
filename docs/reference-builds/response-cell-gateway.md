# Receta: gateway autónomo de ResponseCell

## Objetivo
Federar una célula sin volverla dependiente de área, hub, cloud o backhaul.
## Audiencia
Integradores de edge, storage y federación.
## Prerrequisitos
Core local, namespaces, trust/policy y journal durable.
## Capacidades necesarias
Log local, gateway outbound opcional, carry cifrado, health y reconciliación.
## Alternativas permitidas
Laptop, SBC o servidor existente; backhaul RF, IP o carry, todos reemplazables.
## Componentes e interfaces
`log/identidad/policy → resumen firmado → gateway outbound → peer/carry`; claves y payload crudo quedan locales.
## Pasos
Crear namespace; fijar scopes; instalar gateway; retirar cada superior; inyectar duplicados/conflictos; ensayar carry y rollback.
## Resultado esperado
La ResponseCell opera sola y sincroniza resúmenes/provenance cuando vuelve el enlace.
## Validación mínima
Hub caído/hostil, trust stale, duplicados y conflictos sin overwrite, LWW ni pérdida silenciosa.
## Fallos comunes y recuperación
Si el hub ordena operaciones locales, cortar esa dependencia; ante trust stale aislar sync y continuar local.
## Safety, privacidad y preservación
No exportar claves ni aceptar SOS desde el hub como estado final; preservar el log original.
## Estado de evidencia
Receta `specified`, reconciliación `simulated`, gateway físico `unverified`.
## Qué no demuestra
No demuestra capacidad masiva, seguridad física, disponibilidad ni autoridad central.
## Contratos normativos relacionados
[Federación](../../specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json) y [guía](../guides/federation.md).
