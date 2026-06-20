"""Central configuration. All tunables/secrets are env-driven (constraint 14)."""
from __future__ import annotations

from datetime import timedelta, timezone
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLEAR_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Neon/Postgres connection string. MUST be overridden via CLEAR_DATABASE_URL in any real
    # environment; the localhost default only exists so imports/tests don't crash. Use the
    # Neon *pooler* host (ep-...-pooler...) so the serverless connection cap isn't exhausted.
    database_url: str = "postgresql://localhost:5432/clear"
    raw_data_dir: Path = Field(default=Path("data/raw"))
    model_dir: Path = Field(default=Path("data/models"))
    random_seed: int = 42
    operator_token: str = "dev-operator-token"
    citizen_token: str = "dev-citizen-token"
    # Comma-separated browser origins allowed to call the API (CORS). Browser apps served from
    # another origin are blocked unless their origin is listed here. Override via
    # CLEAR_CORS_ALLOW_ORIGINS in any deployed environment (add your Vercel/Render frontend URL).
    # Never use "*" in production.
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"
    # Rate limiting (fixed window, enforced per worker process). Caps requests per client per
    # window and returns HTTP 429 beyond that. Tune per environment; disable for load tests.
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    ingest_max_retries: int = 3
    ingest_backoff_base_seconds: float = 0.5
    ist_offset_minutes: int = 330  # +05:30 (constraint 4)
    sla_threshold_minutes: int = 60
    forecast_horizon_hours: int = 3
    hotspot_eps_meters: float = 150.0
    hotspot_min_samples: int = 5
    max_clearance_minutes: float = 1440.0
    drift_psi_threshold: float = 0.2

    # --- Phase 1: live weather enrichment (Open-Meteo, free, keyless) ---
    # Flag OFF by default => byte-for-byte the current backend. Set CLEAR_WEATHER_ENABLED=1
    # to populate rainfall_mm from real data.
    weather_enabled: bool = False
    weather_timeout_seconds: float = 2.5
    weather_archive_url: str = "https://archive-api.open-meteo.com/v1/archive"
    weather_forecast_url: str = "https://api.open-meteo.com/v1/forecast"

    # --- Phase 3: MuRIL multilingual severity embeddings (LOCAL / code-only) ---
    # Flag OFF by default => byte-for-byte the current backend. Set CLEAR_USE_MURIL=1 to
    # append PCA-reduced MuRIL text embeddings to the severity feature set. Intentionally NOT
    # wired into the Docker build or render.yaml; exercised locally only.
    use_muril: bool = False
    muril_model_name: str = "google/muril-base-cased"
    muril_cache_path: Path = Field(default=Path("data/models/muril_cache.joblib"))
    muril_pca_dims: int = 16
    muril_batch_size: int = 32
    muril_max_length: int = 64

    # --- Phase 4: planning & decision-support modules (additive, no model changes) ---
    # Forward-looking congestion multipliers by event type, applied by /events/impact to scale a
    # baseline clearance/risk. Tune from historical incident density. JSON string so it is
    # env-overridable via CLEAR_EVENT_MULTIPLIERS_JSON. Unknown types fall back to the default.
    event_multipliers_json: str = (
        '{"ipl_match": 2.3, "political_rally": 1.8, "concert": 2.0, '
        '"festival": 1.7, "marathon": 1.6, "vip_movement": 1.5, "normal": 1.0}'
    )
    event_multiplier_default: float = 1.0
    # Resource-planning heuristics (no ML; simple ratios).
    officers_per_attendees: int = 500
    barricades_per_closure: int = 4
    tow_per_attendees: int = 10000

    # --- Phase 5: live rain-clog risk (Weather Union, real-time hyperlocal observation) ---
    # Flag OFF by default => byte-for-byte the current backend. Set CLEAR_RAIN_CLOG_ENABLED=1 AND
    # provide CLEAR_WEATHER_UNION_API_KEY to expose GET /weather/rain-risk. Read-only enrichment:
    # no model retrain, no change to /ingest or any existing route. Weather Union is an OBSERVATION
    # (nowcast) API: rain_intensity (mm/min) + rain_accumulation (mm since 12 AM IST).
    rain_clog_enabled: bool = False
    weather_union_api_key: str = ""
    weather_union_base_url: str = "https://www.weatherunion.com/gw/weather/external/v0"
    weather_union_timeout_seconds: float = 2.5
    rain_clog_cache_seconds: int = 300  # upstream refreshes ~1/min; cache to respect daily quota
    # Representative lat/long per corridor (Weather Union returns data within ~2 km of its nearest
    # device). JSON => env-overridable via CLEAR_CORRIDOR_LATLON_JSON. Refine coords any time.
    corridor_latlon_json: str = (
        '{"mysore road": [12.9447, 77.5260], "bellary road": [13.0358, 77.5970], '
        '"tumkur road": [13.0280, 77.5190], "orr east": [12.9560, 77.7010], '
        '"orr west": [13.0280, 77.5050], "old madras road": [12.9920, 77.6720], '
        '"hosur road": [12.9100, 77.6390], "magadi road": [12.9760, 77.5360], '
        '"kanakapura road": [12.9120, 77.5600], "sarjapur road": [12.9180, 77.6810], '
        '"mg road": [12.9750, 77.6090], "brigade road": [12.9720, 77.6090], '
        '"residency road": [12.9690, 77.6010], "richmond road": [12.9620, 77.6010]}'
    )
    # Historical water-logging propensity per corridor (0..1): how flood-prone it is, used to weight
    # live rain into a corridor-specific score. Seeded defaults; refine from incidents.water_logging
    # density (helper SQL in §G). Env: CLEAR_CORRIDOR_WATERLOG_JSON.
    corridor_waterlog_json: str = (
        '{"mysore road": 0.45, "bellary road": 0.40, "tumkur road": 0.35, '
        '"orr east": 0.65, "orr west": 0.55, "old madras road": 0.50, '
        '"hosur road": 0.60, "magadi road": 0.30, "kanakapura road": 0.40, '
        '"sarjapur road": 0.70, "mg road": 0.45, "brigade road": 0.40, '
        '"residency road": 0.45, "richmond road": 0.40}'
    )
    corridor_waterlog_default: float = 0.4
    rain_intensity_ref_mm_per_min: float = 0.5  # intensity that alone implies high surface-water risk
    rain_accumulation_ref_mm: float = 40.0      # daily accumulation that alone implies high risk

    # --- Dedicated text-severity model served by /nlp/severity ---
    # Trained on ONLY text-derivable features so train == serve (no lat/lon/rainfall skew).
    severity_text_enabled: bool = True
    muril_text_pca_dims: int = 192          # richer than the structured model's 16
    severity_text_embed_dropout: float = 0.15  # zero embeddings on 30% of train rows (prod robustness)
    severity_text_max_iter: int = 2000      # MLP can train as long as it needs (early stopping guards it)
    severity_text_mlp_alpha: float = 1e-4
    severity_text_lr_c: float = 2.0

    @property
    def ist_tz(self) -> timezone:
        return timezone(timedelta(minutes=self.ist_offset_minutes))

    @property
    def cors_origins(self) -> list[str]:
        """Parsed allow-list from the comma-separated cors_allow_origins setting."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def event_multipliers(self) -> dict[str, float]:
        """Parsed event-type -> multiplier map (falls back to {'normal': 1.0} on bad JSON)."""
        import json
        try:
            data = json.loads(self.event_multipliers_json)
            return {str(k): float(v) for k, v in data.items()}
        except (ValueError, TypeError):
            return {"normal": 1.0}

    @property
    def corridor_latlon(self) -> dict[str, list[float]]:
        """Parsed corridor -> [lat, lon] map (empty on bad JSON)."""
        import json
        try:
            data = json.loads(self.corridor_latlon_json)
            return {str(k).strip().lower(): [float(v[0]), float(v[1])] for k, v in data.items()}
        except (ValueError, TypeError, IndexError, KeyError):
            return {}

    @property
    def corridor_waterlog(self) -> dict[str, float]:
        """Parsed corridor -> historical water-logging propensity 0..1 (empty on bad JSON)."""
        import json
        try:
            data = json.loads(self.corridor_waterlog_json)
            return {str(k).strip().lower(): float(v) for k, v in data.items()}
        except (ValueError, TypeError):
            return {}

    def ensure_dirs(self) -> None:
        # Postgres holds incident data now; we still keep local dirs for the raw CSV (ingest
        # source) and the trained joblib artifacts.
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    return Settings()
