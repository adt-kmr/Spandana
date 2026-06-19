"""Edge-case + band-ordering tests for the text-only severity model.

Trains a small model on synthetic data, then asserts that EVERY input - empty, punctuation,
huge, multilingual, unknown cause, raw free text - returns a valid band in SEVERITY_BANDS with
a confidence in [0, 1], and that severity ordering is broadly respected (minor <= severe).
"""
from __future__ import annotations

import pytest

from clear.datagen import generate
from clear.models.severity_text import SeverityTextModel
from clear.preprocessing import prepare_records
from clear.schema import SEVERITY_BANDS

_BAND_RANK = {b: i for i, b in enumerate(SEVERITY_BANDS)}  # low<medium<high<critical

@pytest.fixture(scope="module")
def model() -> SeverityTextModel:
    frame = prepare_records(generate(600, 7).to_dict("records"))
    return SeverityTextModel.train(frame, version="test")

def _rec(text: str, cause: str = "") -> dict:
    return {
        "event_id": "T", "start_datetime": "2024-01-01T00:00:00+00:00",
        "event_cause": cause, "corridor": "Mysore Road",
        "description": text, "comment": "", "status": "open",
    }

@pytest.mark.parametrize("text", [
    "", " ", "!!!", ".", "123", "x" * 5000, "\n\t  \n",
    "minor issue, no injuries, all clear",
    "severe crash, people trapped, fatal, fire",
    "गंभीर हादसा, मौत, आग, लोग फँसे",          # HI severe
    "ಗಂಭೀರ ಅಪಘಾತ, ಸಾವು, ಬೆಂಕಿ",              # KN severe
    "मामूली बात, सब ठीक",                       # HI minor
    "random unrelated words about nothing here",
])
def test_never_fails_any_input(model: SeverityTextModel, text: str) -> None:
    out = model.predict_one(_rec(text))
    assert out["band"] in SEVERITY_BANDS
    assert 0.0 <= out["confidence"] <= 1.0

def test_unknown_cause_is_safe(model: SeverityTextModel) -> None:
    out = model.predict_one(_rec("something happened", cause="alien_invasion"))
    assert out["band"] in SEVERITY_BANDS

def test_severe_not_below_minor(model: SeverityTextModel) -> None:
    minor = model.predict_one(_rec("minor, slight, no injuries, all clear, moving"))
    severe = model.predict_one(_rec("severe, fatal, people trapped, fire, critical"))
    assert _BAND_RANK[severe["band"]] >= _BAND_RANK[minor["band"]]
