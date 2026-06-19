"""Phase 3: MuRIL multilingual text embeddings for severity (LOCAL, flag-gated).

This is the ONLY module that imports torch/transformers, and it does so lazily (inside
functions) so importing it never crashes the app when the optional `nlp` extra is absent.
Intentionally NOT wired into the Docker build or render.yaml: exercised locally only,
behind CLEAR_USE_MURIL=1.

Pipeline: text -> MuRIL (batched, device-aware) -> attention-masked mean-pool -> 768-d ->
L2-normalize. Results are cached by sha1(text) so the templated synthetic descriptions
(very few unique strings) embed near-instantly on re-runs.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from .config import get_settings

log = logging.getLogger("clear.nlp_muril")

EMBED_DIM = 768

# Lazy singletons (populated on first real embedding call).
_tokenizer = None
_model = None
_device: Optional[str] = None
_torch = None

# sha1 -> np.ndarray(768,) cache, lazily loaded from disk.
_cache: Optional[dict] = None

def _select_device() -> str:
    global _torch
    import torch  # local import; only reached when embedding is actually needed
    _torch = torch
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def _load_model():
    """Lazily import + load tokenizer/model once. Returns (tokenizer, model, device)."""
    global _tokenizer, _model, _device
    if _model is not None:
        return _tokenizer, _model, _device
    from transformers import AutoModel, AutoTokenizer  # local import
    settings = get_settings()
    _device = _select_device()
    _tokenizer = AutoTokenizer.from_pretrained(settings.muril_model_name)
    model = AutoModel.from_pretrained(settings.muril_model_name)
    model.eval()
    model.to(_device)
    # fp16 on accelerators ~2x faster with negligible embedding-quality loss; keep fp32 on CPU.
    if _device in ("cuda", "mps"):
        try:
            model.half()
        except Exception:  # noqa: BLE001 - fall back to fp32 if half() unsupported
            log.warning("half() failed on %s; using fp32", _device)
    _model = model
    log.info("loaded MuRIL %s on %s", settings.muril_model_name, _device)
    return _tokenizer, _model, _device

def _cache_path() -> Path:
    return get_settings().muril_cache_path

def load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    path = _cache_path()
    if path.exists():
        import joblib
        try:
            _cache = dict(joblib.load(path))
        except Exception:  # noqa: BLE001 - corrupt cache => start fresh
            log.warning("could not read MuRIL cache at %s; starting empty", path)
            _cache = {}
    else:
        _cache = {}
    return _cache

def save_cache() -> Path:
    import joblib
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(load_cache(), path)
    return path

def _key(text: str) -> str:
    return hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()

def compose_text(frame: pd.DataFrame) -> list[str]:
    """Per-row text to embed, from the free-text columns present in the modeling frame.
    prepare_records keeps `description` and `comment` (sub_cause is dropped upstream), so we
    embed exactly the same text that cue_count reads."""
    desc = frame["description"] if "description" in frame else pd.Series([""] * len(frame), index=frame.index)
    comm = frame["comment"] if "comment" in frame else pd.Series([""] * len(frame), index=frame.index)
    return (desc.fillna("").astype(str) + " " + comm.fillna("").astype(str)).str.strip().tolist()

def _embed_batch(texts: list[str]) -> np.ndarray:
    tok, model, device = _load_model()
    settings = get_settings()
    enc = tok(
        texts, padding=True, truncation=True,
        max_length=settings.muril_max_length, return_tensors="pt",
    ).to(device)
    with _torch.no_grad():
        out = model(**enc)
    last = out.last_hidden_state                       # (B, T, 768)
    mask = enc["attention_mask"].unsqueeze(-1).type_as(last)
    summed = (last * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    mean = summed / counts                             # attention-masked mean-pool
    vecs = mean.float().cpu().numpy()
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vecs / norms).astype(np.float32)           # L2-normalized

def embed_texts(texts: Iterable[str]) -> np.ndarray:
    """Return an (N, 768) float32 matrix of MuRIL embeddings for `texts`.

    - Disabled (CLEAR_USE_MURIL off) or torch/transformers unavailable => zero matrix
      (graceful no-op so severity degrades to its non-MuRIL behavior).
    - sha1 cache; only unique cache-misses run through the model, in batches.
    """
    texts = ["" if t is None else str(t) for t in texts]
    n = len(texts)
    result = np.zeros((n, EMBED_DIM), dtype=np.float32)
    if n == 0 or not get_settings().use_muril:
        return result
    try:
        cache = load_cache()
        keys = [_key(t) for t in texts]
        uniq: dict[str, int] = {}
        miss_texts: list[str] = []
        for i, k in enumerate(keys):
            if k not in cache and k not in uniq:
                uniq[k] = len(miss_texts)
                miss_texts.append(texts[i])
        if miss_texts:
            bs = max(1, get_settings().muril_batch_size)
            embedded = [
                _embed_batch(miss_texts[s:s + bs]) for s in range(0, len(miss_texts), bs)
            ]
            mat = np.vstack(embedded)
            for k, pos in uniq.items():
                cache[k] = mat[pos]
        for i, k in enumerate(keys):
            result[i] = cache[k]
        return result
    except ImportError:
        log.warning('transformers/torch not installed; MuRIL embeddings are zero. '
                    'Install with: pip install ".[nlp]"')
        return np.zeros((n, EMBED_DIM), dtype=np.float32)
    except Exception as exc:  # noqa: BLE001 - never let embedding crash training/serving
        log.error("MuRIL embedding failed (%s); returning zeros", exc)
        return np.zeros((n, EMBED_DIM), dtype=np.float32)

def precompute(frame: pd.DataFrame) -> dict:
    """Embed all rows' composed text (warming the cache). Returns a summary dict."""
    texts = compose_text(frame)
    unique = len({_key(t) for t in texts})
    embed_texts(texts)
    return {
        "rows": len(texts),
        "unique_texts": unique,
        "cached_vectors": len(load_cache()),
        "device": _device or "n/a",
    }
