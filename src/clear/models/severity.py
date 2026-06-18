"""Severity service: calibrated classifier -> band + confidence, not a raw 0-100 (constraint 5)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV

from ..config import get_settings
from ..preprocessing import prepare_records
from ..schema import EVENT_CAUSES, SEVERITY_BANDS

MODEL_NAME = "severity"

# NOTE: priority_ord is intentionally EXCLUDED from the feature set. On the real dataset the
# severity label falls back to `priority` (there is no independent severity_reported column),
# so feeding priority_ord would leak the label and the model would just echo priority. Severity
# is instead learned from INDEPENDENT incident characteristics: where it happened (lat/lon +
# corridor frequency), when (cyclical hour / day-of-week), what (event cause), whether a road
# closure or vehicle is involved, and how urgent the free text reads (cue_count). (de-leak)
_CAUSE_FEATURES = [f"cause_{c}" for c in EVENT_CAUSES]
_CANDIDATE_FEATURES = [
    "closure", "has_vehicle", "cue_count", "rainfall_mm", "lanes_blocked",
    "lat", "lon", "hour_sin", "hour_cos", "dow_sin", "dow_cos", "corridor_freq",
] + _CAUSE_FEATURES


def _featurize(frame: pd.DataFrame, freq_map: dict, lat_fill: float, lon_fill: float) -> pd.DataFrame:
    feats = pd.DataFrame(index=frame.index)
    feats["closure"] = frame["requires_road_closure"].astype(int)
    feats["has_vehicle"] = frame["has_vehicle"].astype(int)
    feats["cue_count"] = pd.to_numeric(frame["cue_count"], errors="coerce").fillna(0.0)
    feats["rainfall_mm"] = pd.to_numeric(frame["rainfall_mm"], errors="coerce").fillna(0.0)
    feats["lanes_blocked"] = pd.to_numeric(frame["lanes_blocked"], errors="coerce").fillna(0.0)
    feats["lat"] = pd.to_numeric(frame["latitude"], errors="coerce").fillna(lat_fill)
    feats["lon"] = pd.to_numeric(frame["longitude"], errors="coerce").fillna(lon_fill)
    hour = pd.to_numeric(frame["hour_ist"], errors="coerce").fillna(12.0)
    feats["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    feats["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    dow = pd.to_numeric(frame["dow_ist"], errors="coerce").fillna(0.0)
    feats["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    feats["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
    feats["corridor_freq"] = frame["corridor"].map(freq_map).fillna(0.0).astype(float)
    for c in EVENT_CAUSES:
        feats[f"cause_{c}"] = (frame["event_cause"] == c).astype(int)
    return feats[_CANDIDATE_FEATURES]


class SeverityModel:
    def __init__(self, clf, columns, freq_map, lat_fill, lon_fill, version):
        self.clf = clf
        self.columns = columns
        self.freq_map = freq_map
        self.lat_fill = lat_fill
        self.lon_fill = lon_fill
        self.version = version

    @classmethod
    def model_path(cls, version: Optional[str] = None) -> Path:
        settings = get_settings()
        name = f"{MODEL_NAME}.joblib" if version is None else f"{MODEL_NAME}-{version}.joblib"
        return settings.model_dir / name

    @classmethod
    def train(cls, frame: pd.DataFrame, version: str) -> "SeverityModel":
        labeled = frame[frame["severity_reported"].isin(SEVERITY_BANDS)].copy()
        if labeled.empty:
            raise ValueError("no labeled severity rows to train on")
        y = labeled["severity_reported"].astype(str)
        counts = y.value_counts()
        # Keep only bands with enough members to fit AND calibrate across folds.
        usable = counts[counts >= 2].index
        labeled = labeled[y.isin(usable)]
        y = y[y.isin(usable)]
        if y.nunique() < 2:
            raise ValueError(f"severity needs >=2 populated bands, got {dict(counts)}")

        freq_map = labeled["corridor"].value_counts(normalize=True).to_dict()
        lat_med = pd.to_numeric(labeled["latitude"], errors="coerce").median()
        lon_med = pd.to_numeric(labeled["longitude"], errors="coerce").median()
        lat_fill = float(lat_med) if pd.notna(lat_med) else 0.0
        lon_fill = float(lon_med) if pd.notna(lon_med) else 0.0

        X = _featurize(labeled, freq_map, lat_fill, lon_fill)
        # Drop zero-variance columns (rainfall_mm / lanes_blocked are all-zero in the real
        # export) so the model never wastes splits on dead signal; remember what we kept so the
        # serving path lines up exactly.
        keep = [c for c in X.columns if X[c].nunique() > 1]
        if not keep:
            raise ValueError("no non-constant severity features available")
        X = X[keep]

        seed = get_settings().random_seed
        base = LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            colsample_bytree=0.9, class_weight="balanced",  # counter band imbalance
            random_state=seed, n_jobs=-1, verbose=-1,
        )
        # Calibrated probabilities so reported confidence is meaningful (constraint 5). Fold
        # count is bounded by the rarest class; isotonic only when there is plenty of data.
        min_class = int(counts[usable].min())
        cv = max(2, min(3, min_class))
        method = "isotonic" if min_class >= 1000 else "sigmoid"
        clf = CalibratedClassifierCV(base, method=method, cv=cv)
        clf.fit(X, y)
        return cls(clf, keep, freq_map, lat_fill, lon_fill, version)

    def _aligned(self, frame: pd.DataFrame) -> pd.DataFrame:
        X = _featurize(frame, self.freq_map, self.lat_fill, self.lon_fill)
        for col in self.columns:
            if col not in X:
                X[col] = 0
        return X[self.columns]

    def predict_one(self, record: dict) -> dict:
        frame = prepare_records([record], as_of=None)
        X = self._aligned(frame)
        proba = self.clf.predict_proba(X)[0]
        classes = list(self.clf.classes_)
        idx = int(np.argmax(proba))
        return {"band": str(classes[idx]), "confidence": float(proba[idx])}

    def save(self) -> Path:
        blob = {
            "clf": self.clf, "columns": self.columns, "freq_map": self.freq_map,
            "lat_fill": self.lat_fill, "lon_fill": self.lon_fill, "version": self.version,
        }
        path = self.model_path(self.version)
        joblib.dump(blob, path)
        joblib.dump(blob, self.model_path(None))  # current pointer
        return path

    @classmethod
    def load(cls, version: Optional[str] = None) -> "SeverityModel":
        b = joblib.load(cls.model_path(version))
        return cls(b["clf"], b["columns"], b["freq_map"], b["lat_fill"], b["lon_fill"],
                   b["version"])