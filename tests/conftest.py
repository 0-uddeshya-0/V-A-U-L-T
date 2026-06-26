"""Shared test fixtures."""

from __future__ import annotations

import pytest

from vault.models import (
    DocumentMetadata,
    DocumentSegment,
    KnowledgeType,
    KnowledgeUnit,
    NormalizedDocument,
    Partition,
    SourcePointer,
    SourceType,
)


@pytest.fixture
def sample_document() -> NormalizedDocument:
    return NormalizedDocument(
        source_type=SourceType.YOUTUBE,
        source_url="https://www.youtube.com/watch?v=test123",
        segments=[
            DocumentSegment(
                index=0,
                text="Rate limiting with token bucket handles burst traffic better than fixed window.",
                start_offset=0,
                end_offset=80,
                timestamp_start=10.0,
                timestamp_end=15.0,
            ),
            DocumentSegment(
                index=1,
                text="Always return 429 with Retry-After header when rate limit is exceeded.",
                start_offset=81,
                end_offset=150,
                timestamp_start=15.0,
                timestamp_end=20.0,
            ),
        ],
        raw_hash="abc123",
        metadata=DocumentMetadata(title="API Rate Limiting", density_score=0.8),
    )


@pytest.fixture
def sample_units(sample_document) -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            claim="Token bucket rate limiting handles burst traffic better than fixed window",
            type=KnowledgeType.PRINCIPLE,
            domains=["api-design", "rate-limiting"],
            applicability="When designing APIs that experience variable traffic patterns",
            confidence=0.92,
            source=SourcePointer(
                url=sample_document.source_url,
                segment_index=0,
                timestamp_start=10.0,
                text_span="Rate limiting with token bucket handles burst traffic",
            ),
            document_id=sample_document.id,
            partition=Partition.VALIDATED,
        ),
        KnowledgeUnit(
            claim="Return HTTP 429 with Retry-After header when rate limit is exceeded",
            type=KnowledgeType.TECHNIQUE,
            domains=["api-design"],
            applicability="When implementing rate limit enforcement in HTTP APIs",
            confidence=0.95,
            source=SourcePointer(
                url=sample_document.source_url,
                segment_index=1,
                timestamp_start=15.0,
                text_span="Always return 429 with Retry-After header",
            ),
            document_id=sample_document.id,
            partition=Partition.VALIDATED,
        ),
    ]


@pytest.fixture
def neo4j_available():
    """Skip test if Neo4j is not reachable."""
    from neo4j.exceptions import ServiceUnavailable

    from vault.graph import KnowledgeGraph

    graph = KnowledgeGraph()
    try:
        graph.ensure_schema()
        return graph
    except ServiceUnavailable:
        graph.close()
        pytest.skip("Neo4j not available — run `docker compose up -d`")
    except Exception as e:
        graph.close()
        pytest.skip(f"Neo4j not available: {e}")
