# CLEAR RUNBOOK — exact ordered commands

Run every command from the project root (`clear/`). Backend only; no UI yet.

## 0. Prerequisites

- Python 3.11+
- A virtual environment is recommended.

```

python -m venv .venv

source .venv/bin/activate        # Windows: .venvScriptsactivate

```

## 1. Configure environment

```

cp .env.example .env

```

(Secrets/tokens come only from `.env`. Defaults work for local dev.)

## 2. Install (editable, with dev extras)

```

pip install -e .[dev]

```

## 3. Generate synthetic data (skip if you have a real CSV)

```

python -m clear.datagen --out data/raw/incidents.csv --n 8173

```

To use real data instead, place your 46-column file at
`data/raw/incidents.csv` and skip this step.

## 4. Ingest into the local store (idempotent)

```

python -m clear.ingestion --csv data/raw/incidents.csv

```

Re-running is safe: duplicates are deduped on `event_id`; malformed rows go to
the dead-letter table.

## 5. Train models

```

python -m clear.train all

```

Trains severity, clearance (survival), and forecast; registers them and writes
the live `<model>.joblib` pointers. (Hotspot is a batch job, not trained.)

## 6. Run the API

```

uvicorn clear.app:app --reload --port 8000

```

Open http://localhost:8000/docs for the interactive API. Health check:

```

curl localhost:8000/healthz

```

## 7. Try a few authenticated calls

```

OP="Authorization: Bearer dev-operator-token"

CIT="Authorization: Bearer dev-citizen-token"

curl -s -H "$OP" localhost:8000/incidents?limit=5

curl -s -H "$OP" localhost:8000/corridors/risk

curl -s -H "$OP" localhost:8000/hotspots

curl -s -H "$OP" localhost:8000/sla

# Dispatch suggestion (operator supplies assumed unit positions)

curl -s -H "$OP" -H "Content-Type: application/json" \

-d '{"units":[{"unit_id":"U1","lat":12.97,"lon":77.59},{"unit_id":"U2","lat":12.90,"lon":77.62}],"max_incidents":5}' \

localhost:8000/dispatch/suggest

# Confirm a recommendation (replace 1 with the returned recommendation_id)

curl -s -H "$OP" -H "Content-Type: application/json" \

-d '{"recommendation_id":1,"operator_note":"approved"}' \

localhost:8000/dispatch/confirm

# Citizen report (free text is sanitized server-side)

curl -s -H "$CIT" -H "Content-Type: application/json" \

-d '{"corridor":"Mysore Road","latitude":12.95,"longitude":77.55,"description":"tree fallen","event_cause":"tree_fall"}' \

localhost:8000/citizen/report

```

## 8. Retrain lifecycle (shadow -> canary -> promote, with rollback)

```

python -m clear.retrain shadow --model clearance

# inspect, then promote a specific version:

python -m clear.retrain promote --model clearance --version <version>

# one-click rollback if needed:

python -m clear.retrain rollback --model clearance

```

## 9. Run tests

```

pytest -q

```

## Troubleshooting

- **`/corridors/risk` or model endpoints return degraded/503:** train models
  first (step 5). The API intentionally stays up and degrades.
- **OR-Tools missing/unsupported platform:** dispatch automatically falls back
  to the deterministic greedy assignment; no action needed.
- **A command fails:** capture the full error and hand it back to the authoring
  model. Do not hand-edit generated files.
