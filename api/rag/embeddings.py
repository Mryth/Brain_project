"""Sentence embeddings for semantic retrieval (abstracts & questions share one space).
Biomedical model by default; runs on GPU automatically when available."""
import logging
from functools import lru_cache
import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading embedding model {config.EMBED_MODEL} on {device}")
    return SentenceTransformer(config.EMBED_MODEL, device=device)


def embed(texts):
    """texts: str or list[str] -> list[list[float]] (unit-normalized for cosine)."""
    single = isinstance(texts, str)
    arr = _model().encode(
        [texts] if single else list(texts),
        normalize_embeddings=True,          # cosine == dot product
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    out = arr.tolist()
    return out[0] if single else out
