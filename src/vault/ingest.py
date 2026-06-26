"""Unified ingestion entry point — Temporal by default, sync fallback."""

from __future__ import annotations

from vault.models import IngestResponse, SourceType
from vault.pipeline import process_document


async def ingest(
    url: str,
    source_type: SourceType | None = None,
    *,
    sync: bool = False,
    wait: bool = False,
) -> IngestResponse:
    """
    Ingest a URL through the pipeline.

    Default: submit to Temporal workflow (durable, retryable).
    sync=True: run inline (no Temporal required).
    wait=True: block until workflow completes (only with Temporal).
    """
    st = source_type.value if source_type else None

    if sync:
        from vault.ingestion import ingest_url

        doc = await ingest_url(url, source_type)
        await process_document(doc)
        return IngestResponse(
            workflow_id=doc.id,
            document_id=doc.id,
            status="completed",
        )

    from vault.temporal_client import (
        start_ingest_workflow,
        temporal_available,
        wait_for_workflow,
    )

    if not await temporal_available():
        # Graceful fallback when Temporal isn't running
        from vault.ingestion import ingest_url

        doc = await ingest_url(url, source_type)
        await process_document(doc)
        return IngestResponse(
            workflow_id=f"sync-fallback-{doc.id}",
            document_id=doc.id,
            status="completed",
        )

    workflow_id = await start_ingest_workflow(url, st)

    if wait:
        outcome = await wait_for_workflow(workflow_id)
        status = outcome.get("status", "UNKNOWN").lower()
        doc_id = None
        if outcome.get("result"):
            doc_id = outcome["result"].get("document_id")
        return IngestResponse(workflow_id=workflow_id, document_id=doc_id, status=status)

    return IngestResponse(workflow_id=workflow_id, document_id=None, status="running")


async def get_ingest_status(workflow_id: str) -> dict:
    if workflow_id.startswith("sync-fallback-"):
        return {"workflow_id": workflow_id, "status": "COMPLETED", "result": None}
    from vault.temporal_client import get_workflow_status

    return await get_workflow_status(workflow_id)
