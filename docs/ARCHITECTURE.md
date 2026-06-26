# V.A.U.L.T Architecture

> Versatile Archive of Unified Learning & Thought — the Knowledge OS

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DELIVERY LAYER                                  │
│   MCP Server (query_knowledge)          REST API (POST /query)              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ graph traversal + vector rerank
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                         LIVING KNOWLEDGE GRAPH                               │
│   Neo4j / FalkorDB — KnowledgeUnit nodes, Concept nodes, typed edges        │
│   Partitions: validated | quarantine                                          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                          VALIDATION LAYER                                      │
│   1. Source Grounding (groundguard / LongTracer)                              │
│   2. Internal Consistency (graph contradiction scan)                          │
│   3. Comprehension Verification (self-QA, Microsoft SV pattern)             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                          EXTRACTION ENGINE                                     │
│   Instructor + Pydantic — atomic KnowledgeUnits with provenance anchors       │
│   Inspired by: TACITUS (EVD→CTX), AEVS (anchor-constrained extraction)      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                          INGESTION LAYER                                       │
│   NormalizedDocument — common format regardless of source type                │
│   YouTube | Instagram | Articles | Papers                                     │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                     TEMPORAL ORCHESTRATION                                     │
│   IngestWorkflow → ExtractWorkflow → ValidateWorkflow → IntegrateWorkflow   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Design Principles (from product brief)

| Principle | Implementation |
|-----------|----------------|
| Precision over recall | Validation gate before graph; quarantine partition |
| Every claim attributable | `SourcePointer` with URL + span/timestamp on every unit |
| Human in the loop for uncertainty | Quarantine queue + contradiction surfacing |
| Agent-native | MCP-first delivery; structured JSON payload |
| Zero configuration | URL in → knowledge out; only quarantine needs human touch |

## Component Mapping

### 1. Ingestion Layer

All sources normalize to `NormalizedDocument`:

```python
NormalizedDocument:
  id, source_type, source_url
  segments: [{text, start_offset, end_offset, timestamp?, heading?, section_type?}]
  metadata: {author, published_at, domain, density_score}
  raw_hash  # dedup key
```

| Source | Primary Tool | Fallback | Notes |
|--------|-------------|----------|-------|
| YouTube | `yt-dlp` subtitles | `youtube-transcript-api` | Timestamps preserved in segments |
| Instagram Reels | `yt-dlp` + Whisper | `instaloader` captions | Cookie auth via `--cookies-from-browser` |
| Articles | `trafilatura` | Jina Reader (`r.jina.ai`) | Strip nav/ads; extract metadata |
| Papers (PDF) | `MinerU` / `markitdown` | `GROBID` | Section-aware: abstract/methods/conclusion |
| Any URL | **Agent-Reach** CLI | — | Meta-router; bundles yt-dlp, trafilatura patterns |

**Agent-Reach** ([Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)) is recommended as an optional ingestion accelerator — it pre-configures YouTube, web reading, and URL routing. V.A.U.L.T wraps it behind adapters rather than depending on it directly, so the pipeline stays self-contained.

### 2. Extraction Engine

Pattern: **Anchor-Constrained Extraction** (AEVS framework)

1. **Anchor discovery** — identify claim-worthy spans in source segments
2. **Grounded extraction** — LLM extracts only from anchored spans via Instructor
3. **Schema validation** — Pydantic enforces KnowledgeUnit structure

