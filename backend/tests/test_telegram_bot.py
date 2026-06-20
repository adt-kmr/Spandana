"""Phase 5 Telegram bot: pure-helper tests. No network, no token, no bot run."""
from __future__ import annotations

from clear.config import get_settings
from clear import telegram_bot as tb

def test_clean_strips_controls_and_caps():
    assert tb._clean("a\x00b\tc   d", 100) == "a b c d"
    assert len(tb._clean("x" * 500, 64)) == 64

def test_redact_hides_bot_token():
    url = "https://api.telegram.org/bot123456:AAbbCC-_dd/getUpdates"
    out = tb._redact(url)
    assert "123456:AAbbCC" not in out and "<redacted>" in out

def test_mask_never_reveals_token():
    assert tb._mask("123456:AAbbCCddEE") not in ("123456:AAbbCCddEE",)
    assert tb._mask("") == "<empty>"

def test_match_corridor_known_and_unknown():
    s = get_settings()
    assert tb._match_corridor("sarjapur road", s) is not None
    assert tb._match_corridor("totally unknown road", s) is None

def test_format_unavailable_is_safe():
    s = get_settings()
    out = tb._format_rain({"corridor": "Sarjapur Road", "available": False}, s)
    assert "No live rain data" in out

def test_format_escapes_user_corridor():
    s = get_settings()
    out = tb._format_rain({"corridor": "<b>x</b>", "available": False}, s)
    assert "<b>x</b>" not in out  # echoed corridor is HTML-escaped

def test_rate_limit_blocks_after_quota():
    assert tb._rate_ok(99999, 2) is True
    assert tb._rate_ok(99999, 2) is True
    assert tb._rate_ok(99999, 2) is False
