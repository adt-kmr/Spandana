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

# Seed CSV so the first boot can ingest. Models are trained at boot, NOT baked into the image.
COPY data/raw ./data/raw
COPY gunicorn.conf.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

EXPOSE 8000
CMD ["./entrypoint.sh"]
