# Terminal de mensajería humana off-grid

## Alcance

Texto breve, estado, SOS y ubicación con seguridad de aplicación por encima de
un bearer sustituible. No ofrece voz ni garantiza rescate.

## Plano funcional

`operador → UI offline → envelope firmado/cifrado → bearer adapter → receipts append-only`

Recepción técnica, lectura y aceptación operativa permanecen separadas.

## BOM por capacidades

- interfaz accesible offline;
- bearer off-grid con adapter y kill switch;
- identidad y claves por incidente con revocación local.

## Reutilización

Se pueden reutilizar companions y radios Meshtastic, MeshCore, Reticulum/RNode,
terminales seriales o carry bundles. Sus IDs y ACK no son identidad ni aceptación.

## Verificación

Probar firma, TTL, replay, revocación, SOS no verificado, cancelación, restart,
fallo del bearer y cero confirmaciones falsas.

## Límites

No acredita cobertura, entrega ni rescate. Nonce reuse, clave compartida/default
o aceptación sin actor autorizado detienen el perfil.
