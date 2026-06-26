"""Validation layer — three independent checks before graph integration."""

from __future__ import annotations

import instructor
from pydantic import BaseModel, Field

from vault.config import settings
from vault.models import (
    ComprehensionQuestion,
    KnowledgeUnit,
    NormalizedDocument,
    Partition,
    ValidationResult,
)


class QuestionSet(BaseModel):
    questions: list[ComprehensionQuestion]


class AnswerEvaluation(BaseModel):
    question: str
    answer_from_unit: str
    sufficient: bool
    reason: str


class ComprehensionResult(BaseModel):
    evaluations: list[AnswerEvaluation]
    passed: bool


async def validate_unit(
    unit: KnowledgeUnit,
    doc: NormalizedDocument,
    existing_claims: list[str] | None = None,
) -> ValidationResult:
    """Run all three validation checks on a knowledge unit."""
    result = ValidationResult(unit_id=unit.id, passed=False)

    grounding_ok, grounding_score = await check_source_grounding(unit, doc)
    result.checks["grounding"] = grounding_ok
    result.scores["grounding"] = grounding_score

    consistency_ok = check_internal_consistency(unit, existing_claims or [])
    result.checks["consistency"] = consistency_ok

    comprehension_ok, failed_qs = await check_comprehension(unit)
    result.checks["comprehension"] = comprehension_ok
    result.questions_failed = failed_qs

    if not grounding_ok:
        result.failures.append("Source grounding failed — claim not supported by source span")
    if not consistency_ok:
        result.failures.append("Internal consistency failed — contradicts existing validated unit")
    if not comprehension_ok:
        result.failures.append("Comprehension verification failed — unit is lossy or underspecified")

    result.passed = all(result.checks.values())
    unit.partition = Partition.VALIDATED if result.passed else Partition.QUARANTINE
    return result


async def check_source_grounding(
    unit: KnowledgeUnit, doc: NormalizedDocument
) -> tuple[bool, float]:
    """
    Check 1: Source Grounding
    Uses constrained LLM verification (groundguard pattern) when groundguard not installed.
    """
    source_text = doc.full_text
    span = unit.source.text_span or ""

    if span and span.lower() in source_text.lower():
        return True, 1.0

    try:
        from groundguard import verify  # type: ignore

        result = verify(claim=unit.claim, sources=[source_text])
        score = result.compliance_rate if hasattr(result, "compliance_rate") else 0.0
        return score >= settings.grounding_min_score, score
    except ImportError:
        return await _llm_grounding_check(unit, source_text)


async def _llm_grounding_check(unit: KnowledgeUnit, source_text: str) -> tuple[bool, float]:
    """Fallback grounding via constrained LLM verification."""

    class GroundingVerdict(BaseModel):
        supported: bool
        score: float = Field(ge=0.0, le=1.0)
        evidence_span: str | None = None

    client = instructor.from_provider(settings.llm_provider)
    verdict: GroundingVerdict = client.create(
        response_model=GroundingVerdict,
        messages=[
            {
                "role": "system",
                "content": (
                    "Verify whether the claim is supported by the source text ONLY. "
                    "Do not use external knowledge. If unsupported, score low."
                ),
            },
            {
                "role": "user",
                "content": f"Claim: {unit.claim}\n\nSource text:\n{source_text[:8000]}",
            },
        ],
        max_retries=1,
    )
    if verdict.evidence_span and not unit.source.text_span:
        unit.source.text_span = verdict.evidence_span
    return verdict.supported and verdict.score >= settings.grounding_min_score, verdict.score


def check_internal_consistency(unit: KnowledgeUnit, existing_claims: list[str]) -> bool:
    """
    Check 2: Internal Consistency
    Simple lexical contradiction scan; graph-based check happens in graph layer.
    """
    if not existing_claims:
        return True

    contradiction_markers = ["not ", "never ", "avoid ", "don't ", "shouldn't ", "incorrect"]
    unit_lower = unit.claim.lower()
    for existing in existing_claims:
        existing_lower = existing.lower()
        # Same domain topic but explicit negation pattern
        shared_words = set(unit_lower.split()) & set(existing_lower.split())
        if len(shared_words) < 3:
            continue
        for marker in contradiction_markers:
            if marker in unit_lower and marker not in existing_lower:
                if any(w in existing_lower for w in shared_words if len(w) > 4):
                    return False
    return True


async def check_comprehension(unit: KnowledgeUnit) -> tuple[bool, list[str]]:
    """
    Check 3: Comprehension Verification (Microsoft Self-Verification pattern)
    Generate questions, answer from unit only, fail if lossy.
    """
    client = instructor.from_provider(settings.llm_provider)

    questions: QuestionSet = client.create(
        response_model=QuestionSet,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate 3 questions about this knowledge unit: "
                    "1 recall (what does it say), "
                    "1 application (when to use), "
                    "1 analysis (what it implies/limits). "
                    "Include expected answers."
                ),
            },
            {"role": "user", "content": f"Unit:\nClaim: {unit.claim}\nApplicability: {unit.applicability}"},
        ],
        max_retries=1,
    )

    unit_context = f"Claim: {unit.claim}\nType: {unit.type.value}\nApplicability: {unit.applicability}"
    failed: list[str] = []

    for q in questions.questions:
        class UnitAnswer(BaseModel):
            answer: str
            sufficient: bool

        eval_result: UnitAnswer = client.create(
            response_model=UnitAnswer,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer the question using ONLY the knowledge unit provided. "
                        "Mark sufficient=false if the unit lacks info to answer properly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Unit:\n{unit_context}\n\nQuestion ({q.level}): {q.question}",
                },
            ],
            max_retries=1,
        )
        if not eval_result.sufficient:
            failed.append(f"[{q.level}] {q.question}")

    passed = len(failed) == 0
    return passed, failed
