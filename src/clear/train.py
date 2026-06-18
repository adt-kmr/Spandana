"""Training orchestrator: train one or all models with deterministic seeds."""
from __future__ import annotations

import argparse
import os
import time

import pandas as pd

from . import db
from .config import get_settings
from .logging_setup import configure_logging
from .models.clearance import ClearanceModel
from .models.forecast import ForecastModel
from .models.severity import SeverityModel
from .preprocessing import load_and_prepare

log = configure_logging()
_TRAINERS = {
    "severity": SeverityModel,
    "clearance": ClearanceModel,
    "forecast": ForecastModel,
}


def _skip_registry() -> bool:
    """True when model artifacts should be saved WITHOUT writing the Postgres model registry.
    Set during docker build (no live DB) to bake models into the image; unset at runtime so
    normal retrains register as before."""
    return os.environ.get("CLEAR_SKIP_MODEL_REGISTRY", "").strip().lower() in ("1", "true", "yes")


def _version() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _frame() -> pd.DataFrame:
    settings = get_settings()
    csv = settings.raw_data_dir / "incidents.csv"
    if not csv.exists():
        raise FileNotFoundError(f"no dataset at {csv}; run datagen or drop a real CSV there")
    return load_and_prepare(str(csv))


def train_model(name: str, frame: pd.DataFrame | None = None, version: str | None = None) -> dict:
    if name not in _TRAINERS:
        raise ValueError(f"unknown model: {name}")
    frame = _frame() if frame is None else frame
    version = version or _version()
    model = _TRAINERS[name].train(frame, version)
    path = model.save()
    # The .joblib artifact is already on disk here. The Postgres registry write is skipped during
    # build-time baking (CLEAR_SKIP_MODEL_REGISTRY=1) so docker build needs no database; at
    # runtime the var is unset and registration happens exactly as before. Serving loads models
    # from data/models/<name>.joblib on disk, not the registry, so skipping it is safe.
    if _skip_registry():
        log.info("CLEAR_SKIP_MODEL_REGISTRY set; baked %s without DB registration", name)
    else:
        db.init_db()
        conn = db.get_conn()
        try:
            db.register_model(conn, name, version, "production", path, {"trained_rows": int(len(frame))})
        finally:
            conn.close()
    log.info("trained %s version=%s -> %s", name, version, path)
    return {"model": name, "version": version, "path": str(path)}


def train_all() -> list[dict]:
    frame = _frame()
    version = _version()
    results = []
    for name in ("severity", "clearance", "forecast"):
        try:
            results.append(train_model(name, frame=frame, version=version))
        except Exception as exc:  # noqa: BLE001 - keep training the remaining models
            log.error("training %s failed: %s", name, exc)
            results.append({"model": name, "error": str(exc)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CLEAR models.")
    parser.add_argument("target", choices=["all", "severity", "clearance", "forecast"])
    args = parser.parse_args()
    out = train_all() if args.target == "all" else [train_model(args.target)]
    print(out)


if __name__ == "__main__":
    main()