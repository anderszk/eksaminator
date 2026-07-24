"""Local embedding via intfloat/multilingual-e5-large. No data leaves the machine."""
import asyncio
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from app.config import settings
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _embed_sync(texts: list[str]) -> list[list[float]]:
    model = get_model()
    # multilingual-e5 requires "query: " or "passage: " prefix
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
    return [e.tolist() for e in embeddings]


async def embed(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(_embed_sync, texts)
