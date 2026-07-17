# Protocolo P1a — comprensión y operación de terminal offline

- Estado: planificado; no ejecutado en P0
- Owner: `product-ux-reviewer`
- Reviewer: `privacy-safety-reviewer`
- Participantes: 8 operadores/rescatistas y 8 personas no preparadas
- Evidencia P0: sólo checks automáticos de semántica, browser y accesibilidad técnica

## Objetivo

Comprobar, con consentimiento y protección de participantes, que la terminal se
puede operar bajo pérdida de red sin crear falsas expectativas de entrega,
arribo, rescate o ausencia. Este protocolo no puede completarse con datos
sintéticos ni por un agente automatizado.

## Tareas críticas

1. Encolar y revisar un texto breve durante una partición.
2. Compartir estado y ubicación con incertidumbre visible.
3. Emitir un SOS mediante confirmación explícita y explicar cada estado.
4. Solicitar cancelación y demostrar que el SOS y sus recibos no se borraron.
5. Explicar que `accepted` no garantiza arribo ni rescate.
6. Explicar que silencio o falta de respuesta no implica ausencia.
7. Identificar bearer perdido, cola, expiry y capacidades ausentes.
8. Completar los flujos con teclado/touch, guantes, ruido y alto contraste.

## Aceptación

- 8/8 operadores y 8/8 personas no preparadas reciben el mismo briefing.
- 100% comprende las dos red lines después del briefing.
- Al menos 90% completa cada flujo crítico sin ayuda.
- Hay cero SOS o cancelaciones accidentales durante el guion.
- Ninguna acción crítica depende sólo de color, audio o vibración.
- Se ejecutan checks WCAG 2.2 AA manuales además de los automáticos.
- Todo error, abandono o interpretación incorrecta se conserva para review.

## Stop conditions

Un participante que interprete `accepted` como rescate garantizado, silencio
como ausencia o cancelación como borrado fuerza rediseño y repetición. P0 no
puede completar ni simular este receipt humano.
