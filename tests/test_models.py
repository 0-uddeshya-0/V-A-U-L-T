"""Tests for V.A.U.L.T core models and utilities."""

from vault.ingestion import detect_source_type, _split_by_headings
from vault.models import KnowledgeType, KnowledgeUnit, Partition, SourcePointer, SourceType


def test_detect_youtube():
    assert detect_source_type("https://www.youtube.com/watch?v=abc123") == SourceType.YOUTUBE
    assert detect_source_type("https://youtu.be/abc123") == SourceType.YOUTUBE


def test_detect_instagram():
    assert detect_source_type("https://www.instagram.com/reel/abc/") == SourceType.INSTAGRAM


def test_detect_article():
    assert detect_source_type("https://blog.example.com/post") == SourceType.ARTICLE


def test_detect_paper():
    assert detect_source_type("https://arxiv.org/pdf/1234.pdf") == SourceType.PAPER


def test_knowledge_unit_validation():
    unit = KnowledgeUnit(
        claim="Rate limiting should use token bucket for burst tolerance",
        type=KnowledgeType.PRINCIPLE,
        domains=["api-design"],
        applicability="When designing APIs with variable traffic patterns",
        confidence=0.9,
        source=SourcePointer(url="https://example.com", text_span="use token bucket"),
        document_id="doc-1",
    )
    assert unit.partition == Partition.QUARANTINE
    assert unit.type == KnowledgeType.PRINCIPLE


def test_split_by_headings():
    text = "# Introduction\n\nSome intro text.\n\n## Details\n\nMore details."
    segments = _split_by_headings(text)
    assert len(segments) >= 2
    assert any(s.heading == "Introduction" for s in segments)
