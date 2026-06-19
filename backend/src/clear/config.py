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

    @property
    def ist_tz(self) -> timezone:
        return timezone(timedelta(minutes=self.ist_offset_minutes))

    @property
    def cors_origins(self) -> list[str]:
        """Parsed allow-list from the comma-separated cors_allow_origins setting."""
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        # Postgres holds incident data now; we still keep local dirs for the raw CSV (ingest
        # source) and the trained joblib artifacts.
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    return Settings()
