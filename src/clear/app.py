"""FastAPI app: ingest -> infer -> output-validate -> serve, with role-scoped access.
Models are loaded once at startup into app.state; a missing model degrades gracefully
(constraint 13) instead of crashing the API."""
from __future__ import annotations

import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import db
from .auth import require_scope
from .config import get_settings
from .degradation import fifo_queue, stale_corridor_risk
from .ingestion import ingest_one
from .logging_setup import configure_logging
from .metrics import clearance_prediction_error
from .models.dispatch import suggest as dispatch_suggest
from .models.hotspot import run_batch as hotspot_batch
from .ratelimit import RateLimitMiddleware
from .validation import (
    OutputValidationError,
    validate_clearance,
    validate_forecast,
    validate_severity,
)

log = configure_logging()

_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+previous|disregard\s+(all|previous)|system\s*prompt|/system|"
    r"act\s+as|you\s+are\s+now|<\s*script|prompt\s*injection)",
    re.IGNORECASE,
)

def sanitize_text(text: Optional[str], max_len: int = 1000) -> str:
    """Prompt-injection guard for free text before any downstream LLM use (constraint 16)."""
    if not text:
        return ""
    cleaned = text.replace("\x00", " ").strip()[:max_len]
    return _INJECTION_PATTERNS.sub("[redacted]", cleaned)

class DispatchUnit(BaseModel):
    unit_id: str
    lat: float
    lon: float

class DispatchRequest(BaseModel):
    units: list[DispatchUnit] = Field(default_factory=list)
    max_incidents: int = 10

class ConfirmRequest(BaseModel):
    recommendation_id: int
    operator_note: str = ""

class CitizenReport(BaseModel):
    corridor: str = "unknown"
    latitude: float
    longitude: float
    description: str = ""
    event_cause: str = "others"

def _load_models(app: FastAPI) -> None:
    from .models.clearance import ClearanceModel
    from .models.forecast import ForecastModel
    from .models.severity import SeverityModel
    for attr, loader in (
        ("severity", SeverityModel.load),
        ("clearance", ClearanceModel.load),
        ("forecast", ForecastModel.load),
    ):
        try:
            setattr(app.state, attr, loader())
        except Exception as exc:  # noqa: BLE001 - missing/broken model -> degraded mode
            setattr(app.state, attr, None)
            log.warning("model '%s' unavailable, degrading: %s", attr, exc)

@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Lifespan replaces the deprecated @app.on_event("startup"). Initialize the DB schema and
    # load models ONCE before the app accepts traffic; models live on app.state so every
    # request reuses the in-memory estimators instead of re-reading them from disk. (P3)
    db.init_db()
    _load_models(app)
    yield
    # No teardown: SQLite connections are opened per-request and closed in each handler.

def _incident_record(event_id: str) -> dict:
    conn = db.get_conn()
    try:
        row = db.get_incident(conn, event_id)
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return json.loads(row["payload_json"])

def _run_inference(app: FastAPI, conn, payload: dict) -> None:
    """Best-effort severity+clearance inference at ingest; validated before persist."""
    event_id = payload.get("event_id")
    sev = getattr(app.state, "severity", None)
    clr = getattr(app.state, "clearance", None)
    if sev is not None:
        try:
            out = validate_severity(sev.predict_one(payload))
            db.save_prediction(conn, event_id, "severity", out, sev.version)
        except Exception as exc:  # noqa: BLE001 - never let inference break ingest
            log.warning("severity inference skipped for %s: %s", event_id, exc)
    if clr is not None:
        try:
            out = validate_clearance(clr.predict_one(payload))
            db.save_prediction(conn, event_id, "clearance", out, clr.version)
        except Exception as exc:  # noqa: BLE001
            log.warning("clearance inference skipped for %s: %s", event_id, exc)

