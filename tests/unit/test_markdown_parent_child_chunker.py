from uuid import uuid4

import pytest

from src.modules.knowledge.domain.interfaces.i_markdown_chunker import (
    IMarkdownChunker,
)
from src.modules.knowledge.infrastructure.chunking.markdown_parent_child_chunker import (
    MarkdownParentChildChunker,
)


@pytest.mark.asyncio
async def test_markdown_chunker_implements_protocol() -> None:
    chunker = MarkdownParentChildChunker()
    assert isinstance(chunker, IMarkdownChunker)


@pytest.mark.asyncio
async def test_markdown_chunker_empty_document() -> None:
    chunker = MarkdownParentChildChunker()
    doc_id = uuid4()
    result = await chunker.chunk(doc_id, "empty.md", "")
    assert result.document_id == str(doc_id)
    assert len(result.parents) == 0
    assert len(result.children) == 0


@pytest.mark.asyncio
async def test_markdown_chunker_headers_and_breadcrumbs() -> None:
    chunker = MarkdownParentChildChunker(max_parent_tokens=1000)
    doc_id = uuid4()
    markdown = """# Architecture Overview
This is the root introduction.

## Database Layer
We use PostgreSQL and FalkorDB.

### PgVector
Vector similarity search with HNSW indexes.

## API Gateway
FastAPI endpoints with dependency injection.
"""
    result = await chunker.chunk(doc_id, "architecture.md", markdown)
    assert result.document_id == str(doc_id)
    assert len(result.parents) == 4

    assert result.parents[0].header_path == ("[Doc: architecture.md] > # Architecture Overview")
    assert "root introduction" in result.parents[0].content

    assert result.parents[1].header_path == (
        "[Doc: architecture.md] > # Architecture Overview > ## Database Layer"
    )
    assert "FalkorDB" in result.parents[1].content

    assert (
        result.parents[2].header_path
        == "[Doc: architecture.md] > # Architecture Overview > ## Database Layer > ### PgVector"
    )
    assert "HNSW" in result.parents[2].content

    assert result.parents[3].header_path == (
        "[Doc: architecture.md] > # Architecture Overview > ## API Gateway"
    )
    assert "FastAPI" in result.parents[3].content

    assert len(result.children) >= 4
    for child in result.children:
        assert child.parent_chunk_id in [p.id for p in result.parents]
        assert child.header_path != ""


@pytest.mark.asyncio
async def test_markdown_chunker_preserves_tables_and_code_blocks() -> None:
    chunker = MarkdownParentChildChunker(max_parent_tokens=1000)
    doc_id = uuid4()
    markdown = """# Data Models

Here is the configuration table:

| Parameter | Type | Default |
| :--- | :--- | :--- |
| host | string | localhost |
| port | int | 5432 |

And here is the sample code:

```python
def connect():
    return asyncpg.connect("postgresql://localhost:5432")
```
"""
    result = await chunker.chunk(doc_id, "config.md", markdown)
    assert len(result.parents) == 1
    parent = result.parents[0]

    # Verify table is intact
    assert "| Parameter | Type | Default |" in parent.content
    assert "| host | string | localhost |" in parent.content

    # Verify code block is intact
    expected_code = (
        '```python\ndef connect():\n    return asyncpg.connect("postgresql://localhost:5432")\n```'
    )
    assert expected_code in parent.content


@pytest.mark.asyncio
async def test_markdown_chunker_recursively_splits_large_section() -> None:
    # Set max_parent_tokens small to force recursive split
    chunker = MarkdownParentChildChunker(
        max_parent_tokens=30,  # ~120 chars
        child_chunk_tokens=15,
        child_overlap_tokens=5,
    )
    doc_id = uuid4()
    long_section = """# Long Section
Paragraph one with some detailed explanation about the distributed system.

Paragraph two detailing consensus mechanisms, Raft leader election, and snapshotting routines.

Paragraph three discussing client retry backoff, circuit breakers, and exponential full jitter.
"""
    result = await chunker.chunk(doc_id, "large.md", long_section)

    assert len(result.parents) > 1
    for parent in result.parents:
        assert "[Doc: large.md] > # Long Section (Part" in parent.header_path
        assert parent.token_count > 0

    assert len(result.children) >= len(result.parents)


@pytest.mark.asyncio
async def test_markdown_chunker_fallback_for_headerless_document() -> None:
    chunker = MarkdownParentChildChunker(max_parent_tokens=500)
    doc_id = uuid4()
    markdown = """This is a document without any markdown headers.
It contains several paragraphs of pure text.

It should still be parsed into a parent chunk and child chunks with a fallback breadcrumb.
"""
    result = await chunker.chunk(doc_id, "notes.txt", markdown)
    assert len(result.parents) == 1
    assert result.parents[0].header_path == "[Doc: notes.txt]"
    assert len(result.children) >= 1
