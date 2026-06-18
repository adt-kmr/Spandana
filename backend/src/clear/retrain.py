"""Retrain lifecycle: shadow -> canary -> promote with one-click rollback (constraint 12).

Runnable local scripts/stubs. Stages live in the model_registry; the live serving
pointer is the unversioned '<model>.joblib' file that promote/rollback re-point.
"""
from __future__ import annotations

import argparse
import shutil
from typing import Optional

from . import db
from .config import get_settings
from .logging_setup import configure_logging
from .train import train_model

log = configure_logging()
STAGES = ["candidate", "shadow", "canary", "production", "archived"]

def _conn():
    db.init_db()
    return db.get_conn()

def _activate(model: str, version: str) -> None:
    """Re-point the live '<model>.joblib' artifact used at serve time to this version."""
    settings = get_settings()
    src = settings.model_dir / f"{model}-{version}.joblib"
    dst = settings.model_dir / f"{model}.joblib"
    if src.exists():
        shutil.copyfile(src, dst)

def shadow(model: str) -> dict:
    """Train a fresh candidate and register it in shadow (no promotion)."""
    res = train_model(model)
    conn = _conn()
    try:
        db.set_model_stage(conn, model, res["version"], "shadow")
    finally:
        conn.close()
    log.info("shadow: %s %s", model, res["version"])
    return {**res, "stage": "shadow"}

def canary(model: str, version: str) -> dict:
    conn = _conn()
    try:
        db.set_model_stage(conn, model, version, "canary")
    finally:
        conn.close()
    log.info("canary: %s %s", model, version)
    return {"model": model, "version": version, "stage": "canary"}

def promote(model: str, version: str) -> dict:
    """Promote a version to production, archiving the previous production version."""
    conn = _conn()
    try:
        for m in db.get_models(conn, model):
            if m["stage"] == "production" and m["version"] != version:
                db.set_model_stage(conn, model, m["version"], "archived")
        db.set_model_stage(conn, model, version, "production")
        _activate(model, version)
    finally:
        conn.close()
    log.info("promote: %s %s -> production", model, version)
    return {"model": model, "version": version, "stage": "production"}

def rollback(model: str) -> dict:
    """One-click rollback: restore the most recent archived version to production."""
    conn = _conn()
    try:
        models = db.get_models(conn, model)  # newest first
        archived = [m for m in models if m["stage"] == "archived"]
        if not archived:
            return {"model": model, "error": "no archived version to roll back to"}
        target = archived[0]
        for m in models:
            if m["stage"] == "production":
                db.set_model_stage(conn, model, m["version"], "archived")
        db.set_model_stage(conn, model, target["version"], "production")
        _activate(model, target["version"])
    finally:
        conn.close()
    log.info("rollback: %s -> %s", model, target["version"])
    return {"model": model, "version": target["version"], "stage": "production"}

def _clearance_mae_on(model_obj, records: list[dict]) -> Optional[float]:
    """MAE of median prediction vs actual on resolved (observed, non-admin) raw records."""
    import numpy as np

    from .preprocessing import clearance_label, parse_utc
    errs = []
    for rec in records:
        d, observed, admin = clearance_label(
            parse_utc(rec.get("start_datetime")),
            parse_utc(rec.get("resolved_datetime")),
            parse_utc(rec.get("closed_datetime")),
            None, rec.get("status"),
        )
        if d is None or observed != 1 or admin != 0:
            continue
        try:
            pred = model_obj.predict_one(rec)["median_minutes"]
        except Exception:  # noqa: BLE001
            continue
        errs.append(abs(float(pred) - float(d)))
    return float(np.mean(errs)) if errs else None

