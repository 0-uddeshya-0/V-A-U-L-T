"""Living knowledge graph — Neo4j storage, embeddings, and hybrid retrieval."""

from __future__ import annotations

from neo4j import GraphDatabase

from vault.config import settings
from vault.embeddings import EMBEDDING_DIM, embed_passage, embed_query, unit_embedding_text
from vault.models import EdgeType, GraphEdge, KnowledgeUnit, Partition, QueryResult, SourcePointer

VECTOR_INDEX = "unit_embeddings"


class KnowledgeGraph:
    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def ensure_schema(self) -> None:
        with self._driver.session() as session:
            session.run(
                "CREATE CONSTRAINT unit_id IF NOT EXISTS FOR (u:KnowledgeUnit) REQUIRE u.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE"
            )
            session.run(
                "CREATE INDEX unit_partition IF NOT EXISTS FOR (u:KnowledgeUnit) ON (u.partition)"
            )
            # Neo4j 5.13+ vector index
            session.run(
                f"""
                CREATE VECTOR INDEX {VECTOR_INDEX} IF NOT EXISTS
                FOR (u:KnowledgeUnit) ON (u.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {EMBEDDING_DIM},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """
            )

    def upsert_unit(self, unit: KnowledgeUnit, embedding: list[float] | None = None) -> None:
        if embedding is None:
            text = unit_embedding_text(unit.claim, unit.applicability, unit.domains)
            embedding = embed_passage(text)

        with self._driver.session() as session:
            session.run(
                """
                MERGE (u:KnowledgeUnit {id: $id})
                SET u.claim = $claim,
                    u.type = $type,
                    u.domains = $domains,
                    u.applicability = $applicability,
                    u.confidence = $confidence,
                    u.partition = $partition,
                    u.document_id = $document_id,
                    u.source_url = $source_url,
                    u.source_span = $source_span,
                    u.timestamp_start = $timestamp_start,
                    u.validation_failures = $validation_failures,
                    u.embedding = $embedding,
                    u.created_at = datetime($created_at)
                """,
                id=unit.id,
                claim=unit.claim,
                type=unit.type.value,
                domains=unit.domains,
                applicability=unit.applicability,
                confidence=unit.confidence,
                partition=unit.partition.value,
                document_id=unit.document_id,
                source_url=unit.source.url,
                source_span=unit.source.text_span,
                timestamp_start=unit.source.timestamp_start,
                validation_failures=unit.validation_failures,
                embedding=embedding,
                created_at=unit.created_at.isoformat(),
            )
            for domain in unit.domains:
                session.run(
                    """
                    MERGE (c:Concept {name: $name})
                    ON CREATE SET c.weight = 1
                    ON MATCH SET c.weight = c.weight + 1
                    WITH c
                    MATCH (u:KnowledgeUnit {id: $unit_id})
                    MERGE (u)-[:IS_EXAMPLE_OF]->(c)
                    """,
                    name=domain,
                    unit_id=unit.id,
                )
            for dep in unit.dependencies:
                session.run(
                    """
                    MERGE (c:Concept {name: $name})
                    WITH c
                    MATCH (u:KnowledgeUnit {id: $unit_id})
                    MERGE (u)-[:REQUIRES]->(c)
                    """,
                    name=dep,
                    unit_id=unit.id,
                )

    def add_edge(self, edge: GraphEdge) -> None:
        rel = edge.edge_type.value.upper()
        with self._driver.session() as session:
            session.run(
                f"""
                MATCH (a:KnowledgeUnit {{id: $source_id}}), (b:KnowledgeUnit {{id: $target_id}})
                MERGE (a)-[r:{rel}]->(b)
                SET r += $metadata
                """,
                source_id=edge.source_id,
                target_id=edge.target_id,
                metadata=edge.metadata,
            )

    def get_unit(self, unit_id: str) -> dict | None:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (u:KnowledgeUnit {id: $id}) RETURN u",
                id=unit_id,
            )
            record = result.single()
            return dict(record["u"]) if record else None

    def list_quarantine(self, limit: int = 50) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (u:KnowledgeUnit {partition: $q})
                RETURN u
                ORDER BY u.created_at DESC
                LIMIT $limit
                """,
                q=Partition.QUARANTINE.value,
                limit=limit,
            )
            return [_node_to_dict(r["u"]) for r in result]

    def approve_unit(self, unit_id: str) -> bool:
        """Promote quarantined unit to validated partition."""
        unit_data = self.get_unit(unit_id)
        if not unit_data or unit_data.get("partition") != Partition.QUARANTINE.value:
            return False

        with self._driver.session() as session:
            session.run(
                """
                MATCH (u:KnowledgeUnit {id: $id})
                SET u.partition = $validated
                """,
                id=unit_id,
                validated=Partition.VALIDATED.value,
            )

        unit = _dict_to_unit(unit_data)
        unit.partition = Partition.VALIDATED
        integrate_unit(self, unit)
        return True

    def reject_unit(self, unit_id: str) -> bool:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (u:KnowledgeUnit {id: $id, partition: $q})
                DETACH DELETE u
                RETURN count(u) AS deleted
                """,
                id=unit_id,
                q=Partition.QUARANTINE.value,
            )
            return result.single()["deleted"] > 0

    def list_contradictions(self, concept: str | None = None) -> list[dict]:
        with self._driver.session() as session:
            if concept:
                result = session.run(
                    """
                    MATCH (a:KnowledgeUnit)-[:CONTRADICTS]-(b:KnowledgeUnit)
                    MATCH (a)-[:IS_EXAMPLE_OF]->(c:Concept {name: $concept})
                    RETURN a.id AS a_id, a.claim AS a_claim,
                           b.id AS b_id, b.claim AS b_claim
                    LIMIT 20
                    """,
                    concept=concept,
                )
            else:
                result = session.run(
                    """
                    MATCH (a:KnowledgeUnit)-[r:CONTRADICTS]-(b:KnowledgeUnit)
                    WHERE id(a) < id(b)
                    RETURN a.id AS a_id, a.claim AS a_claim,
                           b.id AS b_id, b.claim AS b_claim
                    LIMIT 20
                    """
                )
            return [dict(r) for r in result]

    def find_contradictions(self, unit: KnowledgeUnit) -> list[str]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (u:KnowledgeUnit {id: $unit_id})-[:IS_EXAMPLE_OF]->(c:Concept)
                      <-[:IS_EXAMPLE_OF]-(other:KnowledgeUnit)
                WHERE other.id <> u.id
                  AND other.partition = $validated
                  AND other.type = u.type
                RETURN other.id AS id
                LIMIT 10
                """,
                unit_id=unit.id,
                validated=Partition.VALIDATED.value,
            )
            return [r["id"] for r in result]

    def query(
        self, task: str, domains: list[str] | None = None, limit: int = 10
    ) -> list[QueryResult]:
        """Hybrid retrieval: vector similarity + keyword + graph expansion."""
        query_embedding = embed_query(task)
        candidates: dict[str, tuple[dict, float]] = {}

        with self._driver.session() as session:
            # Vector search
            vector_hits = self._vector_search(session, query_embedding, domains, limit * 3)
            for rank, (node, score) in enumerate(vector_hits):
                rrf = 1.0 / (60 + rank)
                candidates[node["id"]] = (node, rrf * 0.6 + score * 0.4)

            # Keyword search boost
            keyword_hits = self._keyword_search(session, task, domains, limit * 3)
            for rank, node in enumerate(keyword_hits):
                rrf = 1.0 / (60 + rank)
                existing = candidates.get(node["id"])
                if existing:
                    candidates[node["id"]] = (node, existing[1] + rrf * 0.3)
                else:
                    candidates[node["id"]] = (node, rrf * 0.3)

        # Sort and expand via graph
        ranked = sorted(candidates.values(), key=lambda x: x[1], reverse=True)[:limit]

        results: list[QueryResult] = []
        with self._driver.session() as session:
            for node, score in ranked:
                related = self._get_related(session, node["id"])
                results.append(_node_to_query_result(node, related, score))

        return results

    def _vector_search(
        self, session, embedding: list[float], domains: list[str] | None, k: int
    ) -> list[tuple[dict, float]]:
        try:
            if domains:
                result = session.run(
                    f"""
                    CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $k, $embedding)
                    YIELD node, score
                    WHERE node.partition = $validated
                      AND ANY(d IN node.domains WHERE d IN $domains)
                    RETURN node, score
                    LIMIT $k
                    """,
                    k=k,
                    embedding=embedding,
                    validated=Partition.VALIDATED.value,
                    domains=domains,
                )
            else:
                result = session.run(
                    f"""
                    CALL db.index.vector.queryNodes('{VECTOR_INDEX}', $k, $embedding)
                    YIELD node, score
                    WHERE node.partition = $validated
                    RETURN node, score
                    LIMIT $k
                    """,
                    k=k,
                    embedding=embedding,
                    validated=Partition.VALIDATED.value,
                )
            return [(dict(r["node"]), r["score"]) for r in result]
        except Exception:
            return []

    def _keyword_search(
        self, session, task: str, domains: list[str] | None, k: int
    ) -> list[dict]:
        keywords = [w.lower() for w in task.split() if len(w) > 3][:8]
        if domains:
            result = session.run(
                """
                MATCH (u:KnowledgeUnit)-[:IS_EXAMPLE_OF]->(c:Concept)
                WHERE u.partition = $validated AND c.name IN $domains
                RETURN u AS node
                ORDER BY u.confidence DESC
                LIMIT $k
                """,
                validated=Partition.VALIDATED.value,
                domains=domains,
                k=k,
            )
        else:
            result = session.run(
                """
                MATCH (u:KnowledgeUnit)
                WHERE u.partition = $validated
                RETURN u AS node
                ORDER BY u.confidence DESC
                LIMIT $k
                """,
                validated=Partition.VALIDATED.value,
                k=k * 3,
            )

        nodes = [dict(r["node"]) for r in result]
        if keywords:
            nodes.sort(
                key=lambda n: sum(
                    1 for kw in keywords if kw in n.get("claim", "").lower()
                ),
                reverse=True,
            )
        return nodes[:k]

    def list_gaps(self) -> list[dict]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (c:Concept)<-[:REQUIRES]-(u:KnowledgeUnit)
                WHERE NOT EXISTS {
                    MATCH (c)<-[:IS_EXAMPLE_OF]-(v:KnowledgeUnit)
                    WHERE v.partition = 'validated'
                }
                RETURN c.name AS concept, count(u) AS reference_count
                ORDER BY reference_count DESC
                LIMIT 20
                """
            )
            return [{"concept": r["concept"], "reference_count": r["reference_count"]} for r in result]

    def _get_related(self, session, unit_id: str) -> list[dict]:
        result = session.run(
            """
            MATCH (u:KnowledgeUnit {id: $id})-[r]-(other:KnowledgeUnit)
            RETURN other.id AS unit_id, type(r) AS relationship
            LIMIT 5
            """,
            id=unit_id,
        )
        return [{"unit_id": r["unit_id"], "relationship": r["relationship"]} for r in result]


