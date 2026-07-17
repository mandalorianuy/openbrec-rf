import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const STORAGE_KEY = "openbrec:last-projection";

type Layer = "observation" | "evidence" | "fusion_result";
type Point = [number, number];

type ZoneSummary = {
  state: "abstained";
  confidence: number;
  coverage: string;
  capabilities_absent: string[];
  sources: string[];
  explanation: string;
};

type Zone = {
  zone_id: string;
  label: string;
  precision_m: number;
  polygon: Point[];
  summary: ZoneSummary;
};

type NodeProjection = {
  node_id: string;
  label: string;
  zone_id: string;
  position: Point;
  status: string;
  quality: number;
  boot_session: string;
  capabilities: string[];
  capabilities_absent: string[];
};

type TimelineEvent = {
  event_id: string;
  timestamp: string;
  zone_id: string;
  node_id?: string;
  layer: Layer;
  label: string;
  confidence: number;
};

type ProjectionResult = ZoneSummary & {
  result_id: string;
  timestamp: string;
  zone_id: string;
  precision: string;
};

type Projection = {
  scenario_id: string;
  generated_at: string;
  mode: string;
  semantic_layers: Layer[];
  zones: Zone[];
  nodes: NodeProjection[];
  tracks: { track_id: string; label: string; node_ids: string[]; points: Point[] }[];
  timeline: TimelineEvent[];
  results: ProjectionResult[];
  safety_notice: string;
};

const LAYER_LABEL: Record<Layer, string> = {
  observation: "Observación",
  evidence: "Evidencia",
  fusion_result: "Inferencia",
};

function loadCachedProjection(): Projection | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as Projection;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function formatTime(timestamp: string): string {
  return timestamp.slice(11, 19) + "Z";
}

