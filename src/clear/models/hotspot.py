"""Hotspot batch job: DBSCAN over incident coordinates using haversine distance."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

from ..config import get_settings

_EARTH_RADIUS_M = 6371000.0

def detect_hotspots(frame: pd.DataFrame) -> dict[str, Any]:
    settings = get_settings()
    df = frame.copy()
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    if df.empty:
        return {"clusters": [], "n_points": 0, "n_clusters": 0, "note": "no geocoded incidents"}
    coords = np.radians(df[["latitude", "longitude"]].to_numpy())
    eps = settings.hotspot_eps_meters / _EARTH_RADIUS_M  # meters -> radians for haversine
    labels = DBSCAN(
        eps=eps, min_samples=settings.hotspot_min_samples, metric="haversine"
    ).fit_predict(coords)
    df = df.assign(cluster=labels)
    clusters = []
    for cid, g in df[df["cluster"] >= 0].groupby("cluster"):
        corr_mode = g["corridor"].mode() if "corridor" in g else pd.Series(dtype=str)
        clusters.append(
            {
                "cluster_id": int(cid),
                "size": int(len(g)),
                "centroid_lat": round(float(g["latitude"].mean()), 6),
                "centroid_lon": round(float(g["longitude"].mean()), 6),
                "top_corridor": (None if corr_mode.empty else str(corr_mode.iat[0])),
            }
        )
    clusters.sort(key=lambda c: c["size"], reverse=True)
    return {
        "clusters": clusters,
        "n_points": int(len(df)),
        "n_clusters": len(clusters),
        "eps_meters": settings.hotspot_eps_meters,
        "min_samples": settings.hotspot_min_samples,
    }

def run_batch() -> dict[str, Any]:
    """Batch entrypoint: cluster all stored incidents (constraint: hotspot is a batch job)."""
    from .. import db

    conn = db.get_conn()
    try:
        rows = db.get_incidents(conn, limit=100000)
    finally:
        conn.close()
    if not rows:
        return {"clusters": [], "n_points": 0, "n_clusters": 0, "note": "no incidents ingested"}
    return detect_hotspots(pd.DataFrame(rows))
