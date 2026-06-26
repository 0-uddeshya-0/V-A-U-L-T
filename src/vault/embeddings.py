"""Local embedding generation for hybrid graph retrieval."""

from __future__ import annotations

from functools import lru_cache

from vault.config import settings

EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed_passage(text: str) -> list[float]:
    """Embed document/unit text for storage."""
    return _model().encode(text, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query (BGE query prefix)."""
    prefixed = f"Represent this sentence for searching relevant passages: {text}"
    return _model().encode(prefixed, normalize_embeddings=True).tolist()


def unit_embedding_text(claim: str, applicability: str, domains: list[str]) -> str:
    """Combined text for embedding a knowledge unit."""
    domain_str = ", ".join(domains)
    return f"{claim}\nApplicability: {applicability}\nDomains: {domain_str}"
