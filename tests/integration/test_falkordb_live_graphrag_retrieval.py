from uuid import uuid4

import pytest
from falkordb import FalkorDB

from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph
from src.modules.knowledge.domain.value_objects.graph_edge import GraphEdge
from src.modules.knowledge.domain.value_objects.graph_node import GraphNode
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.domain.value_objects.structural_graph_document import (
    StructuralGraphDocument,
)
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)


@pytest.mark.asyncio
async def test_falkordb_live_graphrag_retrieval_and_expansion() -> None:
    # 1. Connect to live FalkorDB container on port 6380
    client = FalkorDB(host="localhost", port=6380)
    adapter = FalkorDbGraphStoreAdapter(client=client)

    kb_id = uuid4()
    graph_name = f"kb_{kb_id.hex}"
    graph_handle = client.select_graph(graph_name)

    try:
        # 2. Ensure vector index in live FalkorDB
        await adapter.ensure_vector_index(kb_id, dimension=4, similarity_function="cosine")

        # 3. Create structural document with 3 sequential parents
        doc_id = uuid4()
        p1 = ParentChunk(
            id="parent-sec-1",
            header_path="# Capítulo 1 > Seção 1",
            content="Esta seção trata sobre privacidade e proteção de dados pessoais sob a LGPD.",
            token_count=80,
        )
        p2 = ParentChunk(
            id="parent-sec-2",
            header_path="# Capítulo 1 > Seção 2",
            content="Esta seção aborda contratos administrativos e licitações sob a Lei 14.133.",
            token_count=90,
        )
        p3 = ParentChunk(
            id="parent-sec-3",
            header_path="# Capítulo 1 > Seção 3",
            content="Disposições finais sobre governança e penalidades contratuais.",
            token_count=70,
        )

        # Embedding close to query vector [1.0, 0.0, 0.0, 0.0]
        c1 = ChildChunk(
            id="child-1-1",
            parent_chunk_id="parent-sec-1",
            chunk_index=0,
            header_path="# Capítulo 1 > Seção 1",
            content="privacidade e proteção de dados pessoais",
            embedding=[0.99, 0.01, 0.0, 0.0],
        )
        # Embedding far from query vector
        c2 = ChildChunk(
            id="child-2-1",
            parent_chunk_id="parent-sec-2",
            chunk_index=0,
            header_path="# Capítulo 1 > Seção 2",
            content="contratos administrativos e licitações",
            embedding=[0.1, 0.9, 0.0, 0.0],
        )

        doc = StructuralGraphDocument(
            document_id=doc_id,
            document_name="governanca_publica.md",
            parents=[p1, p2, p3],
            children=[c1, c2],
        )

        nodes_count, edges_count = await adapter.store_structural_document(kb_id, doc)
        assert nodes_count == 6  # 1 doc + 3 parents + 2 children
        assert edges_count == 7  # 3 HAS_PARENT + 2 CONTAINS_CHILD + 2 NEXT (p1->p2, p2->p3)

        # 4. Ingest Ontological Entities with dynamic labels & Relational Triples
        node_lgpd = GraphNode(
            id="ent-lgpd",
            node_type="Regulation",
            properties={"name": "LGPD", "scope": "Nacional"},
        )
        node_lei = GraphNode(
            id="ent-lei-14133",
            node_type="Law",
            properties={"name": "Lei 14.133", "year": 2021},
        )
        edge_regulates = GraphEdge(
            source_id="ent-lgpd",
            target_id="ent-lei-14133",
            relationship_type="REGULA",
            properties={"obrigatorio": True},
        )

        # Link parent-sec-1 to LGPD and Lei 14.133 with relationship
        await adapter.store_parent_mentions(
            kb_id,
            "parent-sec-1",
            ExtractedGraph(nodes=[node_lgpd, node_lei], edges=[edge_regulates]),
        )
        # Link parent-sec-2 to LGPD and Lei 14.133
        await adapter.store_parent_mentions(
            kb_id,
            "parent-sec-2",
            ExtractedGraph(nodes=[node_lgpd, node_lei], edges=[]),
        )

        # 5. Query Hybrid Search against live FalkorDB with top_k=3
        query_vec = [1.0, 0.0, 0.0, 0.0]
        results_top_3 = await adapter.query_hybrid(kb_id, query_vec, top_k=3, candidate_k=50)

        # Assertions on real FalkorDB response
        assert len(results_top_3) >= 1
        top_res = results_top_3[0]
        assert top_res.parent_chunk_id == "parent-sec-1"
        assert top_res.document_name == "governanca_publica.md"
        assert top_res.next_chunk_id == "parent-sec-2"
        assert top_res.prev_chunk_id is None
        assert top_res.retrieval_source == "vector_match"
        assert top_res.relevance_score > 0.8

        # Verify that related triples are extracted from the live graph
        assert any("LGPD" in t and "REGULA" in t for t in top_res.related_triples)

        # Verify that entities with dynamic labels (:Regulation, :Law) are preserved
        entity_types = [e.get("type") for e in top_res.related_entities]
        assert "Regulation" in entity_types or "Law" in entity_types

        # 6. Verify Top-1 Invariance: querying with top_k=1 evaluates all seeds naturally
        results_top_1 = await adapter.query_hybrid(kb_id, query_vec, top_k=1, candidate_k=50)
        assert len(results_top_1) == 1
        assert results_top_1[0].parent_chunk_id == results_top_3[0].parent_chunk_id
        assert results_top_1[0].relevance_score == results_top_3[0].relevance_score

    finally:
        # Cleanup graph from live FalkorDB
        try:
            graph_handle.delete()
        except Exception:
            pass