def integrate_unit(graph: KnowledgeGraph, unit: KnowledgeUnit) -> None:
    graph.upsert_unit(unit)
    contradictions = graph.find_contradictions(unit)
    for other_id in contradictions:
        graph.add_edge(
            GraphEdge(
                source_id=unit.id,
                target_id=other_id,
                edge_type=EdgeType.CONTRADICTS,
                metadata={"auto_detected": True},
            )
        )


def _node_to_dict(node) -> dict:
    d = dict(node)
    d.pop("embedding", None)
    return d


def _dict_to_unit(d: dict) -> KnowledgeUnit:
    from vault.models import KnowledgeType

    return KnowledgeUnit(
        id=d["id"],
        claim=d["claim"],
        type=KnowledgeType(d["type"]),
        domains=d.get("domains", []),
        applicability=d["applicability"],
        confidence=d["confidence"],
        document_id=d["document_id"],
        partition=Partition(d["partition"]),
        source=SourcePointer(
            url=d.get("source_url", ""),
            text_span=d.get("source_span"),
            timestamp_start=d.get("timestamp_start"),
        ),
    )


def _node_to_query_result(node: dict, related: list[dict], score: float) -> QueryResult:
    from vault.models import KnowledgeType

    return QueryResult(
        unit_id=node["id"],
        claim=node["claim"],
        type=KnowledgeType(node["type"]),
        applicability=node["applicability"],
        confidence=node["confidence"],
        source=SourcePointer(
            url=node.get("source_url", ""),
            text_span=node.get("source_span"),
            timestamp_start=node.get("timestamp_start"),
        ),
        related=related,
        relevance_score=round(score, 4),
    )