def create_app() -> FastAPI:
    app = FastAPI(
        title="CLEAR — Clearance & Logistics Engine for Authority Response",
        lifespan=_lifespan,
    )

    # --- Cross-cutting middleware (NEW) -------------------------------------------------
    # Order matters. Starlette runs the LAST-added middleware OUTERMOST, so we add the rate
    # limiter first (inner) and CORS last (outer). That way: (a) CORS handles the browser
    # preflight OPTIONS and short-circuits it before the limiter ever sees it, and (b) a 429
    # from the limiter still travels back out THROUGH CORS, so the browser gets the
    # Access-Control-Allow-Origin header instead of a opaque CORS failure.
    settings = get_settings()
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            exempt_paths=("/healthz",),  # never rate-limit health checks
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # bearer tokens, not cookies -> no credentialed CORS needed
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # -----------------------------------------------------------------------------------

    @app.get("/healthz")
    def healthz() -> dict:
        return {
            "status": "ok",
            "models": {
                "severity": getattr(app.state, "severity", None) is not None,
                "clearance": getattr(app.state, "clearance", None) is not None,
                "forecast": getattr(app.state, "forecast", None) is not None,
            },
        }

    @app.post("/ingest")
    def ingest(payload: dict, scope: str = Depends(require_scope("operator"))) -> dict:
        conn = db.get_conn()
        try:
            result = ingest_one(conn, payload)
            if result.get("written"):
                _run_inference(app, conn, payload)
            return result
        finally:
            conn.close()

    @app.get("/incidents")
    def incidents(
        limit: int = 100, scope: str = Depends(require_scope("operator", "citizen"))
    ) -> dict:
        conn = db.get_conn()
        try:
            rows = db.get_incidents(conn, limit=limit)
        finally:
            conn.close()
        return {"count": len(rows), "incidents": rows}

    @app.get("/incidents/{event_id}/severity")
    def severity_endpoint(
        event_id: str, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        model = getattr(app.state, "severity", None)
        if model is None:
            raise HTTPException(status_code=503, detail="severity model unavailable (degraded)")
        try:
            return validate_severity(model.predict_one(_incident_record(event_id)))
        except OutputValidationError as exc:
            raise HTTPException(status_code=502, detail=f"invalid model output: {exc}") from exc

    @app.get("/incidents/{event_id}/clearance")
    def clearance_endpoint(
        event_id: str, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        model = getattr(app.state, "clearance", None)
        if model is None:
            raise HTTPException(status_code=503, detail="clearance model unavailable (degraded)")
        try:
            return validate_clearance(model.predict_one(_incident_record(event_id)))
        except OutputValidationError as exc:
            raise HTTPException(status_code=502, detail=f"invalid model output: {exc}") from exc

    @app.get("/corridors/risk")
    def corridor_risk(scope: str = Depends(require_scope("operator", "citizen"))) -> dict:
        settings = get_settings()
        model = getattr(app.state, "forecast", None)
        conn = db.get_conn()
        try:
            if model is None:
                return stale_corridor_risk(conn)  # degraded: last-known risk (constraint 13)
            corridors = [
                r["corridor"]
                for r in conn.execute(
                    "SELECT DISTINCT corridor FROM incidents WHERE corridor IS NOT NULL"
                ).fetchall()
            ]
            if not corridors:
                return {"corridors": [], "note": "no incidents yet"}
            as_of = conn.execute("SELECT MAX(start_ist) AS m FROM incidents").fetchone()["m"]
            now = datetime.fromisoformat(as_of) if as_of else datetime.now(settings.ist_tz)
            results = []
            for corridor in corridors:
                counts = db.recent_hourly_counts(conn, corridor, now.isoformat(), 3)
                try:
                    out = validate_forecast(
                        model.predict_corridor(corridor, counts, now.hour, now.weekday())
                    )
                except OutputValidationError as exc:
                    log.warning("forecast invalid for %s: %s", corridor, exc)
                    continue
                db.upsert_corridor_risk(conn, corridor, out["risk"], model.horizon, stale=0)
                results.append(
                    {"corridor": corridor, "risk": out["risk"],
                     "horizon_hours": model.horizon, "stale": False}
                )
            results.sort(key=lambda r: r["risk"], reverse=True)
            return {
                "as_of_ist": now.isoformat(),
                "horizon_hours": settings.forecast_horizon_hours,
                "corridors": results,
            }
        finally:
            conn.close()

    @app.get("/hotspots")
    def hotspots(
        min_size: Optional[int] = None,
        limit: Optional[int] = None,
        scope: str = Depends(require_scope("operator")),
    ) -> dict:
        # min_size / limit trim the payload server-side: the full batch can emit hundreds of
        # clusters, so callers can request only clusters of >= min_size and cap the count. (P5)
        return hotspot_batch(min_size=min_size, limit=limit)

    @app.post("/dispatch/suggest")
    def dispatch_suggest_endpoint(
        req: DispatchRequest, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        conn = db.get_conn()
        try:
            active = db.get_active_incidents(conn)[: req.max_incidents]
            units = [u.model_dump() for u in req.units]
            if not units or not active:
                return fifo_queue(conn, limit=req.max_incidents)  # degraded baseline queue
            incidents = [
                {
                    "event_id": r["event_id"],
                    "priority": r.get("priority", "medium"),
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                }
                for r in active
                if r.get("latitude") is not None and r.get("longitude") is not None
            ]
            recommendation = dispatch_suggest(units, incidents)
            rec_id = db.save_recommendation(conn, recommendation)
            return {"recommendation_id": rec_id, **recommendation}
        finally:
            conn.close()

    @app.post("/dispatch/confirm")
    def dispatch_confirm(
        req: ConfirmRequest, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        approval = {
            "type": "operator_approval_recommendation",  # approval only, NOT actuation
            "recommendation_id": req.recommendation_id,
            "operator_note": sanitize_text(req.operator_note, 500),
            "approved_at": datetime.now(get_settings().ist_tz).isoformat(),
            "autonomous_actuation": False,
        }
        conn = db.get_conn()
        try:
            ok = db.confirm_recommendation(conn, req.recommendation_id, approval)
        finally:
            conn.close()
        if not ok:
            raise HTTPException(status_code=404, detail="recommendation not found")
        return {"confirmed": True, "approval_event": approval}

    @app.get("/metrics")
    def metrics_endpoint(scope: str = Depends(require_scope("operator"))) -> dict:
        conn = db.get_conn()
        try:
            return {
                "clearance_error": clearance_prediction_error(conn),
                "history": db.get_metrics(conn),
            }
        finally:
            conn.close()

    @app.get("/sla")
    def sla_endpoint(scope: str = Depends(require_scope("operator", "citizen"))) -> dict:
        settings = get_settings()
        conn = db.get_conn()
        try:
            return db.sla_over_resolved(conn, settings.sla_threshold_minutes)
        finally:
            conn.close()

    @app.post("/citizen/report")
    def citizen_report(
        report: CitizenReport, scope: str = Depends(require_scope("citizen"))
    ) -> dict:
        payload = {
            "event_id": f"CIT-{uuid.uuid4().hex[:12]}",
            "start_datetime": datetime.now(get_settings().ist_tz).isoformat(),
            "event_cause": report.event_cause,
            "corridor": report.corridor,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "description": sanitize_text(report.description),  # prompt-injection guard (constraint 16)
            "source_channel": "citizen_app",
            "reported_by": "citizen",
            "status": "open",
        }
        conn = db.get_conn()
        try:
            result = ingest_one(conn, payload)
        finally:
            conn.close()
        return {"report_accepted": True, **result}

    return app

app = create_app()