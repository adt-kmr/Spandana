"""FastAPI app: ingest -> infer -> output-validate -> serve, with role-scoped access.
Models are loaded once at startup into app.state; a missing model degrades gracefully
(constraint 13) instead of crashing the API."""
from __future__ import annotations

import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

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

# Catch-all corridor buckets that are not real ranked corridors. They dominate raw incident
# volume (so they pin the risk score at 100) but carry no operational meaning, so they are
# excluded from the /corridors/risk ranking.
_NON_RANKABLE_CORRIDORS = {"non-corridor", "unknown", "none", ""}


def sanitize_text(text: str | None, max_len: int = 1000) -> str:
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


class NlpSeverityRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    event_cause: str | None = None  # None => infer from the corpus phrase, else "others"
    corridor: str = "unknown"
    latitude: float | None = None
    longitude: float | None = None
    comment: str = ""


class ResourcePlanRequest(BaseModel):
    attendees: int = Field(ge=0)
    road_closures: int = Field(default=0, ge=0)
    event_type: str | None = None

class EventImpactRequest(BaseModel):
    event_type: str | None = None
    base_minutes: float | None = None
    base_risk: float | None = None


def _load_models(app: FastAPI) -> None:
    from .models.clearance import ClearanceModel
    from .models.forecast import ForecastModel
    from .models.severity import SeverityModel
    app.state.models_error = {}
    for attr, loader in (
        ("severity", SeverityModel.load),
        ("clearance", ClearanceModel.load),
        ("forecast", ForecastModel.load),
    ):
        try:
            setattr(app.state, attr, loader())
        except Exception as exc:  # noqa: BLE001 - missing/broken model -> degraded mode
            setattr(app.state, attr, None)
            app.state.models_error[attr] = f"{type(exc).__name__}: {str(exc)}"
            log.exception("model '%s' unavailable, degrading", attr)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Lifespan replaces the deprecated @app.on_event("startup"). Initialize the DB schema and
    # load models ONCE before the app accepts traffic; models live on app.state so every
    # request reuses the in-memory estimators instead of re-reading them from disk. (P3)
    db.init_db()
    _load_models(app)
    yield
    # No teardown: connections are opened per-request and closed in each handler.


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
        title="CLEAR -- Clearance & Logistics Engine for Authority Response",
        lifespan=_lifespan,
    )
    
    # --- Rate limiting: fixed-window 429 guard (flag-gated). Registered BEFORE CORS so the
    #     CORS middleware stays the OUTERMOST layer and 429 responses keep their CORS headers. ---
    settings = get_settings()
    if getattr(settings, "rate_limit_enabled", False):
        app.add_middleware(
            RateLimitMiddleware,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
            exempt_paths={"/healthz"},
        )

    # --- CORS: allow the browser frontend to call the API (fixes OPTIONS 405) ---
    settings = get_settings()
    origins = getattr(settings, "cors_origins", None) or [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # ---------------------------------------------------------------------------
    
    @app.get("/healthz")
    def healthz() -> dict:
        from .nlp_responses import load as _load_nlp_table
        return {
            "status": "ok",
            "models": {
                "severity": getattr(app.state, "severity", None) is not None,
                "severity_text": getattr(app.state, "severity_text", None) is not None,
                "clearance": getattr(app.state, "clearance", None) is not None,
                "forecast": getattr(app.state, "forecast", None) is not None,
                "nlp_severity": bool(_load_nlp_table()),
            },
            "models_error": getattr(app.state, "models_error", {}),
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
                if r["corridor"]
                and r["corridor"].strip().lower() not in _NON_RANKABLE_CORRIDORS
            ]
            if not corridors:
                return {"corridors": [], "note": "no rankable corridors yet"}
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
        min_size: int | None = None,
        limit: int | None = None,
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
                    "priority": r["priority"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                }
                for r in active
            ]
            result = dispatch_suggest(units, incidents)
            result["recommendation_id"] = db.save_recommendation(conn, result)
            return result
        finally:
            conn.close()

    @app.post("/dispatch/confirm")
    def dispatch_confirm_endpoint(
        req: ConfirmRequest, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        # Human-in-the-loop gate (constraint 7): a recommendation only becomes an action when an
        # operator explicitly confirms it. The service never actuates anything on its own.
        conn = db.get_conn()
        try:
            ok = db.confirm_recommendation(conn, req.recommendation_id, req.operator_note)
            if not ok:
                raise HTTPException(status_code=404, detail="recommendation not found")
            return {"confirmed": True, "recommendation_id": req.recommendation_id}
        finally:
            conn.close()

    @app.post("/nlp/severity")
    def nlp_severity(
        body: NlpSeverityRequest,
        _claims=Depends(require_scope("citizen")),
    ) -> dict:
        """Multilingual triage via a precomputed, torch-free response table.
        The model is NEVER loaded at request time (Render memory): we serve
        normalize -> exact -> nearest cached phrase -> safe default.
        """
        from .nlp_responses import lookup
        result = lookup(sanitize_text(body.text))
        # validate_severity asserts band in SEVERITY_BANDS and confidence in [0,1];
        # it returns only {band, confidence}, so we return our richer dict (keeps `source`).
        validate_severity(result)
        return result

    @app.post("/citizen/report")
    def citizen_report(
        report: CitizenReport, scope: str = Depends(require_scope("citizen"))
    ) -> dict:
        # Citizen reports are untrusted: free text is sanitized (constraint 16) and a synthetic
        # event_id is minted so citizens cannot overwrite authority incident IDs.
        event_id = f"CIT-{uuid.uuid4().hex[:12]}"
        payload = {
            "event_id": event_id,
            "start_datetime": datetime.now(get_settings().ist_tz).isoformat(),
            "corridor": sanitize_text(report.corridor, 120),
            "latitude": report.latitude,
            "longitude": report.longitude,
            "description": sanitize_text(report.description),
            "event_cause": sanitize_text(report.event_cause, 60),
            "priority": "low",
            "status": "open",
            "source": "citizen",
        }
        conn = db.get_conn()
        try:
            result = ingest_one(conn, payload)
            if result.get("written"):
                _run_inference(app, conn, payload)
        finally:
            conn.close()
        return {"report_accepted": True, "event_id": event_id}

    @app.get("/sla")
    def sla_endpoint(scope: str = Depends(require_scope("operator", "citizen"))) -> dict:
        settings = get_settings()
        conn = db.get_conn()
        try:
            return db.sla_over_resolved(conn, settings.sla_threshold_minutes)
        finally:
            conn.close()

    @app.get("/events/types")
    def event_types(scope: str = Depends(require_scope("operator", "citizen"))) -> dict:
        from .event_intel import known_event_types
        return {"event_types": known_event_types()}

    @app.post("/events/impact")
    def events_impact(
        req: EventImpactRequest,
        scope: str = Depends(require_scope("operator", "citizen")),
    ) -> dict:
        from .event_intel import apply_impact
        return apply_impact(req.event_type, base_minutes=req.base_minutes, base_risk=req.base_risk)

    @app.post("/resources/plan")
    def resources_plan(
        req: ResourcePlanRequest,
        scope: str = Depends(require_scope("operator")),
    ) -> dict:
        from .resource_planner import plan_resources
        return plan_resources(req.attendees, req.road_closures, req.event_type)

    @app.get("/diversions")
    def diversions(
        corridor: str,
        scope: str = Depends(require_scope("operator", "citizen")),
    ) -> dict:
        from .diversion import diversions_for
        return diversions_for(corridor)

    @app.get("/weather/rain-risk")
    def weather_rain_risk(
        corridor: str,
        scope: str = Depends(require_scope("operator", "citizen")),
    ) -> dict:
        from .rain_clog import corridor_rain_risk
        return corridor_rain_risk(corridor)

    @app.get("/metrics/by-event")
    def metrics_by_event(scope: str = Depends(require_scope("operator"))) -> dict:
        from .metrics import clearance_error_by_event
        conn = db.get_conn()
        try:
            return clearance_error_by_event(conn)
        finally:
            conn.close()

    @app.get("/metrics")
    def metrics_endpoint(scope: str = Depends(require_scope("operator"))) -> dict:
        conn = db.get_conn()
        try:
            return {"clearance_error": clearance_prediction_error(conn)}
        finally:
            conn.close()

    @app.post("/metrics/backfill")
    def metrics_backfill(
        limit: int = 500, scope: str = Depends(require_scope("operator"))
    ) -> dict:
        # /metrics is empty until clearance predictions exist to compare against actuals. The
        # bulk seed ingest does NOT run inference (only the live /ingest path does), so this
        # one-shot backfill scores the model over already-resolved incidents and logs the
        # predictions, giving /metrics a real MAE. NOTE: these rows were in the training set,
        # so the resulting MAE is in-sample (optimistic) -- label it as such when presenting.
        model = getattr(app.state, "clearance", None)
        if model is None:
            raise HTTPException(status_code=503, detail="clearance model unavailable (degraded)")
        conn = db.get_conn()
        written = skipped = 0
        try:
            rows = conn.execute(
                """SELECT event_id, payload_json FROM incidents
                   WHERE event_observed = 1 AND admin_close = 0 AND duration_minutes IS NOT NULL
                   ORDER BY start_ist DESC LIMIT %s""",
                (limit,),
            ).fetchall()
            for r in rows:
                try:
                    payload = json.loads(r["payload_json"])
                    out = validate_clearance(model.predict_one(payload))
                    db.save_prediction(conn, r["event_id"], "clearance", out, model.version)
                    written += 1
                except Exception as exc:  # noqa: BLE001 - skip a bad row, keep going
                    skipped += 1
                    log.warning("backfill skipped %s: %s", r["event_id"], exc)
            return {
                "backfilled": written,
                "skipped": skipped,
                "clearance_error": clearance_prediction_error(conn),
            }
        finally:
            conn.close()

    @app.get("/admin/drift")
    def admin_drift(scope: str = Depends(require_scope("operator"))) -> dict:
        from .monitor import drift_report
        return drift_report()

    @app.post("/admin/retrain")
    def admin_retrain(
        model: str = "clearance",
        min_improvement: float = 0.0,
        force: bool = False,
        scope: str = Depends(require_scope("operator")),
    ) -> dict:
        from .retrain import auto_cycle
        result = auto_cycle(model, min_rel_improvement=min_improvement, force=force)
        if result.get("promoted"):
            _load_models(app)  # hot-swap the new model into THIS worker's app.state
        return result

    return app


app = create_app()