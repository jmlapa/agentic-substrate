import time

from src.modules.knowledge.domain.aggregates.knowledge_base_aggregate import KnowledgeBaseAggregate
from src.modules.knowledge.domain.events.document_attached_event import DocumentAttachedEvent
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.document_source_type import DocumentSourceType


def test_attach_document_with_source_type_and_ingested_at() -> None:
    kb = KnowledgeBaseAggregate.create(
        name="Personal Brain",
        description="Second Brain Knowledge Base",
        ontology=OntologySchema(
            name="general",
            description="General ontology",
            node_types=[],
            relationship_types=[],
        ),
    )

    t0 = time.time()
    doc_id = kb.attach_document(
        file_name="voice_note.m4a",
        content_type="audio/mp4",
        source_type=DocumentSourceType.AUDIO,
        ingested_at=t0,
    )

    assert doc_id in kb.documents
    doc_state = kb.documents[doc_id]
    assert doc_state["source_type"] == DocumentSourceType.AUDIO
    assert doc_state["ingested_at"] == t0
    assert doc_state["file_name"] == "voice_note.m4a"

    attached_events = [e for e in kb.uncommitted_events if isinstance(e, DocumentAttachedEvent)]
    assert len(attached_events) == 1
    assert attached_events[0].source_type == DocumentSourceType.AUDIO
    assert attached_events[0].ingested_at == t0


def test_attach_document_inferred_defaults() -> None:
    kb = KnowledgeBaseAggregate.create(
        name="Personal Brain",
        description="Second Brain Knowledge Base",
        ontology=OntologySchema(
            name="general",
            description="General ontology",
            node_types=[],
            relationship_types=[],
        ),
    )

    doc_id = kb.attach_document(
        file_name="screenshot.png",
        content_type="image/png",
    )

    doc_state = kb.documents[doc_id]
    assert doc_state["source_type"] == DocumentSourceType.IMAGE
    assert doc_state["ingested_at"] > 0
