# syntax=docker/dockerfile:1
FROM python:3.11-slim

# LightGBM needs the OpenMP runtime (libgomp1) on Debian slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first (better layer caching), then the package.
COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

# Seed CSV is needed at BUILD time so the models can be trained into the image.
COPY data/raw ./data/raw

# Bake the trained models into the image: train once during build (reads the seed CSV, writes
# data/models/*.joblib) so the container boots instantly — no train-at-boot, no cold-start
# retrain, no OOM risk on small instances. CLEAR_SKIP_MODEL_REGISTRY=1 saves the artifacts but
# skips the Postgres registry write, so the build needs no live database. The final test fails
# the build loudly if the models did not bake.
RUN mkdir -p data/models \
    && CLEAR_SKIP_MODEL_REGISTRY=1 python -m clear.train all \
    && test -f data/models/forecast.joblib

COPY gunicorn.conf.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]