import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

const STORAGE_KEY = "openbrec:last-projection";

type Projection = { status: "unknown" | "available"; explanation: string };

function loadProjection(): Projection {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) {
    return {
      status: "unknown",
      explanation: "Sin proyección todavía. Unknown no significa ausencia.",
    };
  }
  try {
    return JSON.parse(stored) as Projection;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return { status: "unknown", explanation: "Proyección local inválida." };
  }
}

function App() {
  const projection = loadProjection();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(projection));
  return (
    <main>
      <p className="eyebrow">LAB-SIM · OFFLINE</p>
      <h1>OpenBREC RF</h1>
      <section aria-live="polite">
        <h2>Última proyección local</h2>
        <p className="status">{projection.status}</p>
        <p>{projection.explanation}</p>
      </section>
      <p className="warning">
        Los indicios requieren fuentes y confianza. El silencio de un sensor nunca
        descarta vida.
      </p>
    </main>
  );
}

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js"));
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>,
);
