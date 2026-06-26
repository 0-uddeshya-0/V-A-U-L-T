"""Knowledge graph integration tests — require Neo4j."""

from vault.graph import integrate_unit
from vault.models import Partition


def test_schema_creation(neo4j_available):
    graph = neo4j_available
    graph.close()


def test_upsert_and_query(neo4j_available, sample_units):
    graph = neo4j_available
    for unit in sample_units:
        integrate_unit(graph, unit)

    results = graph.query("rate limiting for APIs with burst traffic", limit=5)
    assert len(results) > 0
    assert any("token bucket" in r.claim.lower() or "429" in r.claim for r in results)
    assert results[0].relevance_score > 0

    graph.close()


def test_quarantine_lifecycle(neo4j_available, sample_units):
    graph = neo4j_available
    unit = sample_units[0]
    unit.partition = Partition.QUARANTINE
    unit.validation_failures = ["Comprehension verification failed"]
    graph.upsert_unit(unit)

    quarantined = graph.list_quarantine()
    assert any(u["id"] == unit.id for u in quarantined)

    assert graph.approve_unit(unit.id)
    approved = graph.get_unit(unit.id)
    assert approved["partition"] == Partition.VALIDATED.value

    graph.close()


def test_list_gaps(neo4j_available, sample_units):
    graph = neo4j_available
    unit = sample_units[0]
    unit.dependencies = ["b-tree-indexing"]
    integrate_unit(graph, unit)

    gaps = graph.list_gaps()
    assert any(g["concept"] == "b-tree-indexing" for g in gaps)

    graph.close()
