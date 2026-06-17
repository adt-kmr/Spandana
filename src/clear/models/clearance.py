"""Clearance service: censored survival analysis -> median + P10-P90 (constraints 2,3)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from lifelines import WeibullAFTFitter

from ..config import get_settings
from ..preprocessing import prepare_records
from ..schema import EVENT_CAUSES

MODEL_NAME = "clearance"

def _design(frame: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=frame.index)
    feats["priority_ord"] = frame["priority_ord"].astype(float)
    feats["closure"] = frame["requires_road_closure"].astype(int)
    feats["rainfall_mm"] = frame["rainfall_mm"].astype(float)
    hour = frame["hour_ist"].fillna(12).astype(float)  # IST-derived (constraint 4)
    feats["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    feats["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    for c in EVENT_CAUSES:
        feats[f"cause_{c}"] = (frame["event_cause"] == c).astype(int)
    # Drop zero-variance one-hots so the AFT design matrix stays full-rank.
    return feats.loc[:, feats.nunique() > 1] if len(feats) > 1 else feats

class ClearanceModel:
    def __init__(self, aft: WeibullAFTFitter, columns: list[str], version: str):
        self.aft = aft
        self.columns = columns
        self.version = version

    @classmethod
    def model_path(cls, version: Optional[str] = None) -> Path:
        settings = get_settings()
        name = f"{MODEL_NAME}.joblib" if version is None else f"{MODEL_NAME}-{version}.joblib"
        return settings.model_dir / name

    @classmethod
    def train(cls, frame: pd.DataFrame, version: str) -> "ClearanceModel":
        cap = get_settings().max_clearance_minutes
        df = frame.copy()
        # Right-censored design: censored rows are censored AT cap, never imputed to 0/now.
        T = df["duration_minutes"].astype(float)
        E = df["event_observed"].astype(int)
        T = T.where(E == 1, other=cap)
        T = T.fillna(cap).clip(lower=1.0, upper=cap)
        design = _design(df)
        design = design.assign(T=T.values, E=E.values)
        aft = WeibullAFTFitter(penalizer=0.1)
        aft.fit(design, duration_col="T", event_col="E")
        cols = [c for c in design.columns if c not in ("T", "E")]
        return cls(aft, cols, version)

    def _aligned(self, frame: pd.DataFrame) -> pd.DataFrame:
        design = _design(frame)
        for col in self.columns:
            if col not in design:
                design[col] = 0
        return design[self.columns]

    def predict_one(self, record: dict) -> dict:
        frame = prepare_records([record], as_of=None)
        design = self._aligned(frame)
        cap = get_settings().max_clearance_minutes

        def _clamp(x: float) -> float:
            return cap if not np.isfinite(x) else float(min(max(x, 1.0), cap))

        # predict_percentile(p) returns the p-th percentile event time.
        median = _clamp(float(self.aft.predict_percentile(design, p=0.5).iloc[0]))
        p10 = _clamp(float(self.aft.predict_percentile(design, p=0.1).iloc[0]))
        p90 = _clamp(float(self.aft.predict_percentile(design, p=0.9).iloc[0]))
        lo, hi = min(p10, p90), max(p10, p90)
        median = min(max(median, lo), hi)
        return {
            "median_minutes": median,
            "p10_minutes": lo,
            "p90_minutes": hi,
            "interval_note": "P10-P90 survival interval; not a guaranteed point ETA.",
        }

    def save(self) -> Path:
        blob = {"aft": self.aft, "columns": self.columns, "version": self.version}
        path = self.model_path(self.version)
        joblib.dump(blob, path)
        joblib.dump(blob, self.model_path(None))  # current pointer
        return path

    @classmethod
    def load(cls, version: Optional[str] = None) -> "ClearanceModel":
        blob = joblib.load(cls.model_path(version))
        return cls(blob["aft"], blob["columns"], blob["version"])
