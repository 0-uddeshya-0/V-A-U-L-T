"""Delivery layer — MCP server and REST API for agent consumption."""

from __future__ import annotations

import json

from vault.graph import KnowledgeGraph
from vault.ingest import get_ingest_status, ingest
from vault.models import IngestRequest, IngestResponse, QueryResult


def create_mcp_server():
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    server = Server("vault-knowledge-os")
    graph = KnowledgeGraph()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="query_knowledge",
                description="Query validated knowledge units for a task. Returns structured claims with provenance.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "domains": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["task"],
                },
            ),
            Tool(
                name="get_unit",
                description="Get a knowledge unit by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"unit_id": {"type": "string"}},
                    "required": ["unit_id"],
                },
            ),
            Tool(
                name="list_contradictions",
                description="List unresolved contradictions.",
                inputSchema={"type": "object", "properties": {"concept": {"type": "string"}}},
            ),
            Tool(
                name="list_gaps",
                description="Concepts referenced but under-specified.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="ingest_url",
                description="Ingest content from URL.",
                inputSchema={
                    "type": "object",
                    "properties": {"url": {"type": "string"}, "wait": {"type": "boolean"}},
                    "required": ["url"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "query_knowledge":
            results = graph.query(
                task=arguments["task"],
                domains=arguments.get("domains"),
                limit=arguments.get("limit", 10),
            )
            return [TextContent(type="text", text=_format_query_results(results))]

        if name == "get_unit":
            unit = graph.get_unit(arguments["unit_id"])
            return [TextContent(type="text", text=json.dumps(unit, indent=2, default=str))]

        if name == "list_contradictions":
            return [TextContent(type="text", text=json.dumps(graph.list_contradictions(arguments.get("concept")), indent=2))]

        if name == "list_gaps":
            return [TextContent(type="text", text=json.dumps(graph.list_gaps(), indent=2))]

        if name == "ingest_url":
            response = await ingest(arguments["url"], wait=arguments.get("wait", False))
            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server, stdio_server, graph


def _format_query_results(results: list[QueryResult]) -> str:
    payload = [
        {
            "unit_id": r.unit_id,
            "claim": r.claim,
            "type": r.type.value if hasattr(r.type, "value") else r.type,
            "applicability": r.applicability,
            "confidence": r.confidence,
            "source": {"url": r.source.url, "timestamp_or_section": r.source.text_span or r.source.timestamp_start},
            "related": r.related,
            "relevance_score": r.relevance_score,
        }
        for r in results
    ]
    return json.dumps(payload, indent=2)


async def main():
    server, stdio_server, graph = create_mcp_server()
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        graph.close()


def create_rest_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from vault.config import settings
    from vault.delivery.quarantine_ui import register_quarantine_routes

    app = FastAPI(title="V.A.U.L.T Knowledge OS", version="0.1.0")

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def graph_factory():
        return KnowledgeGraph()

    register_quarantine_routes(app, graph_factory)

    @app.post("/query")
    async def query(body: dict):
        graph = graph_factory()
        try:
            results = graph.query(task=body["task"], domains=body.get("domains"), limit=body.get("limit", 10))
            return [_query_to_dict(r) for r in results]
        finally:
            graph.close()

    @app.post("/ingest")
    async def ingest_endpoint(body: IngestRequest, sync: bool = False, wait: bool = False) -> IngestResponse:
        return await ingest(body.url, body.source_type, sync=sync, wait=wait)

    @app.get("/ingest/{workflow_id}")
    async def ingest_status(workflow_id: str):
        return await get_ingest_status(workflow_id)

    @app.get("/units/{unit_id}")
    async def get_unit_endpoint(unit_id: str):
        graph = graph_factory()
        try:
            unit = graph.get_unit(unit_id)
            if not unit:
                raise HTTPException(status_code=404, detail="Unit not found")
            unit.pop("embedding", None)
            return unit
        finally:
            graph.close()

    @app.get("/gaps")
    async def gaps():
        graph = graph_factory()
        try:
            return graph.list_gaps()
        finally:
            graph.close()

    @app.get("/health")
    async def health():
        neo4j = "ok"
        try:
            g = graph_factory()
            with g._driver.session() as session:
                session.run("RETURN 1")
            g.close()
        except Exception:
            neo4j = "unavailable"
        return {"status": "ok", "service": "vault-knowledge-os", "neo4j": neo4j}

    return app


def _query_to_dict(r: QueryResult) -> dict:
    return {
        "unit_id": r.unit_id,
        "claim": r.claim,
        "type": r.type.value if hasattr(r.type, "value") else r.type,
        "applicability": r.applicability,
        "confidence": r.confidence,
        "source": {"url": r.source.url, "timestamp_or_section": r.source.text_span or r.source.timestamp_start},
        "related": r.related,
        "relevance_score": r.relevance_score,
    }


def rest_main():
    import uvicorn

    uvicorn.run(create_rest_app(), host="0.0.0.0", port=8400)
