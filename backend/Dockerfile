# syntax=docker/dockerfile:1

#####################################################################
# Stage 1: builder — train + precompute, then throw away heavy inputs
#####################################################################
FROM python:3.11-slim AS builder

# LightGBM needs the OpenMP runtime (libgomp1) on Debian slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Seed CSV (training) + MuRIL cache (so build attaches multilingual features WITHOUT torch).
COPY data/raw ./data/raw
COPY data/seed ./data/seed
RUN mkdir -p data/models && cp data/seed/muril_cache.joblib data/models/muril_cache.joblib

# Build with MuRIL ON so the text model learns multilingual signal, then FREEZE the
# precomputed /nlp/severity response table. Both run at BUILD time only.
ENV CLEAR_USE_MURIL=1
RUN CLEAR_SKIP_MODEL_REGISTRY=1 CLEAR_USE_MURIL=1 python -m clear.train all \
    && CLEAR_USE_MURIL=1 python -m clear.nlp_responses \
    && test -f data/models/forecast.joblib \
    && test -f data/models/severity.joblib \
    && test -f data/models/nlp_responses.joblib

#####################################################################
# Stage 2: runtime — slim image, NO torch, NO muril cache, NO text model
#####################################################################
FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CLEAR_USE_MURIL=0

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Raw seed CSV kept ONLY so bootstrap can seed an empty DB; tiny vs embeddings.
COPY data/raw ./data/raw

# Copy ONLY the runtime artifacts from the builder. Deliberately NOT copying
# severity_text.joblib, muril_cache.joblib, or versioned duplicates.
RUN mkdir -p data/models
COPY --from=builder /app/data/models/severity.joblib       data/models/severity.joblib
COPY --from=builder /app/data/models/clearance.joblib      data/models/clearance.joblib
COPY --from=builder /app/data/models/forecast.joblib       data/models/forecast.joblib
COPY --from=builder /app/data/models/nlp_responses.joblib  data/models/nlp_responses.joblib

COPY gunicorn.conf.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]