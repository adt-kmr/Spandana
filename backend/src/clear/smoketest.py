"""Live smoke test: exercises every CLEAR endpoint against a running API.

Secrets come from .env (via Settings): CLEAR_OPERATOR_TOKEN, CLEAR_CITIZEN_TOKEN.
Target base URL comes from CLEAR_BASE_URL (env/.env) or argv[1], default localhost.

Run:  python -m clear.smoketest
      python -m clear.smoketest https://flipkart-gridlock.onrender.com
"""
from __future__ import annotations

import os
import sys

import httpx

from .config import get_settings


def _base_url() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].rstrip("/")
    return os.environ.get("CLEAR_BASE_URL", "http://localhost:8000").rstrip("/")


class Smoke:
    def __init__(self, base: str, op_token: str, cit_token: str):
        self.base = base
        self.op = {"Authorization": f"Bearer {op_token}"}
        self.cit = {"Authorization": f"Bearer {cit_token}"}
        self.client = httpx.Client(timeout=60.0)
        self.passed = 0
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" :: {detail}" if detail else ""))
        if ok:
            self.passed += 1
        else:
            self.failed += 1

    def get(self, path, headers):
        return self.client.get(self.base + path, headers=headers)

    def post(self, path, headers, json=None):
        return self.client.post(self.base + path, headers=headers, json=json)

    def run(self) -> int:
        # 1. health
        try:
            r = self.get("/healthz", self.op)
            models = r.json().get("models", {})
            self.check("GET /healthz", r.status_code == 200 and bool(models) and all(models.values()),
                       f"status={r.status_code} models={models}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /healthz", False, repr(exc))
            print("\nAPI unreachable -- aborting.")
            return 1

        # 2. incidents
        first_id = None
        try:
            r = self.get("/incidents?limit=5", self.op)
            incs = r.json().get("incidents", [])
            first_id = incs[0]["event_id"] if incs else None
            self.check("GET /incidents", r.status_code == 200 and bool(incs),
                       f"count={r.json().get('count')}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /incidents", False, repr(exc))

        # 3. corridors/risk -- Non-corridor/unknown must be filtered out
        try:
            r = self.get("/corridors/risk", self.op)
            corr = r.json().get("corridors", [])
            names = {str(c["corridor"]).strip().lower() for c in corr}
            clean = names.isdisjoint({"non-corridor", "unknown", "none"})
            self.check("GET /corridors/risk", r.status_code == 200 and bool(corr) and clean,
                       f"n={len(corr)} filtered={'yes' if clean else 'NO'} top={corr[0] if corr else None}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /corridors/risk", False, repr(exc))

        # 4. hotspots
        try:
            r = self.get("/hotspots?min_size=5&limit=5", self.op)
            cl = r.json().get("clusters", [])
            self.check("GET /hotspots", r.status_code == 200 and bool(cl), f"clusters={len(cl)}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /hotspots", False, repr(exc))

        # 5. sla
        try:
            r = self.get("/sla", self.op)
            self.check("GET /sla", r.status_code == 200 and "sla_pct" in r.json(),
                       f"sla_pct={r.json().get('sla_pct')}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /sla", False, repr(exc))

        # 6. severity + clearance on first incident
        if first_id:
            try:
                r = self.get(f"/incidents/{first_id}/severity", self.op)
                j = r.json()
                ok = r.status_code == 200 and 0.0 <= float(j.get("confidence", -1)) <= 1.0
                self.check("GET severity", ok, str(j))
            except Exception as exc:  # noqa: BLE001
                self.check("GET severity", False, repr(exc))
            try:
                r = self.get(f"/incidents/{first_id}/clearance", self.op)
                j = r.json()
                ok = (r.status_code == 200
                      and j["p10_minutes"] <= j["median_minutes"] <= j["p90_minutes"])
                self.check("GET clearance", ok, str(j))
            except Exception as exc:  # noqa: BLE001
                self.check("GET clearance", False, repr(exc))

        # 7. dispatch suggest -> confirm (multi-unit so improvement can be > 0)
        try:
            units = [
                {"unit_id": "U1", "lat": 12.97, "lon": 77.59},
                {"unit_id": "U2", "lat": 13.01, "lon": 77.66},
                {"unit_id": "U3", "lat": 12.92, "lon": 77.62},
                {"unit_id": "U4", "lat": 13.05, "lon": 77.59},
            ]
            r = self.post("/dispatch/suggest", self.op, {"units": units, "max_incidents": 8})
            j = r.json()
            rid = j.get("recommendation_id")
            self.check("POST /dispatch/suggest", r.status_code == 200 and rid is not None,
                       f"method={j.get('method')} served={j.get('incidents_served')} improvement_pct={j.get('improvement_pct')}")
            if rid is not None:
                r2 = self.post("/dispatch/confirm", self.op,
                               {"recommendation_id": rid, "operator_note": "smoketest"})
                self.check("POST /dispatch/confirm",
                           r2.status_code == 200 and r2.json().get("confirmed") is True)
        except Exception as exc:  # noqa: BLE001
            self.check("POST /dispatch", False, repr(exc))

        # 8. metrics (+ backfill so it is not empty)
        try:
            self.post("/metrics/backfill?limit=300", self.op)
            r = self.get("/metrics", self.op)
            err = r.json().get("clearance_error", {})
            self.check("GET /metrics", r.status_code == 200 and int(err.get("n", 0)) > 0,
                       f"mae_minutes={err.get('mae_minutes')} n={err.get('n')}")
        except Exception as exc:  # noqa: BLE001
            self.check("GET /metrics", False, repr(exc))

        # 9. citizen report (citizen scope)
        try:
            r = self.post("/citizen/report", self.cit, {
                "corridor": "Mysore Road", "latitude": 12.95, "longitude": 77.55,
                "description": "smoketest pothole", "event_cause": "pot_holes",
            })
            self.check("POST /citizen/report",
                       r.status_code == 200 and r.json().get("report_accepted") is True)
        except Exception as exc:  # noqa: BLE001
            self.check("POST /citizen/report", False, repr(exc))

        print(f"\n{self.passed} passed, {self.failed} failed")
        return 0 if self.failed == 0 else 1


def main() -> int:
    settings = get_settings()
    base = _base_url()
    print(f"CLEAR smoke test -> {base}\n")
    return Smoke(base, settings.operator_token, settings.citizen_token).run()


if __name__ == "__main__":
    raise SystemExit(main())