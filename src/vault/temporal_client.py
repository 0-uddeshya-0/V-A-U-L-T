"""Temporal client helpers — start and poll ingestion workflows."""

from __future__ import annotations

import uuid
from datetime import timedelta

from temporalio.client import Client, WorkflowFailureError

from vault.config import settings


async def get_client() -> Client:
    return await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)


async def start_ingest_workflow(url: str, source_type: str | None = None) -> str:
    """Start durable ingestion workflow. Returns workflow ID."""
    from vault.workflows import IngestSourceWorkflow

    client = await get_client()
    workflow_id = f"vault-ingest-{uuid.uuid4().hex[:12]}"
    await client.start_workflow(
        IngestSourceWorkflow.run,
        args=[url, source_type],
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return workflow_id


async def get_workflow_status(workflow_id: str) -> dict:
    """Return workflow status and result if completed."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()

    status = desc.status.name if desc.status else "UNKNOWN"
    result = None
    error = None

    if status == "COMPLETED":
        try:
            result = await handle.result()
        except WorkflowFailureError as e:
            error = str(e)
    elif status == "FAILED":
        error = "Workflow failed — check Temporal UI at http://localhost:8080"

    return {
        "workflow_id": workflow_id,
        "status": status,
        "result": result,
        "error": error,
    }


async def wait_for_workflow(workflow_id: str, timeout_seconds: int = 3600) -> dict:
    """Block until workflow completes or times out."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        result = await handle.result(timeout=timedelta(seconds=timeout_seconds))
        return {"workflow_id": workflow_id, "status": "COMPLETED", "result": result}
    except Exception as e:
        return {"workflow_id": workflow_id, "status": "FAILED", "error": str(e)}


async def temporal_available() -> bool:
    """Check if Temporal server is reachable."""
    try:
        await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        return True
    except Exception:
        return False
