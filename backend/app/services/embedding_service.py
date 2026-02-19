"""Local Embedding Service using sentence-transformers.

Provides in-process embedding generation with true batch support.
No network calls, no external API dependencies.
"""
from typing import List
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Singleton model instance
_model = None


def _get_model():
    """Lazy-load the sentence-transformers model (singleton)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _model


def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text string."""
    model = _get_model()
    embedding = model.encode(text, show_progress_bar=False)
    return embedding.tolist()


def generate_embeddings_batch(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """Generate embeddings for multiple texts in a single batch call.

    Uses sentence-transformers native batching for 50-100x speedup
    over sequential calls.

    Args:
        texts: List of text strings to embed.
        batch_size: Internal batch size for the model encoder.

    Returns:
        List of embedding vectors (one per input text).
    """
    if not texts:
        return []

    model = _get_model()
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]
