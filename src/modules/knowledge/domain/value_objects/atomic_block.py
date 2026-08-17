from src.kernel.domain.value_object import ValueObject
from src.modules.knowledge.domain.value_objects.atomic_block_type import (
    AtomicBlockType,
)


class AtomicBlock(ValueObject):
    content: str
    block_type: AtomicBlockType
    estimated_tokens: int
    header_level: int | None = None
    header_title: str | None = None