function App() {
  const [projection, setProjection] = useState<Projection | null>(loadCachedProjection);
  const [selectedZone, setSelectedZone] = useState("zone-bravo");
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [layer, setLayer] = useState<Layer | "all">("all");

  useEffect(() => {
    fetch("/m0-projection.json")
      .then((response) => {
        if (!response.ok) throw new Error("projection unavailable");
        return response.json() as Promise<Projection>;
      })
      .then((value) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        setProjection(value);
      })
      .catch(() => {
        // The last verified projection remains available during a partition.
      });
  }, []);

  const filteredTimeline = useMemo(
    () => projection?.timeline.filter((item) => layer === "all" || item.layer === layer) ?? [],
    [projection, layer],
  );
  const result = projection?.results.find((item) => item.zone_id === selectedZone);
  const event = projection?.timeline.find((item) => item.event_id === selectedEvent);

  if (!projection) {
    return (
      <main className="loading-shell" aria-live="polite">
        <p className="kicker">OPENBREC RF · LAB-SIM</p>
        <h1>Cargando la última proyección local…</h1>
        <p>No se genera ninguna conclusión mientras faltan datos.</p>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="kicker">OPENBREC RF · LAB-SIM</p>
          <h1>Situación sintética</h1>
        </div>
        <div className="run-state" aria-label="Estado de la campaña">
          <span className="pulse" />
          <span>Replay offline</span>
          <time dateTime={projection.generated_at}>{formatTime(projection.generated_at)}</time>
        </div>
      </header>

      <p className="safety-notice" role="note">{projection.safety_notice}</p>

      <div className="workspace">
        <section className="map-panel" data-testid="operations-map" aria-labelledby="map-title">
          <div className="section-heading">
            <div>
              <p className="section-index">01 · COBERTURA</p>
              <h2 id="map-title">Mapa operacional</h2>
            </div>
            <p>3 zonas · 6 nodos · 2 tracks</p>
          </div>
          <svg className="operations-map" viewBox="0 0 100 100" role="img" aria-label="Mapa sintético de tres zonas">
            <defs>
              <pattern id="grid" width="5" height="5" patternUnits="userSpaceOnUse">
                <path d="M 5 0 L 0 0 0 5" fill="none" stroke="currentColor" strokeWidth=".18" />
              </pattern>
            </defs>
            <rect width="100" height="100" fill="url(#grid)" className="map-grid" />
            {projection.zones.map((zone) => (
              <polygon
                key={zone.zone_id}
                points={zone.polygon.map((point) => point.join(",")).join(" ")}
                className={`zone-shape ${selectedZone === zone.zone_id ? "selected" : ""}`}
                tabIndex={0}
                role="button"
                aria-label={`Seleccionar ${zone.label}`}
                onClick={() => setSelectedZone(zone.zone_id)}
                onKeyDown={(keyEvent) => {
                  if (keyEvent.key === "Enter" || keyEvent.key === " ") setSelectedZone(zone.zone_id);
                }}
              />
            ))}
            {projection.tracks.map((track) => (
              <polyline
                key={track.track_id}
                points={track.points.map((point) => point.join(",")).join(" ")}
                className="track-line"
              />
            ))}
            {projection.nodes.map((node) => (
              <g key={node.node_id} className={`map-node ${node.status}`}>
                <circle cx={node.position[0]} cy={node.position[1]} r="2.4" />
                <text x={node.position[0] + 3.2} y={node.position[1] + 1.2}>{node.label}</text>
              </g>
            ))}
          </svg>
          <div className="map-legend" aria-label="Leyenda del mapa">
            <span><i className="legend-dot reporting" /> Reportando</span>
            <span><i className="legend-dot degraded" /> Degradado</span>
            <span><i className="legend-dot lost" /> Sin reporte</span>
          </div>
        </section>

        <aside className="inspector" data-testid="semantic-inspector" aria-labelledby="inspector-title">
          <div className="section-heading compact">
            <div>
              <p className="section-index">02 · LECTURA</p>
              <h2 id="inspector-title">Inspector semántico</h2>
            </div>
          </div>
          {result && (
            <div className="result-inspection" aria-live="polite">
              <div className="result-state">
                <span>Inferencia consolidada</span>
                <strong>Abstención</strong>
              </div>
              <dl className="metric-list">
                <div><dt>Zona</dt><dd>{result.zone_id}</dd></div>
                <div><dt>Timestamp</dt><dd>{formatTime(result.timestamp)}</dd></div>
                <div><dt>Precisión</dt><dd>{result.precision}</dd></div>
                <div><dt>Confianza</dt><dd>{Math.round(result.confidence * 100)}%</dd></div>
                <div><dt>Cobertura</dt><dd>{result.coverage}</dd></div>
              </dl>
              <div className="explanation-block">
                <h3>Explicación</h3>
                <p>{result.explanation}</p>
              </div>
              <div className="list-block">
                <h3>Fuentes</h3>
                <p>{result.sources.join(" · ") || "Sin fuentes activas"}</p>
              </div>
              <div className="list-block absent">
                <h3>Capacidades ausentes</h3>
                <ul>{result.capabilities_absent.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              {event && (
                <div className="selected-event">
                  <span>{LAYER_LABEL[event.layer]}</span>
                  <strong>{event.label}</strong>
                  <small>{event.node_id ?? event.zone_id} · {Math.round(event.confidence * 100)}%</small>
                </div>
              )}
            </div>
          )}
        </aside>
      </div>

      <section className="capabilities" data-testid="capability-matrix" aria-labelledby="capabilities-title">
        <div className="section-heading">
          <div>
            <p className="section-index">03 · NODOS</p>
            <h2 id="capabilities-title">Matriz de capacidades</h2>
          </div>
          <p>Declarado, degradado y ausente permanecen separados</p>
        </div>
        <div className="capability-table" role="table" aria-label="Capacidades por nodo">
          <div className="table-row table-head" role="row">
            <span>Nodo</span><span>Estado</span><span>Disponible</span><span>Ausente</span><span>Calidad</span>
          </div>
          {projection.nodes.map((node) => (
            <div className="table-row" role="row" key={node.node_id}>
              <strong>{node.label}<small>{node.zone_id}</small></strong>
              <span className={`node-status ${node.status}`}>{node.status}</span>
              <span>{node.capabilities.join(", ")}</span>
              <span className="absent-text">{node.capabilities_absent.join(", ")}</span>
              <span>{Math.round(node.quality * 100)}%</span>
            </div>
          ))}
        </div>
      </section>

      <section className="timeline-panel" data-testid="event-timeline" aria-labelledby="timeline-title">
        <div className="section-heading">
          <div>
            <p className="section-index">04 · PROVENANCE</p>
            <h2 id="timeline-title">Timeline causal</h2>
          </div>
          <div className="layer-filters" aria-label="Filtrar nivel semántico">
            <button className={layer === "all" ? "active" : ""} onClick={() => setLayer("all")}>Todo</button>
            {projection.semantic_layers.map((item) => (
              <button key={item} className={layer === item ? "active" : ""} onClick={() => setLayer(item)}>
                {LAYER_LABEL[item]}
              </button>
            ))}
          </div>
        </div>
        <ol className="timeline">
          {filteredTimeline.map((item) => (
            <li key={item.event_id} className={item.layer}>
              <button onClick={() => { setSelectedZone(item.zone_id); setSelectedEvent(item.event_id); }}>
                <span className="timeline-time">{formatTime(item.timestamp)}</span>
                <span className="timeline-layer">{LAYER_LABEL[item.layer]}</span>
                <strong>{item.label}</strong>
                <small>{item.node_id ?? item.zone_id} · confianza {Math.round(item.confidence * 100)}%</small>
              </button>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
