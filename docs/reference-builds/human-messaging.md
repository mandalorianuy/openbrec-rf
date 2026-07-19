# Receta: terminal de mensajería humana

## Objetivo
Proveer texto breve, estado, SOS y ubicación con seguridad de aplicación sobre un bearer sustituible.
## Audiencia
Constructores de terminales e integradores UX/red.
## Prerrequisitos
UI offline, identidad por incidente, claves, almacenamiento y transporte.
## Capacidades necesarias
Firma/MAC, TTL, retry, deduplicación, receipts append-only y revocación.
## Alternativas permitidas
Companions/radios Meshtastic, MeshCore, Reticulum/RNode, LoRaWAN privado, terminal serial o carry; todos reemplazables.
## Componentes e interfaces
`operador → UI → HumanMessage → envelope → adapter → lifecycle`.
## Pasos
Enrolar; eliminar defaults; configurar prioridades; enviar los cuatro tipos; probar restart/revocación; mostrar ACKs separados.
## Resultado esperado
Mensajes trazables sin delegar identidad o aceptación al fabricante.
## Validación mínima
Firma, TTL, duplicado, SOS no verificado, cancelación, restart y cero confirmaciones falsas.
## Fallos comunes y recuperación
Ante bearer caído encolar/carry; ante terminal perdido revocar/rekey; ante autenticidad fallida preservar para review.
## Safety, privacidad y preservación
No descartar distress ambiguo; limitar acceso y retención; no afirmar rescate.
## Estado de evidencia
Receta `specified`, lifecycle `simulated`, terminal físico `unverified`.
## Qué no demuestra
No demuestra cobertura, lectura, comprensión, respuesta ni rescate.
## Contratos normativos relacionados
[Mensajería](../../specs/openbrec/1.0.0-draft.1/messaging-interoperability-profiles.json) y [guía SOS](../guides/messaging-sos.md).
