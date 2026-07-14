# ADR-001: RuView como proveedor CSI opcional

- **Estado:** Accepted
- **Decisión:** integrar por adapter y fijar versión; no convertir RuView en core ni vendorizarlo por defecto.
- **Razón:** acelera firmware/streaming/model baselines, pero mantiene gaps y no está validado para escombros.
- **Consecuencia:** raw frames y replay permanecen autoritativos; toda inferencia es experimental y versionada.
