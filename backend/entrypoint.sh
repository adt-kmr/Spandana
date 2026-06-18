#!/usr/bin/env bash
set -euo pipefail

# One-time idempotent bootstrap: schema + (seed ingest if empty) + (train if no models).
python -m clear.bootstrap

# Serve. Render/App Runner inject $PORT; gunicorn.conf.py binds to it.
exec gunicorn -c gunicorn.conf.py clear.app:app
