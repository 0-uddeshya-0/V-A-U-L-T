"""V.A.U.L.T CLI."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="vault",
        description="V.A.U.L.T — Versatile Archive of Unified Learning & Thought",
    )
    sub = parser.add_subparsers(dest="command")

    ingest_p = sub.add_parser("ingest", help="Ingest a URL (Temporal by default)")
    ingest_p.add_argument("url", help="Source URL (YouTube, article, Instagram, PDF)")
    ingest_p.add_argument("--type", choices=["youtube", "instagram", "article", "paper"])
    ingest_p.add_argument("--sync", action="store_true", help="Run inline without Temporal")
    ingest_p.add_argument("--wait", action="store_true", help="Wait for workflow to complete")

    sub.add_parser("gaps", help="List learning gaps in the knowledge graph")
    sub.add_parser("quarantine", help="Print quarantine review URL")
    sub.add_parser("serve-mcp", help="Start MCP server (stdio)")
    sub.add_parser("serve-api", help="Start REST API + quarantine UI on :8400")

    query_p = sub.add_parser("query", help="Query knowledge for a task")
    query_p.add_argument("task", help="Task description")
    query_p.add_argument("--limit", type=int, default=10)

    status_p = sub.add_parser("status", help="Check ingestion workflow status")
    status_p.add_argument("workflow_id", help="Temporal workflow ID")

    args = parser.parse_args()

    if args.command == "ingest":
        asyncio.run(_ingest(args.url, args.type, args.sync, args.wait))
    elif args.command == "status":
        asyncio.run(_status(args.workflow_id))
    elif args.command == "gaps":
        _gaps()
    elif args.command == "quarantine":
        print("Quarantine review UI: http://localhost:8400/quarantine")
        print("Start the API first: vault serve-api")
    elif args.command == "query":
        _query(args.task, args.limit)
    elif args.command == "serve-mcp":
        asyncio.run(_serve_mcp())
    elif args.command == "serve-api":
        _serve_api()
    else:
        parser.print_help()
        sys.exit(1)


async def _ingest(url: str, source_type: str | None, sync: bool, wait: bool):
    from vault.ingest import ingest
    from vault.models import SourceType

    st = SourceType(source_type) if source_type else None
    print(f"Ingesting: {url} ({'sync' if sync else 'temporal'})")
    response = await ingest(url, st, sync=sync, wait=wait)
    print(json.dumps(response.model_dump(), indent=2))
    if response.status == "running":
        print(f"\nTrack progress: vault status {response.workflow_id}")


async def _status(workflow_id: str):
    from vault.ingest import get_ingest_status

    result = await get_ingest_status(workflow_id)
    print(json.dumps(result, indent=2, default=str))


def _gaps():
    from vault.graph import KnowledgeGraph

    graph = KnowledgeGraph()
    gaps = graph.list_gaps()
    graph.close()
    print(json.dumps(gaps, indent=2))


def _query(task: str, limit: int):
    from vault.delivery import _format_query_results
    from vault.graph import KnowledgeGraph

    graph = KnowledgeGraph()
    results = graph.query(task, limit=limit)
    graph.close()
    print(_format_query_results(results))


async def _serve_mcp():
    from vault.delivery import main as mcp_main

    await mcp_main()


def _serve_api():
    from vault.delivery import rest_main

    rest_main()
