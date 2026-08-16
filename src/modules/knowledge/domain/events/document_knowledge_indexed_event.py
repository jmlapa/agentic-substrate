from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DocumentKnowledgeIndexedEvent(DomainEvent):
    document_id: UUID
    indexed_nodes_count: int
    indexed_edges_count: int
