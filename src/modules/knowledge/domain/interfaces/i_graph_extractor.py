from typing import Protocol, runtime_checkable
from uuid import UUID

from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.extracted_graph import ExtractedGraph


@runtime_checkable
class IGraphExtractor(Protocol):
    async def extract_graph(
        self,
        markdown_text: str,
        ontology: OntologySchema,
        kb_id: UUID | None = None,
    ) -> ExtractedGraph: ...
