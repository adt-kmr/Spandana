"""Phase 5 (optional channel): standalone Telegram bot for CLEAR.

Runs as its OWN process and is a pure *client* of the existing CLEAR HTTP API
(citizen scope). It imports no models, opens no DB, and adds/changes no route in
app.py. If this process never starts, crashes, or is killed, the web API and the
frontend are completely unaffected.

Dependency-free (urllib only). Disabled by default: it needs CLEAR_TELEGRAM_ENABLED=1
AND CLEAR_TELEGRAM_BOT_TOKEN, otherwise it logs once and exits 0.

Hardening rules baked in below:
- Never crash the loop: every poll + every handler is wrapped; on error we log + backoff.
- Never leak internals: chat only ever sees whitelisted, HTML-escaped fields. Bot token,
  API URLs, bearer tokens, stack traces and raw upstream payloads are never sent to chat,
  and the bot token is redacted in logs.
- Never trust input: text is control-char stripped + length capped + URL-encoded, and the
  corridor is validated against the known set before any upstream call.
- Respect limits: per-chat token bucket + Telegram 429 Retry-After + exponential backoff.
- Idempotent: updates consumed via offset, de-duped by update_id, backlog drained on start.
- Graceful shutdown on SIGTERM/SIGINT (Render sends SIGTERM on redeploy).
"""
from __future__ import annotations

import html
import json
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .config import get_settings
from .logging_setup import configure_logging

log = configure_logging()

_RUNNING = True
_TELEGRAM_MAX_MSG = 4096
_TEXT_MAX_LEN = 256
_CORRIDOR_MAX_LEN = 64
_DEDUPE_MAX = 5000
_BUCKETS: dict[int, list[float]] = {}

# ----------------------------- small safe helpers -----------------------------
def _mask(token: str) -> str:
    if not token:
        return "<empty>"
    return f"{token[:4]}…{token[-3:]}" if len(token) > 8 else "<set>"

def _redact(url: str) -> str:
    return re.sub(r"/bot[0-9]+:[A-Za-z0-9_-]+", "/bot<redacted>", url)

def _clean(s: str, limit: int) -> str:
    s = re.sub(r"[\x00-\x1f\x7f]", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]

def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)

