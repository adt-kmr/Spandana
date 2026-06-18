# CLEAR — Clearance & Logistics Engine for Authority Response

CLEAR is a **decision-support** backend for traffic-incident response in
Bengaluru. It ingests incident reports, estimates how long each incident will
take to clear (with honest uncertainty), classifies severity, nowcasts
short-horizon corridor risk, finds spatial hotspots, and proposes — but never
executes — a ranked dispatch plan that a human operator must confirm.

> CLEAR is **not** a traffic-signal control system and is unrelated to the live
> BTP “ASTraM” product. It never actuates signals.

## Why the design looks the way it does

This MVP bakes in 19 pre-mortem fixes. The non-obvious ones:

- **Censored survival analysis for clearance time.** ~94% of incidents have no
  recorded resolution, so a plain regression would be badly biased. CLEAR fits a
  Log-Normal AFT model on right-censored durations and reports a **median +
  P10–P90 interval**, never a bare point ETA. Missing resolutions are censored,
  never imputed.
- **UTC → IST before any time feature.** Hour-of-day matters for traffic; all
  timestamps are converted to IST (+05:30) before deriving features.
- **Severity is a calibrated band + confidence**, not a fake 0–100 score.
- **Forecast is a strict 3-hour nowcast** — no long-horizon forecasting.
- **Dispatch is advisory.** It outputs a ranked suggestion vs. a FIFO/nearest
  baseline, labels unit positions as assumed/external, and requires an explicit
  operator-confirmation event. Zero autonomous actuation.
- **Robust ingest.** Idempotency on `event_id`, bounded retries with backoff,
  and a dead-letter store for poison messages.
- **Honest operations.** Output validation rejects NaN/out-of-range before
  persisting; correctness metrics (predicted-vs-actual MAE, PSI drift) are
  tracked; the API degrades gracefully (last-known risk + FIFO queue, labeled
  stale) when a model is missing.

## Architecture (local = logical AWS flow)

```

ingest -> validate -> idempotency -> store(SQLite) -> infer -> output-validate -> serve(FastAPI)

```

See `infra/README.md` for the optional AWS v2 mapping (not required to run).

## Layout

```

src/clear/

config.py          env-driven settings (CLEAR_* / .env)

schema.py          46-column raw contract + IncidentIn validator

db.py              SQLite store: incidents, DLQ, predictions, registry, metrics

preprocessing.py   UTC->IST, normalization, censoring, junction snap, vehicle gating

datagen.py         synthetic 46-column Bengaluru CSV generator

ingestion.py       validate -> idempotency -> store (+ DLQ, retries)

validation.py      output validator (NaN/range/interval-order)

metrics.py         MAE + PSI drift

auth.py            operator/citizen bearer scopes

degradation.py     stale corridor risk + FIFO fallback queue

models/            severity, clearance, forecast, hotspot, dispatch

train.py           train one/all models

retrain.py         shadow -> canary -> promote + rollback

app.py             FastAPI wiring (role-scoped, degradation-aware)

tests/               preprocessing, idempotency, output-validation

infra/               optional AWS v2 notes (no-op locally)

```

## Quickstart

See `RUNBOOK.md` for the exact, ordered commands. In short:

```

cp .env.example .env

pip install -e .[dev]

python -m clear.datagen --out data/raw/incidents.csv --n 8173

python -m clear.ingestion --csv data/raw/incidents.csv

python -m clear.train all

uvicorn clear.app:app --reload --port 8000

```

Drop a real 46-column CSV at `data/raw/incidents.csv` to use it instead of the
synthetic generator.

## API (all responses are advisory)

| Method | Path                            | Scope             | Purpose                                  |
| ------ | ------------------------------- | ----------------- | ---------------------------------------- |
| GET    | `/healthz`                      | none              | liveness + which models are loaded       |
| POST   | `/ingest`                       | operator          | ingest one raw incident (+ inference)    |
| GET    | `/incidents`                    | operator/citizen  | recent incidents                         |
| GET    | `/incidents/{id}/severity`      | operator          | calibrated severity band + confidence    |
| GET    | `/incidents/{id}/clearance`     | operator          | median + P10-P90 clearance interval      |
| GET    | `/corridors/risk`               | operator/citizen  | 3h corridor nowcast (stale if degraded)  |
| GET    | `/hotspots`                     | operator          | DBSCAN hotspot batch                      |
| POST   | `/dispatch/suggest`             | operator          | ranked suggestion vs FIFO baseline        |
| POST   | `/dispatch/confirm`             | operator          | record operator approval (no actuation)   |
| GET    | `/metrics`                      | operator          | predicted-vs-actual MAE + history         |
| GET    | `/sla`                          | operator/citizen  | SLA% over the resolved subset only        |
| POST   | `/citizen/report`               | citizen           | sanitized citizen incident report         |

Authenticate with `Authorization: Bearer <token>` using the operator/citizen
tokens from `.env`.

## Tests

```

pytest -q

```

Covers UTC→IST conversion, the censoring contract, ingest idempotency +
dead-letter, and output validation.

## Frontend

The React/Vite dashboard is intentionally **out of scope** for this backend pass
and will be added later against the API above.
