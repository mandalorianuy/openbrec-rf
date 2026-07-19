> ⚠️ Documento histórico — corresponde a la encarnación Wi-Fi-CSI previa del proyecto. Sin autoridad normativa. Ver [docs/legacy/README.md](README.md).

# Requisitos resumidos

## Funcionales
- Registro offline de incidentes, zonas, vacíos, nodos, capacidades y antenas.
- Ingesta modular de Wi-Fi pasivo, BLE y CSI; SDR/BFI/UWB/mmWave como plugins.
- Cadena Observation → Evidence → FusionResult.
- Confianza, conflicto, expiración y abstención.
- Mapa de sectores, timeline, salud y replay.
- Exportación firmada de informe y paquete de evidencia.

## No funcionales
- ARM64 y x86-64.
- Inicio offline en menos de cinco minutos.
- Al menos 50 eventos/s por nodo y 12 nodos en hardware común.
- Store-and-forward y recuperación tras pérdida de backhaul.
- Ningún payload ni identificador directo persistido.
- Contenedores non-root, SBOM, secret scan y actualizaciones firmadas.
