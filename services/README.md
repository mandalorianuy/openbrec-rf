# Servicios M0

Los placeholders históricos fueron sustituidos en M0-03 por implementaciones bajo `apps/`:

- `apps/api`: FastAPI con health, readiness e ingreso de `Observation` validado contra JSON Schema;
- `apps/fusion-worker`: worker asyncio que revalida mensajes antes de procesarlos;
- `apps/web`: shell React/TypeScript/Vite instalable y cacheable offline.

Mosquitto y PostgreSQL sólo están disponibles dentro de la red Docker interna `lab-core`. Este runtime es de laboratorio y no es un perfil de campo.

Los collectors y addons documentados no se descartaron: permanecen en specs, matrices y backlog, pero no aparecen como servicios ejecutables hasta cerrar M0 y sus gates específicos.
