from uuid import UUID

from pydantic import Field

from src.kernel.domain.value_object import ValueObject
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk


class StructuralGraphDocument(ValueObject):
    document_id: UUID
    document_name: str
    parents: list[ParentChunk] = Field(default_factory=list)
    children: list[ChildChunk] = Field(default_factory=list)
