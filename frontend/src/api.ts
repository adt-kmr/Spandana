import type {
  Health,
  IncidentsResponse,
  CorridorRiskResponse,
  HotspotsResponse,
  IngestResult,
  SlaResponse,
  ConfirmResponse,
  MetricsResponse,
  SeverityResult,
  ClearanceResult,
  DispatchSuggestion,
  DispatchRequest,
  ConfirmRequest,
  CitizenReport,
  IngestPayload,
  EventTypesResponse,
  EventImpactRequest,
  EventImpactResponse,
  ResourcePlanRequest,
  ResourcePlanResponse,
  DiversionsResponse,
  MetricsByEventResponse,
  RainRisk,
  NlpSeverityRequest,
  NlpSeverityResult,
} from './types';

const BASE = import.meta.env.VITE_CLEAR_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  body?: unknown;

  constructor(status: number, detail: string, body?: unknown) {
    super(`[${status}] ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

type Scope = "operator" | "citizen";
type Opts = {
  method?: "GET" | "POST";
  scope?: Scope;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  timeoutMs?: number;
};

import { getOperatorToken } from './auth';

function tokenFor(scope?: Scope): string | undefined {
  if (scope === "operator") {
    return getOperatorToken() || import.meta.env.VITE_CLEAR_OPERATOR_TOKEN;
  }
  if (scope === "citizen") return import.meta.env.VITE_CLEAR_CITIZEN_TOKEN;
  return undefined;
}

export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const { method = "GET", scope, body, query, timeoutMs = 20000 } = opts;

  const url = new URL(BASE + path);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = {};
  const token = tokenFor(scope);
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
  } catch (e) {
    throw new ApiError(0, e instanceof Error ? e.message : "network error");
  } finally {
    clearTimeout(timer);
  }

  const text = await res.text();
  let parsed: unknown = undefined;
  if (text) { try { parsed = JSON.parse(text); } catch { parsed = text; } }

  if (!res.ok) {
    const detail =
      parsed && typeof parsed === "object" && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : res.statusText || "request failed";
    throw new ApiError(res.status, detail, parsed);
  }
  return parsed as T;
}

export const ClearApi = {
  health: () => api<Health>("/healthz"),

  incidents: (limit = 100, scope: Scope = "operator") =>
    api<IncidentsResponse>("/incidents", { scope, query: { limit } }),
  corridorsRisk: (scope: Scope = "operator") =>
    api<CorridorRiskResponse>("/corridors/risk", { scope }),
  sla: (scope: Scope = "operator") => api<SlaResponse>("/sla", { scope }),

  hotspots: (minSize?: number, limit?: number) =>
    api<HotspotsResponse>("/hotspots", { scope: "operator", query: { min_size: minSize, limit } }),
  severity: (eventId: string) =>
    api<SeverityResult>(`/incidents/${encodeURIComponent(eventId)}/severity`, { scope: "operator" }),
  clearance: (eventId: string) =>
    api<ClearanceResult>(`/incidents/${encodeURIComponent(eventId)}/clearance`, { scope: "operator" }),
  ingest: (payload: IngestPayload) =>
    api<IngestResult>("/ingest", { method: "POST", scope: "operator", body: payload }),
  dispatchSuggest: (req: DispatchRequest) =>
    api<DispatchSuggestion>("/dispatch/suggest", { method: "POST", scope: "operator", body: req }),
  dispatchConfirm: (req: ConfirmRequest) =>
    api<ConfirmResponse>("/dispatch/confirm", { method: "POST", scope: "operator", body: req }),
  metrics: () => api<MetricsResponse>("/metrics", { scope: "operator" }),
  citizenReport: (payload: CitizenReport) =>
    api<{ report_accepted: boolean; event_id: string; written?: boolean }>("/citizen/report", { method: "POST", scope: "citizen", body: payload }),
  nlpSeverity: (body: NlpSeverityRequest) =>
    api<NlpSeverityResult>("/nlp/severity", { method: "POST", scope: "citizen", body }),
  eventTypes: (scope: Scope = "operator") =>
    api<EventTypesResponse>("/events/types", { scope }),
  eventImpact: (body: EventImpactRequest, scope: Scope = "operator") =>
    api<EventImpactResponse>("/events/impact", { method: "POST", scope, body }),
  resourcePlan: (body: ResourcePlanRequest) =>
    api<ResourcePlanResponse>("/resources/plan", { method: "POST", scope: "operator", body }),
  diversions: (corridor: string, scope: Scope = "operator") =>
    api<DiversionsResponse>("/diversions", { scope, query: { corridor } }),
  metricsByEvent: () =>
    api<MetricsByEventResponse>("/metrics/by-event", { scope: "operator" }),
  rainRisk: (corridor: string, scope: Scope = "operator") =>
    api<RainRisk>("/weather/rain-risk", { scope, query: { corridor } }),
};