def auto_cycle(model: str = "clearance", min_rel_improvement: float = 0.0,
               holdout_frac: float = 0.2, force: bool = False) -> dict:
    """Time-split GATED retrain (clearance only). Trains a candidate on the older split,
    compares it to the current production model on the newest holdout, and ONLY promotes (after
    a final FULL-data retrain) if it beats production by >= min_rel_improvement. Otherwise
    production is left untouched. The candidate used for the gate is kept in memory and never
    written to disk, so the live pointer is never polluted before the decision."""
    if model != "clearance":
        return {"model": model, "error": "auto_cycle gate is clearance-only; use "
                "shadow()/canary()/promote() for severity/forecast"}
    import pandas as pd

    from .models.clearance import ClearanceModel
    from .preprocessing import (apply_column_aliases, normalize_columns, parse_utc,
                                prepare_records, scrub_sentinels)
    from .train import _version, train_model

    settings = get_settings()
    csv = settings.raw_data_dir / "incidents.csv"
    if not csv.exists():
        return {"model": model, "error": f"no dataset at {csv}"}
    raw = scrub_sentinels(apply_column_aliases(normalize_columns(
        pd.read_csv(csv, dtype=str, keep_default_na=False))))
    dated = [(r, parse_utc(r.get("start_datetime"))) for r in raw.to_dict(orient="records")]
    dated = [(r, s) for r, s in dated if s is not None]
    dated.sort(key=lambda t: t[1])
    if len(dated) < 100:
        return {"model": model, "error": "too few dated rows for a holdout split"}
    cut = int(len(dated) * (1 - holdout_frac))
    train_records = [r for r, _ in dated[:cut]]
    holdout_records = [r for r, _ in dated[cut:]]
    as_of = max(s for _, s in dated[:cut]).astimezone(settings.ist_tz)

    candidate = ClearanceModel.train(prepare_records(train_records, as_of=as_of),
                                     _version() + "-cand")  # in memory only; no .save()
    try:
        prod = ClearanceModel.load()  # current production pointer
    except Exception as exc:  # noqa: BLE001 - no prod yet -> just train+promote
        log.warning("no production clearance model (%s); training fresh", exc)
        final = train_model("clearance"); promote("clearance", final["version"])
        return {"model": model, "action": "promoted", "promoted": True,
                "version": final["version"], "reason": "no prior production model"}

    cand_mae = _clearance_mae_on(candidate, holdout_records)
    prod_mae = _clearance_mae_on(prod, holdout_records)
    if cand_mae is None or prod_mae is None:
        return {"model": model, "action": "skipped", "promoted": False,
                "reason": "insufficient holdout resolved rows",
                "cand_mae": cand_mae, "prod_mae": prod_mae}
    improved = cand_mae <= prod_mae * (1 - min_rel_improvement)
    if not improved and not force:
        return {"model": model, "action": "kept_production", "promoted": False,
                "prod_mae": round(prod_mae, 2), "cand_mae": round(cand_mae, 2)}
    final = train_model("clearance")          # FULL-data model is what actually ships
    promote("clearance", final["version"])     # archives prior prod + repoints pointer
    return {"model": model, "action": "promoted", "promoted": True,
            "version": final["version"],
            "prod_mae": round(prod_mae, 2), "cand_mae": round(cand_mae, 2)}

def main() -> None:
    parser = argparse.ArgumentParser(description="CLEAR retrain lifecycle.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("shadow").add_argument("--model", required=True)
    for cmd in ("canary", "promote"):
        p = sub.add_parser(cmd)
        p.add_argument("--model", required=True)
        p.add_argument("--version", required=True)
    sub.add_parser("rollback").add_argument("--model", required=True)
    auto = sub.add_parser("auto")
    auto.add_argument("--model", default="clearance")
    auto.add_argument("--min-improvement", type=float, default=0.0)
    auto.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "shadow":
        out = shadow(args.model)
    elif args.command == "canary":
        out = canary(args.model, args.version)
    elif args.command == "promote":
        out = promote(args.model, args.version)
    elif args.command == "auto":
        out = auto_cycle(args.model, min_rel_improvement=args.min_improvement, force=args.force)
    else:
        out = rollback(args.model)
    print(out)

if __name__ == "__main__":
    main()
