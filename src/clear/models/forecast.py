"""3-hour corridor nowcast: short-horizon incident-rate risk (constraint 6).

Strictly a 3-hour-ahead nowcast. No long-horizon / multi-year forecasting anywhere.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from ..config import get_settings

MODEL_NAME = "forecast"
_FEATURES = ["lag1", "lag2", "lag3", "roll3", "hour", "dow", "corridor_freq"]

def hourly_counts(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-corridor hourly incident counts, gap-filled with zeros."""
    df = frame.dropna(subset=["start_ist"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["corridor", "hour_bucket", "count"])
    df["ts"] = pd.to_datetime(df["start_ist"], errors="coerce")
    df = df.dropna(subset=["ts"])
    grp = df.groupby(["corridor", df["ts"].dt.floor("h")]).size().rename("count")
    grp = grp.reset_index().rename(columns={"ts": "hour_bucket"})
    panels = []
    for corridor, g in grp.groupby("corridor"):
        g = g.set_index("hour_bucket").sort_index()
        full = pd.date_range(g.index.min(), g.index.max(), freq="h")
        g = g.reindex(full, fill_value=0)
        g.index.name = "hour_bucket"
        g = g.reset_index()
        g["corridor"] = corridor
        panels.append(g[["corridor", "hour_bucket", "count"]])
    return pd.concat(panels, ignore_index=True)

def _supervised(panel: pd.DataFrame, horizon: int, freq_map: dict) -> pd.DataFrame:
    rows = []
    for corridor, g in panel.groupby("corridor"):
        g = g.sort_values("hour_bucket").reset_index(drop=True)
        counts = g["count"].astype(float).tolist()
        times = list(g["hour_bucket"])
        for t in range(2, len(counts) - horizon):
            rows.append(
                {
                    "lag1": counts[t],
                    "lag2": counts[t - 1],
                    "lag3": counts[t - 2],
                    "roll3": float(np.mean(counts[t - 2 : t + 1])),
                    "hour": int(times[t].hour),
                    "dow": int(times[t].weekday()),
                    "corridor_freq": float(freq_map.get(corridor, 0.0)),
                    "target": float(sum(counts[t + 1 : t + 1 + horizon])),
                }
            )
    return pd.DataFrame(rows)

class ForecastModel:
    def __init__(self, reg, freq_map: dict, scale: float, horizon: int, version: str):
        self.reg = reg
        self.freq_map = freq_map
        self.scale = scale if scale and scale > 0 else 1.0
        self.horizon = horizon
        self.version = version

    @classmethod
    def model_path(cls, version: Optional[str] = None) -> Path:
        settings = get_settings()
        name = f"{MODEL_NAME}.joblib" if version is None else f"{MODEL_NAME}-{version}.joblib"
        return settings.model_dir / name

    @classmethod
    def train(cls, frame: pd.DataFrame, version: str) -> "ForecastModel":
        horizon = get_settings().forecast_horizon_hours
        panel = hourly_counts(frame)
        if panel.empty:
            raise ValueError("no time-stamped incidents to forecast")
        totals = panel.groupby("corridor")["count"].sum()
        freq_map = (totals / max(totals.sum(), 1)).to_dict()
        sup = _supervised(panel, horizon, freq_map)
        if sup.empty:
            raise ValueError("not enough history to build 3h targets")
        X, y = sup[_FEATURES], sup["target"]
        reg = LGBMRegressor(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            random_state=get_settings().random_seed, n_jobs=1, verbose=-1,
        )
        reg.fit(X, y)
        scale = float(np.percentile(np.clip(reg.predict(X), 0, None), 95))
        return cls(reg, freq_map, scale, horizon, version)

    def predict_corridor(self, corridor: str, recent_counts: list[float], hour: int, dow: int) -> dict:
        c = [float(x) for x in recent_counts]
        while len(c) < 3:
            c = [0.0] + c
        X = pd.DataFrame(
            [{
                "lag1": c[-1], "lag2": c[-2], "lag3": c[-3],
                "roll3": float(np.mean(c[-3:])),
                "hour": int(hour), "dow": int(dow),
                "corridor_freq": float(self.freq_map.get(corridor, 0.0)),
            }]
        )[_FEATURES]
        pred = max(0.0, float(self.reg.predict(X)[0]))
        risk = min(100.0, 100.0 * pred / self.scale)
        return {
            "corridor": corridor,
            "expected_incidents_next_3h": round(pred, 2),
            "risk": round(risk, 2),
            "horizon_hours": self.horizon,
        }

    def save(self) -> Path:
        blob = {"reg": self.reg, "freq_map": self.freq_map, "scale": self.scale,
                "horizon": self.horizon, "version": self.version}
        path = self.model_path(self.version)
        joblib.dump(blob, path)
        joblib.dump(blob, self.model_path(None))  # current pointer
        return path

    @classmethod
    def load(cls, version: Optional[str] = None) -> "ForecastModel":
        b = joblib.load(cls.model_path(version))
        return cls(b["reg"], b["freq_map"], b["scale"], b["horizon"], b["version"])
