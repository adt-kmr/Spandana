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
