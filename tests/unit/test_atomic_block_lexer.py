from src.modules.knowledge.domain.value_objects.atomic_block_type import (
    AtomicBlockType,
)
from src.modules.knowledge.infrastructure.chunking.atomic_block_lexer import (
    AtomicBlockLexer,
)


def test_lex_empty_string() -> None:
    lexer = AtomicBlockLexer()
    assert lexer.lex("") == []
    assert lexer.lex("   \n\n   ") == []


def test_lex_headings() -> None:
    lexer = AtomicBlockLexer()
    md = "# Title 1\n\n## Subtitle 2\n\n### Section 3"
    blocks = lexer.lex(md)

    assert len(blocks) == 3
    assert blocks[0].block_type == AtomicBlockType.HEADING
    assert blocks[0].header_level == 1
    assert blocks[0].header_title == "Title 1"
    assert blocks[0].content == "# Title 1"

    assert blocks[1].block_type == AtomicBlockType.HEADING
    assert blocks[1].header_level == 2
    assert blocks[1].header_title == "Subtitle 2"

    assert blocks[2].block_type == AtomicBlockType.HEADING
    assert blocks[2].header_level == 3
    assert blocks[2].header_title == "Section 3"


def test_lex_fenced_code_block() -> None:
    lexer = AtomicBlockLexer()
    md = """Here is code:

```python
def hello():
    print("world")
    return True
```

After code paragraph."""
    blocks = lexer.lex(md)

    assert len(blocks) == 3
    assert blocks[0].block_type == AtomicBlockType.PARAGRAPH
    assert blocks[0].content == "Here is code:"

    assert blocks[1].block_type == AtomicBlockType.CODE_BLOCK
    assert "def hello():" in blocks[1].content
    assert blocks[1].content.startswith("```python")
    assert blocks[1].content.endswith("```")

    assert blocks[2].block_type == AtomicBlockType.PARAGRAPH
    assert blocks[2].content == "After code paragraph."


def test_lex_markdown_table() -> None:
    lexer = AtomicBlockLexer()
    md = """| Header 1 | Header 2 |
| :--- | :--- |
| Val 1 | Val 2 |
| Val 3 | Val 4 |"""
    blocks = lexer.lex(md)

    assert len(blocks) == 1
    assert blocks[0].block_type == AtomicBlockType.TABLE
    assert "| Header 1 | Header 2 |" in blocks[0].content
    assert "| Val 3 | Val 4 |" in blocks[0].content


def test_lex_lists_and_blockquotes() -> None:
    lexer = AtomicBlockLexer()
    md = """> Note: this is a blockquote
> with multiple lines.

* Item 1
* Item 2
- Item 3

1. Numbered 1
2. Numbered 2"""
    blocks = lexer.lex(md)

    assert len(blocks) == 3
    assert blocks[0].block_type == AtomicBlockType.BLOCKQUOTE
    assert "Note: this is a blockquote" in blocks[0].content

    assert blocks[1].block_type == AtomicBlockType.LIST
    assert "* Item 1" in blocks[1].content

    assert blocks[2].block_type == AtomicBlockType.LIST
    assert "1. Numbered 1" in blocks[2].content


def test_lex_thematic_break() -> None:
    lexer = AtomicBlockLexer()
    md = "Paragraph before\n\n---\n\nParagraph after"
    blocks = lexer.lex(md)

    assert len(blocks) == 3
    assert blocks[0].block_type == AtomicBlockType.PARAGRAPH
    assert blocks[1].block_type == AtomicBlockType.THEMATIC_BREAK
    assert blocks[1].content == "---"
    assert blocks[2].block_type == AtomicBlockType.PARAGRAPH


def test_lex_realistic_mixed_document() -> None:
    lexer = AtomicBlockLexer(chars_per_token=4)
    md = """# Constituição Federal de 1988

## TÍTULO I - DOS PRINCÍPIOS FUNDAMENTAIS

Art. 1º A República Federativa do Brasil, formada pela união indissolúvel dos Estados
e Municípios e do Distrito Federal, constitui-se em Estado Democrático de Direito e tem fundamentos:

* I - a soberania;
* II - a cidadania;
* III - a dignidade da pessoa humana;

```sql
SELECT * FROM constituicao WHERE artigo = 1;
```

| Artigo | Status |
|---|---|
| Art. 1º | Vigente |
"""
    blocks = lexer.lex(md)

    assert len(blocks) == 6
    assert blocks[0].block_type == AtomicBlockType.HEADING
    assert blocks[0].header_title == "Constituição Federal de 1988"

    assert blocks[1].block_type == AtomicBlockType.HEADING
    assert blocks[1].header_title == "TÍTULO I - DOS PRINCÍPIOS FUNDAMENTAIS"

    assert blocks[2].block_type == AtomicBlockType.PARAGRAPH
    assert "Art. 1º A República Federativa" in blocks[2].content

    assert blocks[3].block_type == AtomicBlockType.LIST
    assert "I - a soberania" in blocks[3].content

    assert blocks[4].block_type == AtomicBlockType.CODE_BLOCK
    assert "SELECT * FROM constituicao" in blocks[4].content

    assert blocks[5].block_type == AtomicBlockType.TABLE
    assert "| Artigo | Status |" in blocks[5].content
