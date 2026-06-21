"""Precomputed, torch-free response table for /nlp/severity.

WHY: on Render we must never load the severity_text model at request time
(memory). We run the trained model ONCE at build time over the trilingual
corpus, freeze {phrase -> {band, confidence}} to joblib, and serve
/nlp/severity as a pure lookup:
    normalize -> exact -> nearest cached phrase -> safe default

Build (model available, e.g. docker build stage or local venv):
    python -m clear.nlp_responses
"""
from __future__ import annotations

import difflib
from pathlib import Path


import joblib

from .config import get_settings
from .nlp_corpus import all_phrases, cause_for_phrase
from .preprocessing import _normalize_text, _strip_negated
from .schema import SEVERITY_BANDS

TABLE_NAME = "nlp_responses.joblib"

# Safe default when nothing matches: middle band, zero confidence, clearly flagged.
SAFE_DEFAULT = {"band": "medium", "confidence": 0.0, "source": "default"}

# Minimum fuzzy similarity (0-1) to accept a nearest-phrase match.
_NEAREST_CUTOFF = 0.6

_table: dict | None = None

def table_path() -> Path:
    return get_settings().model_dir / TABLE_NAME

def _norm(text: str) -> str:
    # Reuse the model's own normalization + negation stripping so the lookup key
    # matches how the model "saw" the text (e.g. "no fire" won't match a fire phrase).
    return _strip_negated(_normalize_text(text or "")).strip()

def build(model, *, out_path: Path | None = None) -> dict:
    """Run the trained text model over every corpus phrase once; freeze the responses."""
    out_path = out_path or table_path()
    table: dict[str, dict] = {}
    for phrase in all_phrases():
        record = {
            "event_id": "NLP-PRECOMP",
            "start_datetime": "2024-01-01T00:00:00+00:00",
            "event_cause": cause_for_phrase(phrase) or "others",
            "corridor": "unknown",
            "description": phrase,
            "comment": "",
            "status": "open",
        }
        out = model.predict_one(record)
        band = str(out.get("band", "medium"))
        if band not in SEVERITY_BANDS:
            band = "medium"
        conf = float(out.get("confidence", 0.0))
        table[_norm(phrase)] = {
            "band": band,
            "confidence": max(0.0, min(1.0, conf)),
            "source": "precomputed",
        }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(table, out_path)
    return table

def load() -> dict:
    global _table
    if _table is not None:
        return _table
    path = table_path()
    try:
        _table = dict(joblib.load(path)) if path.exists() else {}
    except Exception:
        _table = {}
    return _table

def lookup(text: str) -> dict:
    """Pure, torch-free severity lookup. Never loads the model."""
    table = load()
    key = _norm(text)
    if not table or not key:
        return dict(SAFE_DEFAULT)
    # 1) exact normalized match
    if key in table:
        return dict(table[key])
    # 2) nearest cached phrase (fuzzy, torch-free)
    matches = difflib.get_close_matches(key, list(table.keys()), n=1, cutoff=_NEAREST_CUTOFF)
    if matches:
        hit = dict(table[matches[0]])
        hit["source"] = "nearest"
        return hit
    # 3) safe default
    return dict(SAFE_DEFAULT)

def main() -> None:
    from .models.severity_text import SeverityTextModel
    table = build(SeverityTextModel.load())
    print({"phrases": len(table), "path": str(table_path())})

if __name__ == "__main__":
    main()
