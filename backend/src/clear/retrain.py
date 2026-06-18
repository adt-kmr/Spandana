"""Retrain lifecycle: shadow -> canary -> promote with one-click rollback (constraint 12).

Runnable local scripts/stubs. Stages live in the model_registry; the live serving
pointer is the unversioned '<model>.joblib' file that promote/rollback re-point.
"""
from __future__ import annotations

import argparse
import shutil

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

def main() -> None:
    parser = argparse.ArgumentParser(description="CLEAR retrain lifecycle.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("shadow").add_argument("--model", required=True)
    for cmd in ("canary", "promote"):
        p = sub.add_parser(cmd)
        p.add_argument("--model", required=True)
        p.add_argument("--version", required=True)
    sub.add_parser("rollback").add_argument("--model", required=True)
    args = parser.parse_args()
    if args.command == "shadow":
        out = shadow(args.model)
    elif args.command == "canary":
        out = canary(args.model, args.version)
    elif args.command == "promote":
        out = promote(args.model, args.version)
    else:
        out = rollback(args.model)
    print(out)

if __name__ == "__main__":
    main()
