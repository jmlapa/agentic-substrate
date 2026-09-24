from uuid import uuid4

from src.modules.knowledge.domain.aggregates.document_aggregate import DocumentAggregate
from src.modules.knowledge.domain.value_objects.document_source_type import DocumentSourceType
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus


def _assert_status(doc: DocumentAggregate, expected: DocumentStatus) -> None:
    assert doc.status == expected


def test_document_aggregate_lifecycle_and_replay() -> None:
    doc_id = uuid4()
    kb_id = uuid4()

    # 1. Criação / Attach
    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="relatorio_anual.pdf",
        content_type="application/pdf",
        storage_path=f"kb-{kb_id}/raw/{doc_id}-relatorio_anual.pdf",
        enable_ocr=True,
        ocr_instructions="Extrair tabelas detalhadas",
        source_type=DocumentSourceType.DOCUMENT,
        metadata={"author": "Financeiro"},
    )

    assert doc.id == doc_id
    assert doc.kb_id == kb_id
    _assert_status(doc, DocumentStatus.PENDING_UPLOAD)
    assert doc.enable_ocr is True
    assert doc.metadata == {"author": "Financeiro"}
    assert len(doc.uncommitted_events) == 1

    # 2. Mark Stored
    doc.mark_stored(storage_path="kb-1/raw/file.pdf", byte_size=2048)
    _assert_status(doc, DocumentStatus.UPLOADED)
    assert doc.byte_size == 2048
    assert len(doc.uncommitted_events) == 2

    # 3. Mark Parsed
    doc.mark_parsed(
        markdown_storage_path="kb-1/markdown/file.md",
        markdown_preview="# Relatório Anual\nConteúdo...",
    )
    _assert_status(doc, DocumentStatus.PARSED)
    assert doc.markdown_storage_path == "kb-1/markdown/file.md"
    assert len(doc.uncommitted_events) == 3

    # 4. Mark Chunked
    doc.mark_chunked(
        total_parents=5,
        total_children=25,
        chunks_summary=[{"parent_id": "p1", "children_count": 5}],
    )
    _assert_status(doc, DocumentStatus.CHUNKED)
    assert doc.total_parents == 5
    assert doc.total_children == 25
    assert len(doc.uncommitted_events) == 4

    # 5. Mark Graph Extracted (Lean)
    doc.mark_graph_extracted(
        node_count=12,
        edge_count=18,
        subgraph_storage_path="kb-1/chunks/subgraphs/doc.json",
    )
    _assert_status(doc, DocumentStatus.GRAPH_EXTRACTED)
    assert doc.node_count == 12
    assert doc.edge_count == 18
    assert doc.subgraph_storage_path == "kb-1/chunks/subgraphs/doc.json"
    assert len(doc.uncommitted_events) == 5

    # 6. Mark Knowledge Indexed
    doc.mark_knowledge_indexed(indexed_nodes=12, indexed_edges=18)
    _assert_status(doc, DocumentStatus.INDEXED)
    assert doc.indexed_nodes_count == 12
    assert doc.indexed_edges_count == 18
    assert len(doc.uncommitted_events) == 6

    # 7. Simula Commit e Replay via Event Sourcing (O(1))
    events = list(doc.uncommitted_events)
    for i, ev in enumerate(events, 1):
        ev.event_version = i
    doc.mark_events_as_committed()
    assert len(doc.uncommitted_events) == 0

    rehydrated_doc = DocumentAggregate(id=doc_id)
    rehydrated_doc.load_from_history(events)

    assert rehydrated_doc.id == doc_id
    assert rehydrated_doc.kb_id == kb_id
    assert rehydrated_doc.status == DocumentStatus.INDEXED
    assert rehydrated_doc.file_name == "relatorio_anual.pdf"
    assert rehydrated_doc.byte_size == 2048
    assert rehydrated_doc.total_parents == 5
    assert rehydrated_doc.total_children == 25
    assert rehydrated_doc.indexed_nodes_count == 12
    assert rehydrated_doc.indexed_edges_count == 18
    assert rehydrated_doc.version == 6


def test_document_aggregate_failure_transition() -> None:
    doc_id = uuid4()
    kb_id = uuid4()

    doc = DocumentAggregate.create(
        document_id=doc_id,
        kb_id=kb_id,
        file_name="falha.pdf",
        content_type="application/pdf",
        storage_path="path",
    )

    doc.mark_processing_failed(step="PARSING", error_message="PDF corrompido")
    assert doc.status == DocumentStatus.FAILED
    assert doc.error_step == "PARSING"
    assert doc.error_message == "PDF corrompido"
