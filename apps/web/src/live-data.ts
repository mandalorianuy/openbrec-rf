export type DataSource = "live" | "fixture";

export type LiveFusionResult = {
  result_id: string;
  state: "indicator" | "conflicted" | "abstained";
  zone_id?: string;
  window_start: string;
  window_end: string;
  confidence: number;
  coverage: string;
  abstained: boolean;
  abstention_reasons: string[];
  capabilities_absent: string[];
  explanation: string;
};

export type FusionFeed = {
  source: DataSource;
  results: LiveFusionResult[];
};

const API_BASE: string = import.meta.env.VITE_API_BASE ?? "/api";
const FETCH_TIMEOUT_MS = 3000;

export async function loadFusionResults(limit = 20): Promise<FusionFeed> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}/v1/fusion-results?limit=${limit}`, {
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("fusion results unavailable");
    const body = (await response.json()) as { items?: LiveFusionResult[] };
    if (!Array.isArray(body.items)) throw new Error("unexpected fusion payload");
    return { source: "live", results: body.items };
  } catch {
    // Offline-first: without the API the verified fixtures remain the source.
    return { source: "fixture", results: [] };
  } finally {
    clearTimeout(timer);
  }
}
