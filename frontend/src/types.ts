export type Health = {
  status: "ok";
  models: { severity: boolean; clearance: boolean; forecast: boolean };
};

export type IncidentRow = {
  event_id: string;
  payload_json: string;
  event_cause: string | null;
  corridor: string | null;
  priority: string | null;
  requires_road_closure: 0 | 1 | null;
  start_ist: string | null;
  resolved_ist: string | null;
  closed_ist: string | null;
  duration_minutes: number | null;
  event_observed: 0 | 1 | null;
  admin_close: 0 | 1 | null;
  junction_node: string | null;
  latitude: number | null;
  longitude: number | null;
  status: string | null;
  ingested_at: string | null;
};
export type IncidentsResponse = { count: number; incidents: IncidentRow[] };

export type CorridorRisk = {
  corridor: string;
  risk: number;
  horizon_hours: number;
  stale: boolean;
};
export type CorridorRiskResponse = {
  as_of_ist?: string;
  horizon_hours?: number;
  corridors: CorridorRisk[];
  note?: string;
};

export type HotspotCluster = {
  cluster_id: number;
  size: number;
  centroid_lat: number;
  centroid_lon: number;
  top_corridor: string | null;
};
export type HotspotsResponse = {
  clusters: HotspotCluster[];
  n_points: number;
  n_clusters: number;
  total_clusters?: number;
  returned?: number;
  eps_meters?: number;
  min_samples?: number;
  note?: string;
};

export type IngestResult = {
  event_id: string | null;
  written?: boolean;
  duplicate?: boolean;
  dead_lettered?: boolean;
  attempts: number;
};

export type SlaResponse = {
  sla_pct: number | null;
  resolved_subset_size: number;
  threshold_minutes: number;
  note: string;
};

export type ConfirmResponse = {
  confirmed: boolean;
  approval_event: {
    type: string;
    recommendation_id: number;
    operator_note: string;
    approved_at: string;
    autonomous_actuation: false;
  };
};

export type MetricsResponse = {
  clearance_error: unknown;
  history: { model: string; metric: string; value: number; created_at: string }[];
};

export type SeverityResult = Record<string, unknown>;
export type ClearanceResult = Record<string, unknown>;
export type DispatchSuggestion = {
  recommendation_id?: number;
  [k: string]: unknown;
};

export type DispatchUnit = { unit_id: string; lat: number; lon: number };
export type DispatchRequest = { units: DispatchUnit[]; max_incidents?: number };
export type ConfirmRequest = { recommendation_id: number; operator_note?: string };
export type CitizenReport = {
  corridor?: string;
  latitude: number;
  longitude: number;
  description?: string;
  event_cause?: string;
};
export type IngestPayload = {
  event_id: string;
  start_datetime: string;
  latitude: number;
  longitude: number;
  event_cause?: string;
  corridor?: string;
  priority?: "low" | "medium" | "high" | "critical";
  [k: string]: unknown;
};

export interface EventTypesResponse { event_types: string[]; }
export interface EventImpactRequest { event_type?: string; base_minutes?: number; base_risk?: number; }
export interface EventImpactResponse { event_type: string; multiplier: number; adjusted_clearance_minutes?: number; adjusted_risk?: number; }
export interface ResourcePlanRequest { attendees: number; road_closures?: number; event_type?: string; }
export interface ResourcePlanResponse { attendees: number; road_closures: number; event_type: string; multiplier: number; officers: number; officers_base: number; barricades: number; tow_trucks: number; note: string; }
export type DiversionRank = "primary" | "secondary";
export interface DiversionAlternate { corridor: string; rank: DiversionRank; delta_minutes: number; }
export interface DiversionsResponse { blocked_corridor: string; has_diversion: boolean; alternates: DiversionAlternate[]; note: string; }
export interface MetricsByEventRow { event_cause: string; mae_minutes: number; n: number; }
export interface MetricsByEventResponse { by_event: MetricsByEventRow[]; overall_mae_minutes: number; n: number; }

export type RainRisk = {
  corridor: string;
  available: boolean;            // false => grey out; multiplier is 1.0
  rain_clog_score: number;       // 0..100
  risk_band: "low" | "moderate" | "high" | "unknown";
  rain_multiplier: number;       // 1.0 .. 1.6 — fold into ETA like the event multiplier
  waterlog_weight?: number;      // corridor's historical flood propensity (0..1)
  stale?: boolean;               // served from cache on a transient upstream miss
  reason?: string;               // present when available is false
  rain?: {
    intensity: number;           // mm/min
    accumulation: number;        // mm since 12 AM IST
    temperature: number;         // °C
    humidity: number;            // %
    device_type: number | null;
    stale: boolean;
  };
};

export interface NlpSeverityRequest {
  text: string;
  event_cause?: string | null;
  corridor?: string;
  latitude?: number;
  longitude?: number;
  comment?: string;
}
export interface NlpSeverityResult {
  band: "low" | "medium" | "high" | "critical";
  confidence: number;
  source?: "precomputed" | "nearest" | "default";
}



