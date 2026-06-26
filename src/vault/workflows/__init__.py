"""Temporal workflow orchestration for durable pipeline execution."""

from __future__ import annotations

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from vault.config import settings
    from vault.ingestion import ingest_url
    from vault.models import NormalizedDocument
    from vault.pipeline import process_document


@activity.defn
async def ingest_activity(url: str, source_type: str | None = None) -> dict:
    from vault.models import SourceType

    st = SourceType(source_type) if source_type else None
    doc = await ingest_url(url, st)
    return doc.model_dump(mode="json")


@activity.defn
async def process_activity(doc_dict: dict) -> dict:
    doc = NormalizedDocument.model_validate(doc_dict)
    return await process_document(doc)


@workflow.defn
class IngestSourceWorkflow:
    """Durable workflow: ingest → extract → validate → integrate."""

    @workflow.run
    async def run(self, url: str, source_type: str | None = None) -> dict:
        retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            maximum_attempts=3,
        )

        doc_dict = await workflow.execute_activity(
            ingest_activity,
            args=[url, source_type],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=retry,
        )

        result = await workflow.execute_activity(
            process_activity,
            args=[doc_dict],
            start_to_close_timeout=timedelta(minutes=60),
            retry_policy=retry,
        )

        return {
            "url": url,
            "document_id": doc_dict.get("id"),
            **result,
        }


async def run_worker():
    from temporalio.client import Client
    from temporalio.worker import Worker

    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[IngestSourceWorkflow],
        activities=[ingest_activity, process_activity],
    )
    await worker.run()


def main():
    import asyncio

    asyncio.run(run_worker())
