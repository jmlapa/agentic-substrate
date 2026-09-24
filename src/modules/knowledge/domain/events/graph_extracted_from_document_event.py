from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


class GraphExtractedFromDocumentEvent(DomainEvent):
    document_id: UUID
    node_count: int
    edge_count: int
    extracted_graph: ExtractedGraph | None = None
    subgraph_storage_path: str | None = None
    kb_id: UUID | None = None
