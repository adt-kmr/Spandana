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
    ingest_max_retries: int = 3
    ingest_backoff_base_seconds: float = 0.5
    ist_offset_minutes: int = 330  # +05:30 (constraint 4)
    sla_threshold_minutes: int = 60
    forecast_horizon_hours: int = 3
    hotspot_eps_meters: float = 150.0
    hotspot_min_samples: int = 5
    max_clearance_minutes: float = 1440.0
    drift_psi_threshold: float = 0.2

    @property
    def ist_tz(self) -> timezone:
        return timezone(timedelta(minutes=self.ist_offset_minutes))

    def ensure_dirs(self) -> None:
        # Postgres holds incident data now; we still keep local dirs for the raw CSV (ingest
        # source) and the trained joblib artifacts.
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings() -> Settings:
    return Settings()
