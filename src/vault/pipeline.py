"""End-to-end document processing pipeline."""

from __future__ import annotations

from vault.extraction import extract_knowledge_units
from vault.graph import KnowledgeGraph, integrate_unit
from vault.models import NormalizedDocument, Partition
from vault.validation import validate_unit


async def process_document(doc: NormalizedDocument) -> dict:
    """Run extraction → validation → graph integration for a normalized document."""
    graph = KnowledgeGraph()
    graph.ensure_schema()

    units = await extract_knowledge_units(doc)

    existing_claims = _get_validated_claims(graph)
    validated_count = 0
    quarantined_count = 0
    results = []

    for unit in units:
        validation = await validate_unit(unit, doc, existing_claims)
        if validation.passed:
            integrate_unit(graph, unit)
            existing_claims.append(unit.claim)
            validated_count += 1
        else:
            unit.validation_failures = validation.failures
            graph.upsert_unit(unit)
            quarantined_count += 1

        results.append(
            {
                "unit_id": unit.id,
                "claim": unit.claim[:80],
                "partition": unit.partition.value,
                "passed": validation.passed,
                "failures": validation.failures,
            }
        )

    graph.close()
    return {
        "document_id": doc.id,
        "source_url": doc.source_url,
        "total_units": len(units),
        "validated": validated_count,
        "quarantined": quarantined_count,
        "units": results,
    }


def _get_validated_claims(graph: KnowledgeGraph) -> list[str]:
    with graph._driver.session() as session:
        result = session.run(
            "MATCH (u:KnowledgeUnit {partition: $p}) RETURN u.claim AS claim",
            p=Partition.VALIDATED.value,
        )
        return [r["claim"] for r in result]