Tools:
- [567-labs/instructor](https://github.com/567-labs/instructor) — structured LLM output with retries
- [IBM/kep](https://github.com/IBM/kep) — reference pipeline for classify→extract
- [sargonxg/TACITUS-Knowledge-Pipeline-open](https://github.com/sargonxg/TACITUS-Knowledge-Pipeline-open) — EVD→CTX→GND provenance model

Knowledge unit types: `Fact | Concept | Principle | Pattern | Technique | Tradeoff | Warning | Tool`

### 3. Validation Layer

Three independent checks, implemented as Temporal activities:

| Check | Tool / Pattern | Pass Criteria |
|-------|---------------|---------------|
| Source Grounding | [pulkitj/groundguard](https://github.com/pulkitj/groundguard) | Every claim supported by source span |
| Internal Consistency | Graph query (Neo4j) | No unflagged `contradicts` edges with existing validated units |
| Comprehension Verification | Self-QA (Microsoft SV pattern) | Unit alone answers recall + application + analysis questions |

Additional grounding tools for tiered verification:
- [ENDEVSOLS/LongTracer](https://github.com/ENDEVSOLS/LongTracer) — STS + NLI hybrid
- [Vbj1808/Dokis](https://github.com/Vbj1808/Dokis) — zero-LLM BM25 provenance (fast first pass)
- [zhjai/groundcheck](https://github.com/zhjai/groundcheck) — pluggable fact-gate for agent pipelines

Failed units → `quarantine` partition. Passed units → `validated` partition.

### 4. Living Knowledge Graph

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Graph DB | **Neo4j 5** (primary) | Mature Cypher, vector index, KAG-style provenance chains |
| Dev/lightweight | **FalkorDB** or Ladybug (Kuzu fork) | Embedded, fast multi-hop for local dev |
| Embeddings | `sentence-transformers` (local) | No API dependency; hybrid retrieval |

Edge types: `extends | contradicts | requires | implements | supersedes | is_example_of | co_occurs`

Graph integration on new unit:
1. Resolve/create Concept nodes from unit domains + dependencies
2. Create edges to referenced concepts and prior units
3. Scan for potential contradictions (same concept, incompatible claims)
4. Update concept weight; detect gap nodes (referenced but no units)

Reference implementations:
- [leakydata/claude-graphrag-mcp](https://github.com/leakydata/claude-graphrag-mcp) — KAG mutual indexing (Chunk↔Entity provenance)
- [andrewbergsma/knowledge-mcp](https://github.com/andrewbergsma/knowledge-mcp) — 9 relationship types, hybrid FTS+vector

### 5. Delivery Layer

**MCP Server** tools:
- `query_knowledge(task: str, domains?: str[], limit?: int)` — graph traversal + rerank
- `get_unit(id: str)` — single unit with full provenance
- `list_contradictions(concept?: str)` — unresolved conflicts
- `list_gaps()` — concepts referenced but under-specified
- `ingest_url(url: str)` — trigger pipeline (returns workflow ID)

**REST API** mirrors MCP via FastAPI.

Query strategy (not pure vector search):
1. Embed task description → vector similarity on unit claims
2. Expand via graph: follow `requires`, `extends`, `contradicts` edges
3. Filter by applicability text match
4. Return ranked payload with related units and relationship types

## Orchestration: Temporal

The full pipeline is a Temporal workflow — durable, retryable, observable:

```
IngestSourceWorkflow
  ├─ Activity: detect_source_type
  ├─ Activity: fetch_and_normalize     (ingestion adapters)
  ├─ ChildWorkflow: ProcessDocumentWorkflow
  │    ├─ Activity: extract_units      (Instructor, chunked)
  │    ├─ Activity: validate_grounding (groundguard)
  │    ├─ Activity: validate_comprehension (self-QA)
  │    ├─ Activity: check_consistency  (graph scan)
  │    └─ Activity: integrate_graph    (Neo4j upsert)
  └─ Signal: quarantine_review         (human approve/reject)
```

Why Temporal over Celery/Arq:
- Long-running ingestion (40-min video transcription) survives restarts
- Per-activity retry policies (LLM rate limits, yt-dlp failures)
- Workflow history = audit trail for every knowledge unit's journey
- Signals for human quarantine review without polling

## Data Flow Example

```
Input: https://youtube.com/watch?v=abc123
  → Ingest: NormalizedDocument with 847 timestamped segments
  → Extract: 23 KnowledgeUnits (12 Principle, 6 Tradeoff, 5 Technique)
  → Validate: 19 pass, 4 quarantined (2 failed grounding, 2 failed comprehension)
  → Graph: 19 units linked to 8 Concept nodes, 3 new edges to existing "rate-limiting" cluster
  → Delivery: Cursor agent queries "designing API rate limits" → receives 7 ranked units with contradictions flagged
```

## What V.A.U.L.T Is Not

- Not a chatbot, search engine, note-taking app, LMS, or fine-tuning pipeline
- Not Mem0/Zep (conversation memory) — stores **learned content from external sources**
- Not standard RAG — delivers **structured claims**, not raw chunks

## Phase Plan

| Phase | Scope | Exit Criteria |
|-------|-------|---------------|
| **P0** | Ingest YouTube + articles; extract; validate grounding; Neo4j store; MCP query | One URL → queryable units in Cursor |
| **P1** | Instagram + PDF papers; comprehension check; contradiction detection; quarantine UI | Full validation partition works |
| **P2** | Gap detection; concept clustering; REST API; Temporal Cloud | Graph reveals learning gaps |
| **P3** | Agent-Reach integration; batch ingestion; confidence re-evaluation | Zero-config multi-source |
