"""Offline one-time weather backfill for the training CSV (Phase 1).

Run LOCALLY (never in the Docker build) so the build stays network-free:

    CLEAR_WEATHER_ENABLED=1 PYTHONPATH=backend/src \
        .venv/bin/python -m clear.backfill_weather --csv backend/data/raw/incidents.csv

Fills rainfall_mm only where it is missing/zero, writes the CSV back, then you retrain so the
models pick up the now-varying feature. Idempotent: rows that already have a positive value are
left alone, so re-runs only fill gaps.
"""
from __future__ import annotations

import argparse

import pandas as pd

from .config import get_settings
from .logging_setup import configure_logging
from .preprocessing import parse_utc
from .weather import rainfall_for

log = configure_logging()

def backfill(csv_path: str) -> dict:
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    cols = {c.lower(): c for c in df.columns}
    lat_c, lon_c = cols.get("latitude"), cols.get("longitude")
    start_c = cols.get("start_datetime") or cols.get("created_datetime")
    rain_c = cols.get("rainfall_mm")
    if not (lat_c and lon_c and start_c):
        raise SystemExit("CSV missing latitude/longitude/start_datetime columns")
    if rain_c is None:
        rain_c = "rainfall_mm"
        df[rain_c] = ""
    filled = skipped = 0
    new_vals: list[str] = []
    for _, row in df.iterrows():
        cur = str(row.get(rain_c, "")).strip()
        try:
            if cur and float(cur) > 0:
                new_vals.append(cur); skipped += 1; continue
        except ValueError:
            pass
        try:
            lat, lon = float(row[lat_c]), float(row[lon_c])
        except (TypeError, ValueError):
            new_vals.append(cur or "0.0"); skipped += 1; continue
        mm = rainfall_for(lat, lon, parse_utc(row[start_c]))
        new_vals.append(f"{mm:.2f}"); filled += 1
    df[rain_c] = new_vals
    df.to_csv(csv_path, index=False)
    return {"rows": len(df), "filled": filled, "skipped": skipped, "csv": csv_path}

def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Backfill rainfall_mm from Open-Meteo.")
    parser.add_argument("--csv", default=str(settings.raw_data_dir / "incidents.csv"))
    args = parser.parse_args()
    if not settings.weather_enabled:
        log.warning("CLEAR_WEATHER_ENABLED not set; rainfall_for returns 0.0. "
                    "Set CLEAR_WEATHER_ENABLED=1 to actually fetch.")
    print(backfill(args.csv))

if __name__ == "__main__":
    main()
