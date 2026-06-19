"""Dedicated text-only severity model served by /nlp/severity.

Why this exists
---------------
The citizen endpoint /nlp/severity only ever supplies free TEXT (+ optional cause / coords).
The structured SeverityModel is dominated by features that endpoint never sends
(lat, lon, rainfall_mm, hour_*, dow_*, corridor_freq, lanes_blocked, closure). At serve time
those collapse to constant training fills -> train/serve skew -> flat bands and the capped
0.44 confidence. This model trains on ONLY text-derivable signal, so train == serve:

  * multilingual TIERED lexical cue counts  (torch-free, fire in EN / HI / KN)
  * event-cause one-hot + has_vehicle
  * PCA-reduced MuRIL embedding             (semantic generalization, cache-backed at serve)

Robustness
----------
During training the MuRIL embedding is randomly zeroed for a fraction of rows
(`severity_text_embed_dropout`) so the model stays confident from LEXICAL features alone -
exactly the production free-text case where an uncached phrase yields a zero embedding
(no torch on Render). Calibrated with isotonic regression so reported confidence is a real,
sharp probability.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.decomposition import PCA
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .. import nlp_muril
from ..config import get_settings
from ..preprocessing import prepare_records
from ..schema import EVENT_CAUSES, SEVERITY_BANDS

MODEL_NAME = "severity_text"
_MURIL_PREFIX = "muril_"
_CAUSE_FEATURES = [f"cause_{c}" for c in EVENT_CAUSES]
_LEXICAL_FEATURES = [
    "cue_severe", "cue_serious", "cue_moderate", "cue_minor", "cue_closure",
    "cue_count", "has_vehicle",
]
_BASE_FEATURES = _LEXICAL_FEATURES + _CAUSE_FEATURES

def _lexical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=frame.index)
    for col in _LEXICAL_FEATURES:
        feats[col] = (
            pd.to_numeric(frame[col], errors="coerce").fillna(0.0)
            if col in frame.columns else 0.0
        )
    for c in EVENT_CAUSES:
        feats[f"cause_{c}"] = (
            (frame["event_cause"] == c).astype(int) if "event_cause" in frame.columns else 0
        )
    return feats[_BASE_FEATURES]

def _build_estimator(seed: int):
    settings = get_settings()
    logreg = Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(
            C=settings.severity_text_lr_c, max_iter=5000,
            class_weight="balanced", random_state=seed,
        )),
    ])
    mlp = Pipeline([
        ("scale", StandardScaler()),
        ("clf", MLPClassifier(
            hidden_layer_sizes=(256, 128), alpha=settings.severity_text_mlp_alpha,
            max_iter=settings.severity_text_max_iter, early_stopping=True,
            n_iter_no_change=25, random_state=seed,
        )),
    ])
    # Soft-vote a well-calibrated linear model with a non-linear MLP: LogReg anchors
    # calibration + handles imbalance, the MLP captures non-linear embedding structure.
    return VotingClassifier(estimators=[("logreg", logreg), ("mlp", mlp)], voting="soft")

class SeverityTextModel:
    def __init__(self, clf, columns, emb_cols, muril_pca, version):
        self.clf = clf
        self.columns = columns
        self.emb_cols = emb_cols
        self.muril_pca = muril_pca
        self.version = version

    @classmethod
    def model_path(cls, version: Optional[str] = None) -> Path:
        settings = get_settings()
        name = f"{MODEL_NAME}.joblib" if version is None else f"{MODEL_NAME}-{version}.joblib"
        return settings.model_dir / name

    @classmethod
    def train(cls, frame: pd.DataFrame, version: str) -> "SeverityTextModel":
        settings = get_settings()
        seed = settings.random_seed
        labeled = frame[frame["severity_reported"].isin(SEVERITY_BANDS)].copy()
        if labeled.empty:
            raise ValueError("no labeled severity rows to train on")
        y = labeled["severity_reported"].astype(str)
        counts = y.value_counts()
        # isotonic calibration across cv folds needs a few members per class per fold.
        usable = counts[counts >= 5].index
        labeled = labeled[y.isin(usable)]
        y = y[y.isin(usable)]
        if y.nunique() < 2:
            raise ValueError(f"severity_text needs >=2 populated bands, got {dict(counts)}")

        X = _lexical_frame(labeled)
        emb_cols: List[str] = []
        muril_pca = None
        if settings.use_muril:
            emb = nlp_muril.embed_texts(nlp_muril.compose_text(labeled))
            if emb.any():
                ncomp = int(min(settings.muril_text_pca_dims, emb.shape[0], emb.shape[1]))
                muril_pca = PCA(n_components=ncomp, random_state=seed).fit(emb)
                reduced = muril_pca.transform(emb).astype(np.float64)
                # Embedding dropout: zero a fraction of rows so the model learns to be
                # confident from lexical cues ALONE (the prod zero-embedding free-text case).
                rng = np.random.default_rng(seed)
                drop = rng.random(reduced.shape[0]) < settings.severity_text_embed_dropout
                reduced[drop] = 0.0
                emb_cols = [f"{_MURIL_PREFIX}{i}" for i in range(reduced.shape[1])]
                X = pd.concat(
                    [X, pd.DataFrame(reduced, index=X.index, columns=emb_cols)], axis=1
                )

        columns = list(X.columns)
        min_class = int(counts[usable].min())
        cv = max(2, min(5, min_class))
        base = _build_estimator(seed)
        try:
            clf = CalibratedClassifierCV(base, method="isotonic", cv=cv)
            clf.fit(X, y)
        except Exception:  # noqa: BLE001 - never fail training; fall back to a robust linear model
            fallback = Pipeline([
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(
                    C=settings.severity_text_lr_c, max_iter=5000,
                    class_weight="balanced", random_state=seed,
                )),
            ])
            clf = CalibratedClassifierCV(fallback, method="isotonic", cv=cv)
            clf.fit(X, y)
        return cls(clf, columns, emb_cols, muril_pca, version)

    def _aligned(self, frame: pd.DataFrame) -> pd.DataFrame:
        X = _lexical_frame(frame)
        if self.muril_pca is not None and get_settings().use_muril:
            emb = nlp_muril.embed_texts(nlp_muril.compose_text(frame))
            reduced = self.muril_pca.transform(emb).astype(np.float64)
            cols = [f"{_MURIL_PREFIX}{i}" for i in range(reduced.shape[1])]
            X = pd.concat([X, pd.DataFrame(reduced, index=X.index, columns=cols)], axis=1)
        for col in self.columns:
            if col not in X.columns:
                X[col] = 0.0
        return X[self.columns]

    def predict_one(self, record: dict) -> dict:
        frame = prepare_records([record], as_of=None)
        if frame.empty:
            return {"band": "medium", "confidence": 0.0}
        X = self._aligned(frame)
        proba = self.clf.predict_proba(X)[0]
        classes = list(self.clf.classes_)
        idx = int(np.argmax(proba))
        return {"band": str(classes[idx]), "confidence": float(proba[idx])}

    def save(self) -> Path:
        blob = {
            "clf": self.clf, "columns": self.columns, "emb_cols": self.emb_cols,
            "muril_pca": self.muril_pca, "version": self.version,
        }
        path = self.model_path(self.version)
        joblib.dump(blob, path)
        joblib.dump(blob, self.model_path(None))  # current pointer
        return path

    @classmethod
    def load(cls, version: Optional[str] = None) -> "SeverityTextModel":
        b = joblib.load(cls.model_path(version))
        return cls(b["clf"], b["columns"], b.get("emb_cols", []), b.get("muril_pca"), b["version"])