# ------------------------------- HTTP (urllib) --------------------------------
def _http_json(method: str, url: str, *, headers: Optional[dict] = None,
               body: Optional[dict] = None, timeout: float = 10.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"content-type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        out: dict = {}
        ra = e.headers.get("Retry-After") if e.headers else None
        if ra:
            try:
                out["_retry_after"] = float(ra)
            except ValueError:
                pass
        log.warning("http %s %s -> %s", method, _redact(url), e.code)
        return e.code, (out or None)
    except Exception as e:  # timeout / network / DNS
        log.warning("http %s %s failed: %s", method, _redact(url), e)
        return 0, None

# ------------------------------- Telegram API ---------------------------------
def _send(chat_id: int, text: str, settings) -> None:
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/sendMessage"
    status, data = _http_json("POST", url, body={
        "chat_id": chat_id,
        "text": text[:_TELEGRAM_MAX_MSG],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=settings.telegram_http_timeout_seconds)
    if status == 429 and isinstance(data, dict) and data.get("_retry_after"):
        time.sleep(min(float(data["_retry_after"]), 30))

def _get_updates(settings, offset: int, timeout: int):
    url = f"{settings.telegram_api_base}/bot{settings.telegram_bot_token}/getUpdates"
    return _http_json("POST", url, body={
        "timeout": timeout, "offset": offset, "allowed_updates": ["message"],
    }, timeout=timeout + settings.telegram_http_timeout_seconds)

# ------------------------------ policy helpers --------------------------------
def _allowed(chat_id: int, settings) -> bool:
    raw = (settings.telegram_allowed_chat_ids or "").strip()
    if not raw:
        return True
    return str(chat_id) in {x.strip() for x in raw.split(",") if x.strip()}

def _rate_ok(chat_id: int, per_min: int) -> bool:
    now = time.time()
    win = _BUCKETS.setdefault(chat_id, [])
    win[:] = [t for t in win if t > now - 60]
    if len(win) >= max(1, per_min):
        return False
    win.append(now)
    return True

def _known_corridors(settings) -> dict[str, str]:
    fix = {"orr": "ORR", "mg": "MG"}
    out: dict[str, str] = {}
    for low in settings.corridor_latlon.keys():
        out[low] = " ".join(fix.get(w, w.capitalize()) for w in low.split())
    return out

def _match_corridor(text: str, settings) -> Optional[str]:
    known = _known_corridors(settings)
    q = _clean(text, _CORRIDOR_MAX_LEN).lower()
    if not q:
        return None
    if q in known:
        return known[q]
    hits = [disp for low, disp in known.items() if low.startswith(q) or q in low]
    return hits[0] if len(hits) == 1 else None

# ------------------------------- CLEAR API call -------------------------------
def _fetch_rain(corridor: str, settings) -> Optional[dict]:
    base = settings.telegram_clear_api_base.rstrip("/")
    qs = urllib.parse.urlencode({"corridor": corridor})
    # Reuse the API's own citizen token when a dedicated one isn't set, so a same-env
    # deployment needs zero extra secrets and the two can never drift out of sync.
    token = settings.telegram_api_token or settings.citizen_token
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    status, data = _http_json("GET", f"{base}/weather/rain-risk?{qs}",
                              headers=headers, timeout=settings.telegram_http_timeout_seconds)
    return data if status == 200 and isinstance(data, dict) else None

# --------------------------------- formatting ---------------------------------
def _deep_link(corridor: str, settings) -> str:
    base = (settings.telegram_frontend_base or "").rstrip("/")
    return f"{base}/citizen?corridor={urllib.parse.quote(corridor)}" if base else ""

def _format_rain(data: dict, settings) -> str:
    name = _esc(_clean(str(data.get("corridor", "")), _CORRIDOR_MAX_LEN)) or "Corridor"
    if not data.get("available"):
        return f"🌧️ <b>{name}</b>\nNo live rain data right now — try again shortly."
    band = str(data.get("risk_band", "unknown"))
    emoji = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(band, "⚪")
    lines = [
        f"🌧️ <b>{name}</b>",
        f"{emoji} Rain-clog risk: <b>{_esc(str(data.get('rain_clog_score', '?')))}/100</b> ({_esc(band)})",
        f"⏱️ ETA impact: ×{_esc(str(data.get('rain_multiplier', '?')))}",
    ]
    rain = data.get("rain")
    if isinstance(rain, dict):
        lines.append(f"💧 {_esc(str(rain.get('intensity', '?')))} mm/min · "
                     f"{_esc(str(rain.get('accumulation', '?')))} mm today")
    if data.get("stale"):
        lines.append("<i>(cached reading)</i>")
    link = _deep_link(str(data.get("corridor", "")), settings)
    if link:
        lines.append(f"\n🔗 {_esc(link)}")
    return "\n".join(lines)

def _help_text(settings) -> str:
    return (
        "👋 <b>CLEAR rain-clog bot</b>\n"
        "Live water-logging risk for a Bengaluru corridor.\n\n"
        "• <code>/rain Sarjapur Road</code> — risk for a corridor\n"
        "• or just type a corridor name\n"
        "• <code>/corridors</code> — list corridors\n"
        "• <code>/report</code> — link to report an incident\n"
        "• <code>/help</code> — this message"
    )

# --------------------------------- dispatch -----------------------------------
def _handle(update: dict, settings) -> None:
    msg = update.get("message")
    if not isinstance(msg, dict):
        return  # ignore edited_message / channel_post / callbacks / etc.
    chat_id = (msg.get("chat") or {}).get("id")
    if not isinstance(chat_id, int):
        return
    if not _allowed(chat_id, settings):
        return  # silent drop for disallowed chats
    if not _rate_ok(chat_id, settings.telegram_rate_limit_per_min):
        _send(chat_id, "⏳ Too many requests — please wait a minute.", settings)
        return
    text = _clean(str(msg.get("text", "")), _TEXT_MAX_LEN)
    if not text:
        return
    head, _, rest = text.partition(" ")
    cmd = head.lower().lstrip("/").split("@", 1)[0]
    arg = _clean(rest, _CORRIDOR_MAX_LEN)

    if cmd in ("start", "help"):
        _send(chat_id, _help_text(settings), settings)
        return
    if cmd == "corridors":
        names = ", ".join(sorted(_known_corridors(settings).values()))
        _send(chat_id, f"Known corridors:\n{_esc(names)}", settings)
        return
    if cmd == "report":
        link = _deep_link(arg, settings)
        _send(chat_id, f"📝 Report an incident:\n🔗 {_esc(link)}" if link
              else "Reporting link isn't configured.", settings)
        return

    query = arg if cmd == "rain" else text
    corridor = _match_corridor(query, settings)
    if not corridor:
        _send(chat_id, "Couldn't find that corridor. Send /corridors for the list.", settings)
        return
    data = _fetch_rain(corridor, settings)
    if data is None:
        _send(chat_id, "⚠️ Service is busy right now — please try again in a moment.", settings)
        return
    _send(chat_id, _format_rain(data, settings), settings)

# ----------------------------------- main -------------------------------------
def _install_signals() -> None:
    def _stop(*_):
        global _RUNNING
        _RUNNING = False
    try:
        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
    except ValueError:
        pass  # not on main thread; fine

def main() -> int:
    settings = get_settings()
    if not settings.telegram_enabled or not settings.telegram_bot_token:
        log.info("telegram bot disabled (enabled=%s, token=%s) — exiting cleanly",
                 settings.telegram_enabled, _mask(settings.telegram_bot_token))
        return 0
    _install_signals()
    log.info("telegram bot up (token=%s, api=%s)", _mask(settings.telegram_bot_token),
             settings.telegram_clear_api_base)
    # Startup sanity warnings (never crash — just surface misconfig in the logs).
    if not (settings.telegram_api_token or settings.citizen_token):
        log.warning("telegram: no API token (CLEAR_TELEGRAM_API_TOKEN / CLEAR_CITIZEN_TOKEN) — upstream calls will be unauthenticated")
    if not settings.corridor_latlon:
        log.warning("telegram: no corridor map (apply the rain-clog config) — corridor lookups will fail")

    # Drain any backlog so a restart never replays stale messages.
    offset = 0
    status, data = _get_updates(settings, -1, 0)
    if status == 200 and isinstance(data, dict) and data.get("ok"):
        for upd in data.get("result", []):
            if isinstance(upd.get("update_id"), int):
                offset = max(offset, upd["update_id"] + 1)

    seen: dict[int, float] = {}
    backoff = 1.0
    while _RUNNING:
        try:
            status, data = _get_updates(settings, offset, settings.telegram_poll_timeout_seconds)
            if status == 429 and isinstance(data, dict) and data.get("_retry_after"):
                time.sleep(min(float(data["_retry_after"]), 30))
                continue
            if status != 200 or not isinstance(data, dict) or not data.get("ok"):
                time.sleep(min(backoff, 30))
                backoff = min(backoff * 2, 30)
                continue
            backoff = 1.0
            for upd in data.get("result", []):
                uid = upd.get("update_id")
                if not isinstance(uid, int):
                    continue
                offset = max(offset, uid + 1)
                if uid in seen:
                    continue
                seen[uid] = time.time()
                try:
                    _handle(upd, settings)
                except Exception as e:
                    log.warning("handle failed for update %s: %s", uid, e)
            if len(seen) > _DEDUPE_MAX:
                cut = time.time() - 3600
                for k in [k for k, t in seen.items() if t < cut]:
                    seen.pop(k, None)
        except Exception as e:
            log.warning("poll loop error: %s", e)
            time.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)
    log.info("telegram bot stopped cleanly")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
