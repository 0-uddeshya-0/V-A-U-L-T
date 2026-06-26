"""Extraction engine — anchor-constrained KnowledgeUnit extraction via Instructor."""

from __future__ import annotations

import instructor
from pydantic import BaseModel, Field

from vault.config import settings
from vault.models import (
    DocumentSegment,
    KnowledgeType,
    KnowledgeUnit,
    NormalizedDocument,
    SourcePointer,
)


class ExtractedUnitDraft(BaseModel):
    """LLM output schema — maps to KnowledgeUnit after post-processing."""

    claim: str
    type: KnowledgeType
    domains: list[str]
    applicability: str
    confidence: float = Field(ge=0.0, le=1.0)
    dependencies: list[str] = Field(default_factory=list)
    source_segment_index: int
    source_text_span: str = Field(description="Verbatim quote from source supporting claim")


class ExtractionBatch(BaseModel):
    units: list[ExtractedUnitDraft]


EXTRACTION_SYSTEM = """You are a knowledge distillation engine. Extract atomic knowledge units from the source material.

Rules:
- Each unit is ONE precise, unambiguous claim — not a summary, not a paragraph
- Only extract what is explicitly stated or directly implied in the source
- Include the exact verbatim quote (source_text_span) that supports each claim
- Assign confidence based on how clearly/unambiguously the source states it (NOT whether it's true)
- Prefer fewer, high-quality units over many vague ones
- Types: Fact, Concept, Principle, Pattern, Technique, Tradeoff, Warning, Tool
"""


def _build_extraction_prompt(doc: NormalizedDocument, segments: list[DocumentSegment]) -> str:
    numbered = "\n\n".join(
        f"[Segment {s.index}]"
        + (f" ({s.timestamp_start:.1f}s)" if s.timestamp_start is not None else "")
        + (f" [{s.heading}]" if s.heading else "")
        + f"\n{s.text}"
        for s in segments
    )
    return f"""Source URL: {doc.source_url}
Source type: {doc.source_type.value}

Extract knowledge units from these segments:

{numbered}

Return structured knowledge units with source_segment_index and source_text_span for each."""


async def extract_knowledge_units(doc: NormalizedDocument) -> list[KnowledgeUnit]:
    """Extract knowledge units from a normalized document using Instructor."""
    client = instructor.from_provider(settings.llm_provider)

    # Process in chunks to handle long documents
    chunk_size = 20
    all_units: list[KnowledgeUnit] = []

    for i in range(0, len(doc.segments), chunk_size):
        chunk = doc.segments[i : i + chunk_size]
        batch: ExtractionBatch = client.create(
            response_model=ExtractionBatch,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": _build_extraction_prompt(doc, chunk)},
            ],
            max_retries=2,
        )

        for draft in batch.units:
            seg = _resolve_segment(doc, draft.source_segment_index)
            all_units.append(
                KnowledgeUnit(
                    claim=draft.claim,
                    type=draft.type,
                    domains=draft.domains,
                    applicability=draft.applicability,
                    confidence=draft.confidence,
                    dependencies=draft.dependencies,
                    document_id=doc.id,
                    source=SourcePointer(
                        url=doc.source_url,
                        author=doc.metadata.author,
                        segment_index=draft.source_segment_index,
                        timestamp_start=seg.timestamp_start if seg else None,
                        timestamp_end=seg.timestamp_end if seg else None,
                        section_heading=seg.heading if seg else None,
                        text_span=draft.source_text_span,
                    ),
                )
            )

    return all_units


def _resolve_segment(doc: NormalizedDocument, index: int) -> DocumentSegment | None:
    for seg in doc.segments:
        if seg.index == index:
            return seg
    return doc.segments[index] if 0 <= index < len(doc.segments) else None
