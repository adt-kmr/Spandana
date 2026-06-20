"""Phase 5 unit tests: pure scoring + safe-by-default orchestration. No network, no API key."""
from __future__ import annotations

import clear.config as cfg
from clear.rain_clog import corridor_rain_risk, rain_clog_score

def test_score_zero_when_no_rain():
    assert rain_clog_score(0.0, 0.0, 0.7) == 0.0

def test_score_increases_with_intensity():
    low = rain_clog_score(0.1, 0.0, 0.5)
    high = rain_clog_score(0.5, 0.0, 0.5)
    assert 0.0 <= low < high <= 100.0

def test_floodprone_corridor_scores_higher():
    mild = rain_clog_score(0.3, 10.0, 0.2)
    prone = rain_clog_score(0.3, 10.0, 0.9)
    assert prone > mild

def test_score_capped_at_100():
    assert rain_clog_score(99.0, 9999.0, 1.0) == 100.0

def test_corridor_risk_disabled_is_safe(monkeypatch):
    # Force the flag OFF regardless of .env, then re-read settings.
    monkeypatch.setenv("CLEAR_RAIN_CLOG_ENABLED", "0")
    cfg.get_settings.cache_clear()
    try:
        out = corridor_rain_risk("Sarjapur Road")
    finally:
        cfg.get_settings.cache_clear()
    assert out["available"] is False
    assert out["rain_multiplier"] == 1.0
    assert out["reason"] == "rain-clog disabled"
