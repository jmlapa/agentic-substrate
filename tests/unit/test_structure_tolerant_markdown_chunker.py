from uuid import uuid4

import pytest

from src.modules.knowledge.infrastructure.chunking.structure_tolerant_markdown_chunker import (
    StructureTolerantMarkdownChunker,
)


@pytest.mark.asyncio
async def test_chunk_empty_document() -> None:
    chunker = StructureTolerantMarkdownChunker()
    doc_id = uuid4()
    result = await chunker.chunk(doc_id, "empty.md", "")

    assert result.document_id == str(doc_id)
    assert len(result.parents) == 0
    assert len(result.children) == 0


@pytest.mark.asyncio
async def test_chunk_small_document() -> None:
    chunker = StructureTolerantMarkdownChunker(max_parent_tokens=1000)
    doc_id = uuid4()
    md = "# Overview\nThis is a simple small document with one paragraph."
    result = await chunker.chunk(doc_id, "small.md", md)

    assert len(result.parents) == 1
    assert result.parents[0].id == f"{doc_id}-p1"
    assert result.parents[0].header_path == "[Doc: small.md] > # Overview"
    assert "simple small document" in result.parents[0].content
    assert len(result.children) >= 1
    assert result.children[0].parent_chunk_id == result.parents[0].id


@pytest.mark.asyncio
async def test_chunk_document_without_headings() -> None:
    # Quando não há cabeçalhos #, gera [Doc: {name}] > Part N
    chunker = StructureTolerantMarkdownChunker(max_parent_tokens=30, chars_per_token=4)
    doc_id = uuid4()
    paragraphs = [
        f"Paragraph {i}: This is some standard plain text without any markdown header."
        for i in range(1, 6)
    ]
    md = "\n\n".join(paragraphs)

    result = await chunker.chunk(doc_id, "no_headers.txt", md)

    assert len(result.parents) > 1
    for idx, p in enumerate(result.parents):
        assert p.header_path == f"[Doc: no_headers.txt] > Part {idx + 1}"
        assert p.id == f"{doc_id}-p{idx + 1}"


@pytest.mark.asyncio
async def test_preserve_tables_and_code_blocks() -> None:
    chunker = StructureTolerantMarkdownChunker(max_parent_tokens=150, chars_per_token=4)
    doc_id = uuid4()
    md = """# Data and Scripts

```python
def calculate_metrics(data: list[int]) -> dict[str, float]:
    return {"total": sum(data), "avg": sum(data) / len(data)}
```

| Metric | Target | Current |
|---|---|---|
| Latency | < 50ms | 32ms |
| Throughput | > 1000 rps | 1450 rps |
| Error Rate | < 0.01% | 0.002% |

Final summary paragraph of the system performance report.
"""
    result = await chunker.chunk(doc_id, "report.md", md)

    assert len(result.parents) >= 1
    # Verifica que o code block permaneceu íntegro
    code_parents = [p for p in result.parents if "def calculate_metrics" in p.content]
    assert len(code_parents) == 1
    assert code_parents[0].content.startswith("```python") or "```python" in code_parents[0].content
    assert "```" in code_parents[0].content

    # Verifica que a tabela permaneceu íntegra
    table_parents = [p for p in result.parents if "| Metric | Target |" in p.content]
    assert len(table_parents) == 1
    assert "| Error Rate | < 0.01% | 0.002% |" in table_parents[0].content


@pytest.mark.asyncio
async def test_single_large_paragraph_sentence_split_fallback() -> None:
    # Parágrafo contínuo único maior que max_parent_tokens deve acionar split por sentenças
    chunker = StructureTolerantMarkdownChunker(max_parent_tokens=25, chars_per_token=4)
    doc_id = uuid4()
    sentences = [
        "First sentence explaining the context.",
        "Second sentence providing detailed justification.",
        "Third sentence adding further technical rationale.",
        "Fourth sentence concluding the thought.",
    ]
    md = " ".join(sentences)

    result = await chunker.chunk(doc_id, "large_para.md", md)

    assert len(result.parents) > 1
    # Todas as sentenças devem estar preservadas no conjunto de parents
    combined_parents_text = " ".join(p.content for p in result.parents)
    for s in sentences:
        assert s in combined_parents_text


@pytest.mark.asyncio
async def test_child_chunks_overlap_and_indexing() -> None:
    chunker = StructureTolerantMarkdownChunker(
        max_parent_tokens=1000,
        child_chunk_tokens=20,
        child_overlap_tokens=5,
        chars_per_token=4,
    )
    doc_id = uuid4()
    md = """# Constitutional Article

Art. 5º Todos são iguais perante a lei, sem distinção de qualquer natureza.
Garante-se aos residentes no País a inviolabilidade do direito à vida.
A inviolabilidade estende-se à liberdade, à igualdade, à segurança e à propriedade.
Ninguém será submetido a tortura nem a tratamento desumano ou degradante.
É livre a manifestação do pensamento, sendo vedado o anonimato.
"""
    result = await chunker.chunk(doc_id, "cf88.md", md)

    assert len(result.parents) == 1
    assert len(result.children) > 1

    for idx, child in enumerate(result.children):
        assert child.parent_chunk_id == result.parents[0].id
        assert child.chunk_index == idx
        assert child.header_path == result.parents[0].header_path
        assert len(child.content) > 0


@pytest.mark.asyncio
async def test_chunk_with_source_type_and_ingested_at() -> None:
    from src.modules.knowledge.domain.value_objects.document_source_type import DocumentSourceType

    chunker = StructureTolerantMarkdownChunker()
    doc_id = uuid4()
    text = "# Title\n\nParagraph content here."
    t0 = 1787238000.0

    collection = await chunker.chunk(
        document_id=doc_id,
        document_name="note.md",
        markdown_text=text,
        source_type=DocumentSourceType.AUDIO,
        ingested_at=t0,
    )

    assert len(collection.parents) > 0
    assert len(collection.children) > 0

    for p in collection.parents:
        assert p.metadata.get("source_type") == "audio"
        assert p.metadata.get("ingested_at") == t0

    for c in collection.children:
        assert c.metadata.get("source_type") == "audio"
        assert c.metadata.get("ingested_at") == t0
