# Planificación del deployment

## Objetivo

Convertir una misión en celdas autónomas, capacidades, roles, energía, cobertura tentativa y degradaciones explícitas.

## Audiencia

Líderes de equipo, responsables técnicos y planificadores BREC/USAR.

## Prerrequisitos

Objetivo de misión, mapa aproximado, cantidad de equipos, restricciones de energía/radio y responsables de safety y datos.

## Capacidades necesarias

Comunicación local, persistencia, reloj, energía, operación ante partición y un inventario de nodos/roles.

## Alternativas permitidas

Kit independiente, una o varias ResponseCells, áreas con hubs opcionales o carry bundles. Ningún nivel superior es obligatorio para que el inferior opere.

## Componentes e interfaces

`Node`, `Team`, `ResponseCell`, `OperationalArea` e `IncidentFederation`; adapters de transporte, energía, almacenamiento y sincronización.

## Pasos

1. Estimar operadores, edificios/sectores y mensajes críticos por ventana.
2. Dividir en celdas que puedan operar aisladas y asignar roles locales.
3. Seleccionar topología y airtime budget por plano humano/máquina.
4. Calcular cargas críticas y degradables; reservar energía para SOS y apagado seguro.
5. Planear ubicación, cobertura tentativa y fallback físico/carry.
6. Definir partición, reconciliación, deduplicación y conflictos.
7. Registrar riesgos: congestión, near-far, pérdida de nodos, claves, privacidad y jurisdicción.
8. Ensayar sintéticamente la topología antes de cualquier despliegue.

## Resultado esperado

Un deployment manifest con celdas, roles, capacidades, alternativas, prioridades, degradaciones y criterios de stop/go.

## Validación mínima

Simular pérdida de hub y comprobar que cada ResponseCell conserva mensajería crítica, identidad local y replay; luego simular reconciliación sin duplicar SOS.

## Fallos comunes y recuperación

Una topología demasiado centralizada pierde utilidad al partirse: reducir dependencias y replicar lo crítico. Si el airtime no cierra, bajar telemetría, separar canales o añadir bearers; nunca degradar silenciosamente SOS.

## Safety, privacidad y preservación

La preservación de vida tiene prioridad. Aplicar minimización y acceso por rol, manteniendo evidencia crítica en cuarentena/review cuando no puede verificarse.

## Estado de evidencia

La jerarquía está `specified` y tiene escenarios `simulated`; cada deployment real queda `unverified` hasta su evidencia.

## Qué no demuestra

Un plan no acredita cobertura, regulación, capacidad RF, comprensión humana, seguridad eléctrica ni field readiness.

## Contratos normativos relacionados

[Federación](../../specs/openbrec/1.0.0-draft.1/recursive-federation-profiles.json), [energía](../../specs/openbrec/1.0.0-draft.1/energy-architecture-profiles.json) y [transportes](../../specs/openbrec/1.0.0-draft.1/multi-bearer-transport-profiles.json).
