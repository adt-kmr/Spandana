"""Phase 3: offline MuRIL cache warmer (LOCAL ONLY; torch required here, NOT at runtime).

    CLEAR_USE_MURIL=1 PYTHONPATH=backend/src \
        .venv/bin/python -m clear.precompute_muril

Embeds (a) every training row's free-text and (b) the trilingual citizen corpus once,
then persists the sha1 cache. Idempotent: already-cached text is skipped.
"""
from __future__ import annotations

import argparse

from . import nlp_muril
from .config import get_settings
from .logging_setup import configure_logging
from .nlp_corpus import all_phrases
from .preprocessing import load_and_prepare

log = configure_logging()

def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Warm the MuRIL embedding cache.")
    parser.add_argument("--csv", default=str(settings.raw_data_dir / "incidents.csv"))
    parser.add_argument("--no-corpus", action="store_true", help="skip the trilingual corpus")
    args = parser.parse_args()
    if not settings.use_muril:
        log.warning("CLEAR_USE_MURIL not set; embeddings will be zero and nothing is cached. "
                    "Set CLEAR_USE_MURIL=1 to actually embed.")
    frame = load_and_prepare(args.csv)
    summary = nlp_muril.precompute(frame)
    if not args.no_corpus:
        phrases = all_phrases()
        nlp_muril.embed_texts(phrases)  # warm the EN/HI/KN corpus
        summary["corpus_phrases"] = len(phrases)
    nlp_muril.save_cache()
    summary["cached_vectors"] = len(nlp_muril.load_cache())
    summary["path"] = str(nlp_muril._cache_path())
    print(summary)

if __name__ == "__main__":
    main()
