"""End-to-end pipeline tests with mocked LLM calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from vault.models import Partition
from vault.pipeline import process_document


@pytest.mark.asyncio
async def test_pipeline_with_mocked_extraction(sample_document, sample_units):
    async def mock_validate(unit, doc, existing_claims=None):
        from vault.models import ValidationResult

        result = ValidationResult(unit_id=unit.id, passed=True)
        result.checks = {"grounding": True, "consistency": True, "comprehension": True}
        unit.partition = Partition.VALIDATED
        return result

    with (
        patch("vault.pipeline.extract_knowledge_units", return_value=sample_units),
        patch("vault.pipeline.validate_unit", side_effect=mock_validate),
        patch("vault.pipeline.KnowledgeGraph") as MockGraph,
    ):
        mock_graph = MockGraph.return_value
        mock_graph.ensure_schema = lambda: None
        mock_graph.close = lambda: None
        mock_graph._driver.session.return_value.__enter__ = lambda s: s
        mock_graph._driver.session.return_value.__exit__ = lambda *a: None
        mock_graph._driver.session.return_value.run.return_value = iter([])

        with patch("vault.pipeline.integrate_unit") as mock_integrate:
            result = await process_document(sample_document)

    assert result["total_units"] == 2
    assert result["validated"] == 2
    assert result["quarantined"] == 0
    assert mock_integrate.call_count == 2


@pytest.mark.asyncio
async def test_pipeline_quarantine_on_validation_failure(sample_document, sample_units):
    async def mock_validate(unit, doc, existing_claims=None):
        from vault.models import ValidationResult

        passed = unit.id == sample_units[0].id
        result = ValidationResult(
            unit_id=unit.id,
            passed=passed,
            failures=[] if passed else ["Source grounding failed"],
        )
        result.checks = {"grounding": passed, "consistency": True, "comprehension": passed}
        unit.partition = Partition.VALIDATED if passed else Partition.QUARANTINE
        return result

    with (
        patch("vault.pipeline.extract_knowledge_units", return_value=sample_units),
        patch("vault.pipeline.validate_unit", side_effect=mock_validate),
        patch("vault.pipeline.KnowledgeGraph") as MockGraph,
    ):
        mock_graph = MockGraph.return_value
        mock_graph.ensure_schema = lambda: None
        mock_graph.close = lambda: None
        mock_graph._driver.session.return_value.__enter__ = lambda s: s
        mock_graph._driver.session.return_value.__exit__ = lambda *a: None
        mock_graph._driver.session.return_value.run.return_value = iter([])
        mock_graph.upsert_unit = lambda u: None

        with patch("vault.pipeline.integrate_unit"):
            result = await process_document(sample_document)

    assert result["validated"] == 1
    assert result["quarantined"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_youtube_ingestion_real_transcript():
    """Fetch a real YouTube transcript (no LLM, no Neo4j)."""
    from youtube_transcript_api._errors import VideoUnavailable

    from vault.ingestion import ingest_url

    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" — first YT video
    try:
        doc = await ingest_url(url)
    except (VideoUnavailable, ValueError) as e:
        pytest.skip(f"YouTube transcript unavailable: {e}")

    assert doc.source_type.value == "youtube"
    assert len(doc.segments) > 0
    assert doc.full_text


@pytest.mark.asyncio
async def test_ingest_sync_fallback():
    """Ingest module falls back to sync when Temporal unavailable."""
    from vault.ingest import ingest

    with (
        patch("vault.temporal_client.temporal_available", new_callable=AsyncMock, return_value=False),
        patch("vault.ingestion.ingest_url", new_callable=AsyncMock) as mock_ingest,
        patch("vault.ingest.process_document", new_callable=AsyncMock) as mock_process,
    ):
        from vault.models import NormalizedDocument, SourceType

        mock_ingest.return_value = NormalizedDocument(
            source_type=SourceType.ARTICLE,
            source_url="https://example.com",
            segments=[],
            raw_hash="x",
        )
        mock_process.return_value = {"validated": 0}

        response = await ingest("https://example.com")
        assert response.status == "completed"
        assert response.workflow_id.startswith("sync-fallback-")
