# V.A.U.L.T Toolstack Research

Curated GitHub tools evaluated for each pipeline component. Stars and maintenance status as of June 2026.

## Tier 1 — Adopt Directly

| Tool | Repo | Role in V.A.U.L.T |
|------|------|-------------------|
| **Instructor** | [567-labs/instructor](https://github.com/567-labs/instructor) | Structured KnowledgeUnit extraction via Pydantic |
| **Trafilatura** | [adbar/trafilatura](https://github.com/adbar/trafilatura) | Article/blog normalization |
| **yt-dlp** | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube + Instagram media download |
| **groundguard** | [pulkitj/groundguard](https://github.com/pulkitj/groundguard) | Source grounding validation (Check 1) |
| **Temporal SDK** | [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | Durable pipeline orchestration |
| **MCP Python SDK** | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | Agent delivery layer |
| **Neo4j** | [neo4j/neo4j-python-driver](https://github.com/neo4j/neo4j-python-driver) | Knowledge graph storage |
| **FastAPI** | [fastapi/fastapi](https://github.com/tiago2/fastapi) | REST delivery API |

## Tier 2 — Integrate / Wrap

| Tool | Repo | Role in V.A.U.L.T |
|------|------|-------------------|
| **Agent-Reach** | [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | Optional meta-ingestion router (YouTube, web, multi-platform) |
| **LongTracer** | [ENDEVSOLS/LongTracer](https://github.com/ENDEVSOLS/LongTracer) | STS+NLI claim verification (grounding tier 2) |
| **Dokis** | [Vbj1808/Dokis](https://github.com/Vbj1808/Dokis) | Fast BM25 provenance check (grounding tier 0, no LLM) |
| **MarkItDown** | [microsoft/markitdown](https://github.com/microsoft/markitdown) | PDF/office → markdown for papers |
| **MinerU** | [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | Academic PDF structure extraction |
| **Whisper** | [openai/whisper](https://github.com/openai/whisper) | Instagram/video audio transcription |
| **sentence-transformers** | [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers) | Local embeddings for hybrid retrieval |

## Tier 3 — Reference Architecture / Patterns

| Tool | Repo | What to Borrow |
|------|------|----------------|
| **TACITUS Pipeline** | [sargonxg/TACITUS-Knowledge-Pipeline-open](https://github.com/sargonxg/TACITUS-Knowledge-Pipeline-open) | EVD→CTX→GND provenance layers; OntoRAG theory seeding |
| **claude-graphrag-mcp** | [leakydata/claude-graphrag-mcp](https://github.com/leakydata/claude-graphrag-mcp) | KAG mutual indexing; Chunk↔Entity provenance chain |
| **knowledge-mcp** | [andrewbergsma/knowledge-mcp](https://github.com/andrewbergsma/knowledge-mcp) | 12 entity types, 9 relationship types, hybrid FTS+vector |
| **Artifactor** | [agenisea/artifactor](https://github.com/agenisea/artifactor) | Dual-path validation (deterministic + LLM cross-validation) |
| **IBM KEP** | [IBM/kep](https://github.com/IBM/kep) | Classify→extract pipeline; schema-driven few-shot |
| **GroundCheck** | [zhjai/groundcheck](https://github.com/zhjai/groundcheck) | Pluggable fact-gate contract for multi-agent systems |
| **HalluciGuard** | [Hermes-Lekkas/HalluciGuard](https://github.com/Hermes-Lekkas/HalluciGuard) | Claim extraction + confidence scoring + audit logs |

## Tier 4 — Instagram-Specific

| Tool | Repo | Notes |
|------|------|-------|
| **insta-transcribe** | [AmitabhMorey/insta-transcribe](https://github.com/AmitabhMorey/insta-transcribe) | yt-dlp + Whisper pattern we replicate |
| **instagram-reel-extractor** | [JayceBatallones/instagram-reel-extractor](https://github.com/JayceBatallones/instagram-reel-extractor) | Rich metadata + frames; good reference for segment structure |
| **ig2insights** | [devbush/ig2insights](https://github.com/devbush/ig2insights) | Go CLI with whisper.cpp; local-only option |

## Explicitly Not Using (and why)

| Tool | Why Not |
|------|---------|
| **Mem0 / Zep** | Conversation memory, not external-source knowledge extraction |
| **Standard RAG (knowledge-rag, etc.)** | Chunk retrieval, not structured claim delivery — useful only for embedding layer patterns |
| **Kuzu (archived)** | Apple acquired Oct 2025; use Neo4j or Ladybug fork instead |
| **Unstructured.io (enterprise)** | Heavy; trafilatura + markitdown sufficient for personal scale |

## Validation Stack (Three Checks)

```
Check 1 — Source Grounding
  Tier 0: Dokis (BM25, no LLM, ~60% of claims)
  Tier 1: groundguard (lexical + constrained LLM)
  Tier 2: LongTracer (STS + NLI entailment)

Check 2 — Internal Consistency
  Neo4j Cypher: MATCH contradictions on same Concept
  Human signal via Temporal workflow

Check 3 — Comprehension Verification
  Pattern: Microsoft Self-Verification (arxiv 2306.00024)
  Generate recall/application/analysis questions
  Answer from unit only → fail if lossy
```

## Graph Database Decision

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Neo4j 5** | Vector index, Cypher, KAG patterns, MCP examples | Server overhead | **Production choice** |
| **FalkorDB** | Redis-based, fast, GraphRAG SDK | Smaller ecosystem | Dev/alternative |
| **Ladybug** (Kuzu fork) | Embedded, 400x faster multi-hop | No corporate backing post-Kuzu archive | Analytics-only fallback |
| **SQLite + NetworkX** | Zero deps | No concurrent access, no vector index | P0 local dev only |

## Agent-Reach Integration Strategy

Agent-Reach is **not** a dependency — it's an optional ingestion accelerator:

```
vault ingest https://youtube.com/...     → native yt-dlp adapter
vault ingest --via-agent-reach <url>     → delegates to Agent-Reach CLI
```

Use Agent-Reach when:
- Source type is ambiguous (Agent-Reach auto-routes)
- Platform requires cookie auth Agent-Reach already configured
- You want Reddit/Twitter/Bilibili without building adapters

Build native adapters when:
- You need timestamp-precise segments (Agent-Reach returns flat text)
- Validation requires segment-level provenance pointers
- Pipeline must be self-contained (no external CLI dependency)
