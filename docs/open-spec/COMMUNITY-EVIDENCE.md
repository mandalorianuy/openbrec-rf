# Evidencia comunitaria

## Flujo

1. Crear un submission versionado contra el schema normativo.
2. Fijar spec, firmware, schemas y protocolos aplicables.
3. Declarar claim solicitado, limitaciones y resultados negativos.
4. Ejecutar gates offline y adjuntar receipts.
5. Solicitar reviews de seguridad, privacidad y safety.
6. Registrar la decisión como `accepted`, `rejected_with_record` o `superseded`.

## Conservación

Las decisiones son append-only. Un aporte rechazado, un ensayo fallido o un
resultado negativo no se descarta: queda vinculado para review y evita repetir
errores. La supersesión conserva el historial completo.

La vida y el posible distress preceden a la minimización destructiva. Durante
un incidente, material potencialmente vital puede quedar en un vault protegido
y acotado aun cuando sea sensible. El cierre del incidente exige una disposición
revisada, auditable y con receipt; no habilita retención indefinida.

## Promoción

`bench-validated` o `field-validated` requieren evidencia vigente de la versión
y combinación exactas (`lab_validated` y `field_validated` en contratos de
máquina). Un nombre comercial, una prueba de otra revisión o evidencia
comunitaria genérica no alcanza.
