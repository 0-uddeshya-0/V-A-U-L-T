"""Core domain models for the Knowledge OS."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    ARTICLE = "article"
    PAPER = "paper"


class KnowledgeType(str, Enum):
    FACT = "Fact"
    CONCEPT = "Concept"
    PRINCIPLE = "Principle"
    PATTERN = "Pattern"
    TECHNIQUE = "Technique"
    TRADEOFF = "Tradeoff"
    WARNING = "Warning"
    TOOL = "Tool"


class EdgeType(str, Enum):
    EXTENDS = "extends"
    CONTRADICTS = "contradicts"
    REQUIRES = "requires"
    IMPLEMENTS = "implements"
    SUPERSEDES = "supersedes"
    IS_EXAMPLE_OF = "is_example_of"
    CO_OCCURS = "co_occurs"


class Partition(str, Enum):
    VALIDATED = "validated"
    QUARANTINE = "quarantine"


class SourcePointer(BaseModel):
    """Exact attribution back to source material."""

    url: str
    author: str | None = None
    segment_index: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    section_heading: str | None = None
    text_span: str | None = Field(
        default=None, description="Verbatim quote from source supporting the claim"
    )


class DocumentSegment(BaseModel):
    """A slice of normalized content with structural/temporal markers."""

    index: int
    text: str
    start_offset: int
    end_offset: int
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    heading: str | None = None
    section_type: str | None = Field(
        default=None, description="e.g. abstract, methods, conclusion for papers"
    )


class DocumentMetadata(BaseModel):
    author: str | None = None
    title: str | None = None
    published_at: datetime | None = None
    domain: str | None = Field(default=None, description="Inferred topical domain")
    density_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Information density signal"
    )


class NormalizedDocument(BaseModel):
    """Common intermediate format — all sources normalize to this."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: SourceType
    source_url: str
    segments: list[DocumentSegment]
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    raw_hash: str = Field(description="SHA-256 of raw content for deduplication")
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def full_text(self) -> str:
        return "\n\n".join(s.text for s in self.segments)


class KnowledgeUnit(BaseModel):
    """Atomic, structured claim — the core unit of the knowledge graph."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    claim: str = Field(description="One precise, unambiguous statement")
    type: KnowledgeType
    domains: list[str] = Field(min_length=1)
    applicability: str = Field(description="When this knowledge is relevant")
    source: SourcePointer
    confidence: float = Field(ge=0.0, le=1.0, description="How clearly stated in source")
    dependencies: list[str] = Field(
        default_factory=list, description="Concept or unit IDs required first"
    )
    partition: Partition = Partition.QUARANTINE
    document_id: str
    validation_failures: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("claim")
    @classmethod
    def claim_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("claim must not be empty")
        return v


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    unit_id: str
    passed: bool
    checks: dict[str, bool] = Field(
        default_factory=dict,
        description="grounding, consistency, comprehension",
    )
    scores: dict[str, float] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    questions_failed: list[str] = Field(default_factory=list)


class ComprehensionQuestion(BaseModel):
    level: Literal["recall", "application", "analysis"]
    question: str
    expected_answer: str


class QueryResult(BaseModel):
    """Structured payload delivered to agents."""

    claim: str
    type: KnowledgeType
    applicability: str
    confidence: float
    source: SourcePointer
    unit_id: str
    related: list[dict] = Field(
        default_factory=list,
        description="[{unit_id, relationship_type}]",
    )
    relevance_score: float = 0.0


class IngestRequest(BaseModel):
    url: str
    source_type: SourceType | None = None


class IngestResponse(BaseModel):
    workflow_id: str
    document_id: str | None = None
    status: str
