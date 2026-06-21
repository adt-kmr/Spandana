"""Unit tests for the torch-free /nlp/severity response table (clear.nlp_responses).

Pure tests: they never load the real model, never hit the DB, and never read the
on-disk joblib. We inject a tiny in-memory table (or a stub model) and assert the
serving contract the /nlp/severity route relies on:

    normalize -> exact -> nearest cached phrase -> safe default

and that every result still passes the same validate_severity() the route runs.
"""
from __future__ import annotations

import pytest

from clear import nlp_responses
from clear.schema import SEVERITY_BANDS
from clear.validation import validate_severity


@pytest.fixture
def tiny_table(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Inject a 2-entry table, keyed exactly how lookup() normalizes its input."""
    raw = {
        "truck broke down blocking the road": {"band": "high", "confidence": 0.9},
        "water logging slowing traffic": {"band": "medium", "confidence": 0.5},
    }
    table = {
        nlp_responses._norm(phrase): {**payload, "source": "precomputed"}
        for phrase, payload in raw.items()
    }
    monkeypatch.setattr(nlp_responses, "_table", table)
    return table


def test_exact_match_returns_precomputed(tiny_table: dict) -> None:
    # Robust by construction: derive the probe from a real table key so it is
    # GUARANTEED to hit the exact branch. _normalize_text only lowercases +
    # NFC-normalizes (it does NOT strip punctuation), so we vary ONLY the case.
    # The precondition assert fails loudly here if normalization ever changes,
    # instead of silently sliding into the fuzzy 'nearest' branch.
    probe = "TRUCK BROKE DOWN BLOCKING THE ROAD"  # no punctuation; case differs
    assert nlp_responses._norm(probe) in tiny_table  # precondition: exact key
    out = nlp_responses.lookup(probe)
    assert out["band"] == "high"
    assert out["source"] == "precomputed"
    assert out["confidence"] == 0.9


def test_close_paraphrase_uses_nearest(tiny_table: dict) -> None:
    out = nlp_responses.lookup("truck broke down blocking the road today")
    assert out["source"] == "nearest"
    assert out["band"] == "high"


def test_unknown_text_falls_back_to_default(tiny_table: dict) -> None:
    out = nlp_responses.lookup("the weather is lovely and nothing is wrong at all")
    assert out == {"band": "medium", "confidence": 0.0, "source": "default"}


def test_blank_input_is_safe(tiny_table: dict) -> None:
    assert nlp_responses.lookup("   \n\t ")["source"] == "default"


def test_result_is_a_copy_not_a_table_alias(tiny_table: dict) -> None:
    first = nlp_responses.lookup("truck broke down blocking the road")
    first["band"] = "critical"  # caller mutation must NOT poison the cached table
    second = nlp_responses.lookup("truck broke down blocking the road")
    assert second["band"] == "high"


def test_every_path_passes_output_validator(tiny_table: dict) -> None:
    for text in ("truck broke down blocking the road", "totally unrelated text", "  "):
        validate_severity(nlp_responses.lookup(text))  # must not raise


class _StubModel:
    """Returns an out-of-range confidence and an invalid band on purpose."""

    def predict_one(self, record: dict) -> dict:
        return {"band": "not-a-band", "confidence": 1.7}


def test_build_clamps_confidence_and_sanitizes_band(tmp_path) -> None:
    out_path = tmp_path / "nlp_responses.joblib"
    table = nlp_responses.build(_StubModel(), out_path=out_path)
    assert out_path.exists()
    assert table, "corpus should yield at least one phrase"
    for entry in table.values():
        assert entry["band"] in SEVERITY_BANDS      # invalid band -> medium
        assert 0.0 <= entry["confidence"] <= 1.0     # 1.7 -> clamped to 1.0
        assert entry["source"] == "precomputed"