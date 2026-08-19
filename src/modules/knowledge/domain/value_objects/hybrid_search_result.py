from typing import Any

from pydantic import Field

from src.kernel.domain.value_object import ValueObject


class HybridSearchResult(ValueObject):
    parent_chunk_id: str
    header_path: str
    parent_content: str
    relevance_score: float
    document_id: str = ""
    document_name: str = ""
    retrieval_source: str = "vector_match"
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
    related_triples: list[str] = Field(default_factory=list)
    related_entities: list[dict[str, Any]] = Field(default_factory=list)
