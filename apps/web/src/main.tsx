import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { loadFusionResults } from "./live-data";
import type { FusionFeed } from "./live-data";
import "./style.css";

const STORAGE_KEY = "openbrec:last-projection";
const TERMINAL_FIXTURE_KEY = "openbrec:terminal-fixture";
const TERMINAL_MESSAGES_KEY = "openbrec:terminal-messages";

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

type TerminalMessageType = "text" | "status" | "sos" | "location";
type TerminalState = "queued" | "sent" | "delivered" | "seen" | "accepted" | "cancelled" | "expired";
type TerminalEvent = { event_id: string; event_type: string; occurred_at: string };
type PathReceipt = { receipt_id: string; kind: string; result: string };
type TerminalMessage = {
  message_id: string;
  message_type: TerminalMessageType;
  recipient: string;
  preview: string;
  created_at: string;
  expires_at: string;
  uncertainty: string;
  event_log: TerminalEvent[];
  path_receipts: PathReceipt[];
};
type TerminalProjection = {
  scenario_id: string;
  logical_now: string;
  claim_scope: string;
  connectivity: {
    bearer_state: string;
    partition_started_at: string;
    queue_gap_visible: boolean;
    gap_reason: string;
  };
  terminal_capability: {
    support_status: string;
    offline_actions: string[];
    capabilities_absent: string[];
    limitations: string[];
  };
  coverage: {
    label: string;
    location_zone: string;
    location_uncertainty_m: number;
    last_bearer_receipt_at: string;
  };
  safety_copy: { acceptance: string; silence: string; queue: string; cancel: string };
  messages: TerminalMessage[];
};

const LAYER_LABEL: Record<Layer, string> = {
  observation: "Observación",
  evidence: "Evidencia",
  fusion_result: "Inferencia",
};

const STATE_LABEL: Record<TerminalState, string> = {
  queued: "En cola local",
  sent: "Enviado · sin entrega confirmada",
  delivered: "Recibido por gateway",
  seen: "Visto por operador",
  accepted: "Aceptado por operador",
  cancelled: "Cancelación solicitada",
  expired: "Vencido · historial conservado",
};

const TYPE_LABEL: Record<TerminalMessageType, string> = {
  text: "Texto breve",
  status: "Estado",
  sos: "SOS",
  location: "Ubicación",
};

