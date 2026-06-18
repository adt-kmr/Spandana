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
# so using priority_ord as a feature would leak the label and the model would just echo
# priority. Severity is instead learned from incident characteristics. (de-leak)
_FEATURES = [
    "closure", "rainfall_mm", "has_vehicle", "lanes_blocked", "cue_count",
] + [f"cause_{c}" for c in EVENT_CAUSES]

def _featurize(frame: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=frame.index)
    feats["closure"] = frame["requires_road_closure"].astype(int)
    feats["rainfall_mm"] = frame["rainfall_mm"].astype(float)
    feats["has_vehicle"] = frame["has_vehicle"].astype(int)
    feats["lanes_blocked"] = frame["lanes_blocked"].astype(float)
    feats["cue_count"] = frame["cue_count"].astype(float)
    for c in EVENT_CAUSES:
        feats[f"cause_{c}"] = (frame["event_cause"] == c).astype(int)
    return feats[_FEATURES]

class SeverityModel:
    def __init__(self, clf: CalibratedClassifierCV, version: str):
        self.clf = clf
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
        X = _featurize(labeled)
        y = labeled["severity_reported"].astype(str)
        seed = get_settings().random_seed
        base = LGBMClassifier(
            n_estimators=200, learning_rate=0.05, num_leaves=31,
            random_state=seed, n_jobs=1, verbose=-1,
        )
        # Calibrated probabilities so the reported confidence is meaningful (constraint 5).
        clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)
        clf.fit(X, y)
        return cls(clf, version)

    def predict_one(self, record: dict) -> dict:
        frame = prepare_records([record], as_of=None)
        X = _featurize(frame)
        proba = self.clf.predict_proba(X)[0]
        classes = list(self.clf.classes_)
        idx = int(np.argmax(proba))
        return {"band": str(classes[idx]), "confidence": float(proba[idx])}

    def save(self) -> Path:
        blob = {"clf": self.clf, "version": self.version}
        path = self.model_path(self.version)
        joblib.dump(blob, path)
        joblib.dump(blob, self.model_path(None))  # current pointer
        return path

    @classmethod
    def load(cls, version: Optional[str] = None) -> "SeverityModel":
        blob = joblib.load(cls.model_path(version))
        return cls(blob["clf"], blob["version"])
