"""Phase 3: offline MuRIL cache warmer (LOCAL ONLY; never in the Docker build).

    CLEAR_USE_MURIL=1 PYTHONPATH=backend/src \
        .venv/bin/python -m clear.precompute_muril

Embeds the free-text of every training row once and persists the sha1 cache so subsequent
trains / smoke runs are instant. Idempotent: text already cached is skipped.
"""
from __future__ import annotations

import argparse

from . import nlp_muril
from .config import get_settings
from .logging_setup import configure_logging
from .preprocessing import load_and_prepare

log = configure_logging()

def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Warm the MuRIL embedding cache.")
    parser.add_argument("--csv", default=str(settings.raw_data_dir / "incidents.csv"))
    args = parser.parse_args()
    if not settings.use_muril:
        log.warning("CLEAR_USE_MURIL not set; embeddings will be zero and nothing is cached. "
                    "Set CLEAR_USE_MURIL=1 to actually embed.")
    frame = load_and_prepare(args.csv)
    summary = nlp_muril.precompute(frame)
    nlp_muril.save_cache()
    summary["path"] = str(nlp_muril._cache_path())
    print(summary)

if __name__ == "__main__":
    main()