const ACTION_LABEL: Record<TerminalMessageType, string> = {
  text: "Encolar texto",
  status: "Compartir estado",
  sos: "Encolar SOS",
  location: "Compartir ubicación",
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

function loadCachedTerminal(): TerminalProjection | null {
  const stored = localStorage.getItem(TERMINAL_FIXTURE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as TerminalProjection;
  } catch {
    localStorage.removeItem(TERMINAL_FIXTURE_KEY);
    return null;
  }
}

function deriveTerminalState(message: TerminalMessage): TerminalState {
  const events = new Set(message.event_log.map((item) => item.event_type));
  if (events.has("operator.accepted")) return "accepted";
  if (events.has("sos.cancel_requested")) return "cancelled";
  if (events.has("sos.expired") || events.has("sos.failed")) return "expired";
  if (events.has("operator.seen")) return "seen";
  if (events.has("gateway.received")) return "delivered";
  if (events.has("transport.transmitted")) return "sent";
  return "queued";
}

function TerminalWorkspace({ terminal }: { terminal: TerminalProjection }) {
  const [messages, setMessages] = useState<TerminalMessage[]>(() => {
    const stored = localStorage.getItem(TERMINAL_MESSAGES_KEY);
    if (!stored) return terminal.messages;
    try {
      return JSON.parse(stored) as TerminalMessage[];
    } catch {
      localStorage.removeItem(TERMINAL_MESSAGES_KEY);
      return terminal.messages;
    }
  });
  const [messageType, setMessageType] = useState<TerminalMessageType>("text");
  const [text, setText] = useState("");
  const [status, setStatus] = useState("Equipo operativo");
  const [sosConfirmed, setSosConfirmed] = useState(false);

  useEffect(() => {
    localStorage.setItem(TERMINAL_MESSAGES_KEY, JSON.stringify(messages));
  }, [messages]);

  const queued = messages.filter((message) => deriveTerminalState(message) === "queued");
  const createMessage = (event: React.FormEvent) => {
    event.preventDefault();
    if (messageType === "sos" && !sosConfirmed) return;
    const now = new Date().toISOString();
    const preview = messageType === "location"
      ? `${terminal.coverage.location_zone} · ±${terminal.coverage.location_uncertainty_m} m · última ubicación conocida`
      : messageType === "status" ? status : messageType === "sos" ? "SOS · asistencia requerida" : text.trim();
    if (!preview) return;
    const messageId = crypto.randomUUID();
    const createdEvent = messageType === "sos" ? "sos.created" : "message.created";
    const queuedEvent = messageType === "sos" ? "sos.queued" : "message.queued";
    const next: TerminalMessage = {
      message_id: messageId,
      message_type: messageType,
      recipient: messageType === "sos" ? "role:rescue-command" : "role:cell-lead",
      preview,
      created_at: now,
      expires_at: new Date(Date.now() + (messageType === "sos" ? 15 : 60) * 60_000).toISOString(),
      uncertainty: "bearer particionado; entrega desconocida",
      event_log: [
        { event_id: crypto.randomUUID(), event_type: createdEvent, occurred_at: now },
        { event_id: crypto.randomUUID(), event_type: queuedEvent, occurred_at: now },
      ],
      path_receipts: [{ receipt_id: crypto.randomUUID(), kind: "local_queue", result: "preserved" }],
    };
    setMessages((current) => [next, ...current]);
    setText("");
    setSosConfirmed(false);
  };

  const cancelSos = (messageId: string) => {
    const now = new Date().toISOString();
    setMessages((current) => current.map((message) => message.message_id === messageId
      ? {
          ...message,
          event_log: [...message.event_log, {
            event_id: crypto.randomUUID(),
            event_type: "sos.cancel_requested",
            occurred_at: now,
          }],
        }
      : message));
  };

  return (
    <section className="terminal-workspace" data-testid="offline-terminal" aria-labelledby="terminal-title">
      <div className="terminal-status-strip" role="status">
        <div>
          <strong>Partición activa</strong>
          <span>{terminal.connectivity.gap_reason}</span>
        </div>
        <dl>
          <div><dt>Bearer</dt><dd>{terminal.connectivity.bearer_state}</dd></div>
          <div><dt>Cola activa</dt><dd>{queued.length} mensajes</dd></div>
          <div><dt>Cobertura</dt><dd>{terminal.coverage.label}</dd></div>
        </dl>
      </div>

      <div className="terminal-grid">
        <form className="message-composer" data-testid="message-composer" onSubmit={createMessage} aria-describedby="composer-help">
          <div className="section-heading compact">
            <div>
              <p className="section-index">01 · EMITIR</p>
              <h2 id="terminal-title">Mensaje local</h2>
            </div>
          </div>
          <fieldset className="message-types">
            <legend>Tipo de mensaje</legend>
            {(["text", "status", "sos", "location"] as TerminalMessageType[]).map((type) => (
              <label key={type} className={messageType === type ? "selected" : ""}>
                <input type="radio" name="message-type" value={type} checked={messageType === type} onChange={() => setMessageType(type)} />
                <span>{TYPE_LABEL[type]}</span>
              </label>
            ))}
          </fieldset>

          {messageType === "text" && (
            <label className="field-label">Mensaje breve
              <textarea value={text} maxLength={160} onChange={(event) => setText(event.target.value)} placeholder="Qué necesitás o qué cambió" required />
              <small>{text.length}/160</small>
            </label>
          )}
          {messageType === "status" && (
            <label className="field-label">Estado predefinido
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option>Equipo operativo</option>
                <option>Necesitamos asistencia</option>
                <option>Replegando a punto seguro</option>
              </select>
            </label>
          )}
          {messageType === "location" && (
            <div className="location-preview" role="note">
              <strong>{terminal.coverage.location_zone}</strong>
              <span>Última ubicación conocida · incertidumbre ±{terminal.coverage.location_uncertainty_m} m</span>
              <small>Capacidad ausente: GNSS en vivo</small>
            </div>
          )}
          {messageType === "sos" && (
            <div className="sos-confirmation">
              <p>El SOS quedará preservado localmente aunque no exista bearer.</p>
              <label>
                <input type="checkbox" checked={sosConfirmed} onChange={(event) => setSosConfirmed(event.target.checked)} />
                <span>Confirmo que deseo encolar un SOS</span>
              </label>
            </div>
          )}
          <p id="composer-help" className="composer-help">{terminal.safety_copy.queue}</p>
          <button className={`primary-action ${messageType === "sos" ? "distress" : ""}`} type="submit" disabled={(messageType === "text" && !text.trim()) || (messageType === "sos" && !sosConfirmed)}>
            {ACTION_LABEL[messageType]}
          </button>
        </form>

        <aside className="queue-panel" data-testid="message-queue" aria-labelledby="queue-title" aria-live="polite">
          <div className="section-heading compact">
            <div>
              <p className="section-index">02 · PENDIENTE</p>
              <h2 id="queue-title">Cola local</h2>
            </div>
            <strong className="queue-count">{queued.length}</strong>
          </div>
          <p className="queue-gap"><strong>Gap visible:</strong> {terminal.connectivity.gap_reason}</p>
          {queued.length === 0 ? <p className="empty-state">No hay mensajes pendientes.</p> : (
            <ol className="queue-list">
              {queued.map((message) => (
                <li key={message.message_id}>
                  <div><span>{TYPE_LABEL[message.message_type]}</span><strong>{message.preview}</strong></div>
                  <small>{STATE_LABEL.queued} · vence {formatTime(message.expires_at)}</small>
                  {message.message_type === "sos" && <button type="button" onClick={() => cancelSos(message.message_id)}>Solicitar cancelación</button>}
                </li>
              ))}
            </ol>
          )}
        </aside>
      </div>

      <div className="terminal-safety-copy" role="note">
        <p>{terminal.safety_copy.acceptance}</p>
        <p>{terminal.safety_copy.silence}</p>
        <p>{terminal.safety_copy.cancel}</p>
      </div>

      <section className="message-history" data-testid="message-history" aria-labelledby="history-title">
        <div className="section-heading">
          <div><p className="section-index">03 · TRAZABILIDAD</p><h2 id="history-title">Historial derivado</h2></div>
          <p>El estado se calcula desde eventos; nunca se edita directamente.</p>
        </div>
        <ol>
          {messages.map((message) => {
            const state = deriveTerminalState(message);
            return (
              <li key={message.message_id} className={message.message_type === "sos" ? "distress" : ""}>
                <div className="history-main">
                  <span>{TYPE_LABEL[message.message_type]}</span>
                  <strong>{message.preview}</strong>
                  <small>{message.uncertainty}</small>
                </div>
                <div className="history-state">
                  <strong className={`state-label ${state}`}>{STATE_LABEL[state]}</strong>
                  <small>{message.event_log.length} eventos · {message.path_receipts.length} recibos</small>
                  <time dateTime={message.expires_at}>Vence {formatTime(message.expires_at)}</time>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="terminal-capabilities" aria-labelledby="terminal-capabilities-title">
        <div><p className="section-index">04 · LÍMITES</p><h2 id="terminal-capabilities-title">Capacidades ausentes</h2></div>
        <ul>{terminal.terminal_capability.capabilities_absent.map((item) => <li key={item}>{item}</li>)}</ul>
        <p>Soporte {terminal.terminal_capability.support_status}. Las pruebas automáticas no acreditan comprensión humana ni uso en campo.</p>
      </section>
    </section>
  );
}

function formatTime(timestamp: string): string {
  return timestamp.slice(11, 19) + "Z";
}

function App() {
  const [projection, setProjection] = useState<Projection | null>(loadCachedProjection);
  const [terminal, setTerminal] = useState<TerminalProjection | null>(loadCachedTerminal);
  const [fusionFeed, setFusionFeed] = useState<FusionFeed>({ source: "fixture", results: [] });
  const [view, setView] = useState<"terminal" | "situation">("terminal");
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
    fetch("/p0-terminal.json")
      .then((response) => {
        if (!response.ok) throw new Error("terminal projection unavailable");
        return response.json() as Promise<TerminalProjection>;
      })
      .then((value) => {
        localStorage.setItem(TERMINAL_FIXTURE_KEY, JSON.stringify(value));
        setTerminal(value);
      })
      .catch(() => {
        // The local terminal fixture and queued messages survive a partition.
      });
    loadFusionResults().then(setFusionFeed);
  }, []);

  const filteredTimeline = useMemo(
    () => projection?.timeline.filter((item) => layer === "all" || item.layer === layer) ?? [],
    [projection, layer],
  );
  const result = projection?.results.find((item) => item.zone_id === selectedZone);
  const event = projection?.timeline.find((item) => item.event_id === selectedEvent);

  if (!projection || !terminal) {
    return (
      <main className="loading-shell" aria-live="polite">
        <p className="kicker">OPENBREC RF · LAB-SIM</p>
        <h1>Cargando el estado local…</h1>
        <p>No se genera ninguna conclusión mientras faltan datos.</p>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="kicker">OPENBREC RF · LAB-SIM</p>
          <h1>{view === "terminal" ? "Terminal offline" : "Situación sintética"}</h1>
        </div>
        <div className="topbar-actions">
          <nav className="view-switcher" aria-label="Vistas principales">
            <button className={view === "terminal" ? "active" : ""} onClick={() => setView("terminal")}>Terminal</button>
            <button className={view === "situation" ? "active" : ""} onClick={() => setView("situation")}>Situación</button>
          </nav>
          <div className="run-state" aria-label={view === "terminal" ? "Estado de conectividad" : "Estado de la campaña"}>
            <span className="pulse" />
            <span>{view === "terminal" ? "Partición activa" : "Replay offline"}</span>
            <time dateTime={view === "terminal" ? terminal.logical_now : projection.generated_at}>{formatTime(view === "terminal" ? terminal.logical_now : projection.generated_at)}</time>
          </div>
          <span className={`data-source ${fusionFeed.source}`} role="status">
            Fuente: {fusionFeed.source === "live" ? "API en vivo" : "fixtures verificados"}
          </span>
        </div>
      </header>

      <p className="safety-notice" role="note">{view === "terminal" ? terminal.safety_copy.acceptance : projection.safety_notice}</p>

      {view === "terminal" && <TerminalWorkspace terminal={terminal} />}

      {view === "situation" && <>
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

      {fusionFeed.results.length > 0 && (
      <section className="timeline-panel" data-testid="live-fusion-feed" aria-labelledby="live-fusion-title">
        <div className="section-heading">
          <div>
            <p className="section-index">05 · API EN VIVO</p>
            <h2 id="live-fusion-title">Fusión del pipeline</h2>
          </div>
          <p>Leído de la API local; las abstenciones se muestran sin interpretar.</p>
        </div>
        <ol className="timeline">
          {fusionFeed.results.map((item) => (
            <li key={item.result_id} className="fusion_result">
              <div className="history-main">
                <span>{item.abstained ? "Abstención" : item.state === "conflicted" ? "Conflicto" : "Indicador"}</span>
                <strong>{item.explanation}</strong>
                <small>{item.zone_id ?? "sin zona"} · confianza {Math.round(item.confidence * 100)}% · {item.coverage}</small>
                {item.abstention_reasons.length > 0 && <small>Razones: {item.abstention_reasons.join(" · ")}</small>}
              </div>
            </li>
          ))}
        </ol>
      </section>
      )}
      </>}
    </main>
  );
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
