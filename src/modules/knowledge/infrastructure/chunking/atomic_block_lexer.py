import re

from src.modules.knowledge.domain.value_objects.atomic_block import AtomicBlock
from src.modules.knowledge.domain.value_objects.atomic_block_type import (
    AtomicBlockType,
)


class AtomicBlockLexer:
    """
    Lexer sintático determinístico para Markdown.
    Decompõe o texto em uma sequência linear de blocos atômicos indivisíveis
    (Code Blocks, Tabelas, Cabeçalhos, Listas, Blockquotes e Parágrafos).
    """

    def __init__(self, chars_per_token: int = 4) -> None:
        self._chars_per_token = max(1, chars_per_token)
        self._heading_regex = re.compile(r"^(#{1,6})\s+(.+)$")
        self._thematic_break_regex = re.compile(r"^(?:[-*_]\s*){3,}$")
        self._list_item_regex = re.compile(r"^(\*|-|\+|\d+\.)\s+(.+)$")

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // self._chars_per_token)

    def lex(self, markdown_text: str) -> list[AtomicBlock]:
        clean_text = markdown_text.strip()
        if not clean_text:
            return []

        lines = markdown_text.splitlines()
        blocks: list[AtomicBlock] = []

        current_lines: list[str] = []
        current_type: AtomicBlockType = AtomicBlockType.PARAGRAPH
        in_code_block = False
        code_fence = ""

        def flush_current() -> None:
            nonlocal current_lines, current_type
            if not current_lines:
                return
            content = "\n".join(current_lines).strip()
            if content:
                tokens = self._estimate_tokens(content)
                blocks.append(
                    AtomicBlock(
                        content=content,
                        block_type=current_type,
                        estimated_tokens=tokens,
                    )
                )
            current_lines = []
            current_type = AtomicBlockType.PARAGRAPH

        for line in lines:
            stripped = line.strip()

            # 1. Tratamento de Fenced Code Block
            if stripped.startswith("```") or stripped.startswith("~~~"):
                fence_prefix = stripped[:3]
                if not in_code_block:
                    flush_current()
                    in_code_block = True
                    code_fence = fence_prefix
                    current_type = AtomicBlockType.CODE_BLOCK
                    current_lines.append(line)
                    continue
                elif code_fence == fence_prefix:
                    current_lines.append(line)
                    flush_current()
                    in_code_block = False
                    code_fence = ""
                    continue

            if in_code_block:
                current_lines.append(line)
                continue

            # Linha em branco = delimitador de parágrafo / bloco
            if not stripped:
                flush_current()
                continue

            # 2. Cabeçalhos (#, ##, etc.)
            heading_match = self._heading_regex.match(stripped)
            if heading_match:
                flush_current()
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                tokens = self._estimate_tokens(line)
                blocks.append(
                    AtomicBlock(
                        content=line.strip(),
                        block_type=AtomicBlockType.HEADING,
                        estimated_tokens=tokens,
                        header_level=level,
                        header_title=title,
                    )
                )
                continue

            # 3. Thematic Break (---, ***, ___)
            if self._thematic_break_regex.match(stripped):
                flush_current()
                tokens = self._estimate_tokens(line)
                blocks.append(
                    AtomicBlock(
                        content=line.strip(),
                        block_type=AtomicBlockType.THEMATIC_BREAK,
                        estimated_tokens=tokens,
                    )
                )
                continue

            # 4. Tabelas Markdown (| col1 | col2 |)
            is_table_row = stripped.startswith("|") and stripped.endswith("|")
            if is_table_row:
                if current_type != AtomicBlockType.TABLE:
                    flush_current()
                    current_type = AtomicBlockType.TABLE
                current_lines.append(line)
                continue
            elif current_type == AtomicBlockType.TABLE:
                flush_current()

            # 5. Citações em Bloco (> ...)
            if stripped.startswith(">"):
                if current_type != AtomicBlockType.BLOCKQUOTE:
                    flush_current()
                    current_type = AtomicBlockType.BLOCKQUOTE
                current_lines.append(line)
                continue
            elif current_type == AtomicBlockType.BLOCKQUOTE:
                flush_current()

            # 6. Listas (*, -, +, 1.)
            if self._list_item_regex.match(stripped):
                if current_type != AtomicBlockType.LIST:
                    flush_current()
                    current_type = AtomicBlockType.LIST
                current_lines.append(line)
                continue
            elif current_type == AtomicBlockType.LIST:
                flush_current()

            # 7. Parágrafos gerais
            if current_type != AtomicBlockType.PARAGRAPH:
                flush_current()
            current_lines.append(line)

        flush_current()
        return blocks
