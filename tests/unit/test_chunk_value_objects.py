import pytest
from pydantic import ValidationError

from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.document_chunk_collection import (
    DocumentChunkCollection,
)
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk


def test_parent_chunk_instantiation_and_immutability() -> None:
    parent = ParentChunk(
        id="parent-1",
        header_path="[Doc: spec.md] > # Architecture > ## Database",
        content="## Database\nPostgres is used as the relational and vector database.",
        token_count=18,
        metadata={"section": "database"},
    )
    assert parent.id == "parent-1"
    assert parent.header_path == "[Doc: spec.md] > # Architecture > ## Database"
    assert "Postgres" in parent.content
    assert parent.token_count == 18
    assert parent.metadata["section"] == "database"

    with pytest.raises(ValidationError):
        # Frozen model should reject mutation
        parent.content = "New content"


def test_child_chunk_instantiation_and_immutability() -> None:
    child = ChildChunk(
        id="child-1",
        parent_chunk_id="parent-1",
        chunk_index=0,
        header_path="[Doc: spec.md] > # Architecture > ## Database",
        content="Postgres is used as the relational and vector database.",
        embedding=[0.1, 0.2, 0.3],
        metadata={"tags": ["db", "postgres"]},
    )
    assert child.id == "child-1"
    assert child.parent_chunk_id == "parent-1"
    assert child.chunk_index == 0
    assert child.embedding == [0.1, 0.2, 0.3]
    assert child.metadata["tags"] == ["db", "postgres"]

    with pytest.raises(ValidationError):
        child.chunk_index = 1


def test_document_chunk_collection() -> None:
    parent = ParentChunk(
        id="parent-1",
        header_path="[Doc: doc.md] > # Intro",
        content="# Intro\nWelcome.",
        token_count=5,
    )
    child = ChildChunk(
        id="child-1",
        parent_chunk_id="parent-1",
        chunk_index=0,
        header_path="[Doc: doc.md] > # Intro",
        content="Welcome.",
    )
    collection = DocumentChunkCollection(
        document_id="doc-123",
        parents=[parent],
        children=[child],
    )
    assert collection.document_id == "doc-123"
    assert len(collection.parents) == 1
    assert len(collection.children) == 1
    assert collection.parents[0].id == "parent-1"
    assert collection.children[0].parent_chunk_id == "parent-1"
