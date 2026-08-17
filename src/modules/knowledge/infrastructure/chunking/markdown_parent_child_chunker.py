import re
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_markdown_chunker import (
    IMarkdownChunker,
)
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.document_chunk_collection import (
    DocumentChunkCollection,
)
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk


class MarkdownParentChildChunker(IMarkdownChunker):
    """
    Particionador hierárquico structure-aware de Markdown.
    Preserva tabelas, blocos de código e hierarquia de cabeçalhos (H1-H6),
    produzindo Parent Chunks (com subdivisão recursiva para seções longas)
    e Child Chunks vinculados para busca vetorial de alta precisão.
    """

    def __init__(
        self,
        max_parent_tokens: int = 1200,
        child_chunk_tokens: int = 200,
        child_overlap_tokens: int = 30,
        chars_per_token: int = 4,
    ) -> None:
        self._max_parent_tokens = max_parent_tokens
        self._child_chunk_tokens = child_chunk_tokens
        self._child_overlap_tokens = child_overlap_tokens
        self._chars_per_token = chars_per_token

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // self._chars_per_token)

    async def chunk(
        self,
        document_id: UUID,
        document_name: str,
        markdown_text: str,
    ) -> DocumentChunkCollection:
        clean_text = markdown_text.strip()
        if not clean_text:
            return DocumentChunkCollection(
                document_id=str(document_id),
                parents=[],
                children=[],
            )

        # 1. Separar seções por cabeçalhos preservando blocos cercados
        raw_sections = self._split_by_headers_or_fallback(document_name, clean_text)

        # 2. Refinar Parent Chunks com subdivisão recursiva para seções > max_parent_tokens
        parent_chunks: list[ParentChunk] = []
        parent_counter = 0

        for header_path, section_content in raw_sections:
            estimated_tokens = self._estimate_tokens(section_content)
            if estimated_tokens <= self._max_parent_tokens:
                parent_counter += 1
                parent_id = f"{document_id}-p{parent_counter}"
                parent_chunks.append(
                    ParentChunk(
                        id=parent_id,
                        header_path=header_path,
                        content=section_content,
                        token_count=estimated_tokens,
                        metadata={
                            "document_id": str(document_id),
                            "document_name": document_name,
                        },
                    )
                )
            else:
                sub_parents = self._recursively_split_large_section(
                    section_content,
                    self._max_parent_tokens,
                )
                for idx, sub_content in enumerate(sub_parents):
                    parent_counter += 1
                    parent_id = f"{document_id}-p{parent_counter}"
                    sub_header = (
                        f"{header_path} (Part {idx + 1}/{len(sub_parents)})"
                        if len(sub_parents) > 1
                        else header_path
                    )
                    parent_chunks.append(
                        ParentChunk(
                            id=parent_id,
                            header_path=sub_header,
                            content=sub_content,
                            token_count=self._estimate_tokens(sub_content),
                            metadata={
                                "document_id": str(document_id),
                                "document_name": document_name,
                                "part": idx + 1,
                                "total_parts": len(sub_parents),
                            },
                        )
                    )

        # 3. Gerar Child Chunks dentro de cada Parent Chunk
        child_chunks: list[ChildChunk] = []
        child_global_index = 0

        for parent in parent_chunks:
            child_texts = self._create_child_chunks_from_parent(
                parent.content,
                self._child_chunk_tokens,
                self._child_overlap_tokens,
            )
            for idx, child_text in enumerate(child_texts):
                child_id = f"{parent.id}-c{idx + 1}"
                child_chunks.append(
                    ChildChunk(
                        id=child_id,
                        parent_chunk_id=parent.id,
                        chunk_index=child_global_index,
                        header_path=parent.header_path,
                        content=child_text,
                        metadata={
                            "document_id": str(document_id),
                            "document_name": document_name,
                            "parent_chunk_id": parent.id,
                        },
                    )
                )
                child_global_index += 1

        return DocumentChunkCollection(
            document_id=str(document_id),
            parents=parent_chunks,
            children=child_chunks,
        )

    def _split_by_headers_or_fallback(
        self, document_name: str, markdown_text: str
    ) -> list[tuple[str, str]]:
        lines = markdown_text.splitlines(keepends=True)
        sections: list[tuple[str, str]] = []
        current_headers: dict[int, str] = {}
        current_lines: list[str] = []
        current_header_path = f"[Doc: {document_name}]"
        in_code_block = False

        header_regex = re.compile(r"^(#{1,6})\s+(.+)$")

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block

            if not in_code_block:
                match = header_regex.match(stripped)
                if match:
                    # Encontrou novo cabeçalho
                    if current_lines:
                        content = "".join(current_lines).strip()
                        if content:
                            sections.append((current_header_path, content))
                        current_lines = []

                    level = len(match.group(1))
                    title = match.group(2).strip()

                    # Atualizar pilha de cabeçalhos
                    current_headers = {k: v for k, v in current_headers.items() if k < level}
                    current_headers[level] = f"{match.group(1)} {title}"

                    # Construir breadcrumb
                    breadcrumb_parts = [f"[Doc: {document_name}]"]
                    for k in sorted(current_headers.keys()):
                        breadcrumb_parts.append(current_headers[k])
                    current_header_path = " > ".join(breadcrumb_parts)

            current_lines.append(line)

        if current_lines:
            content = "".join(current_lines).strip()
            if content:
                sections.append((current_header_path, content))

        if not sections:
            sections.append((f"[Doc: {document_name}]", markdown_text.strip()))

        return sections

    def _recursively_split_large_section(self, text: str, max_tokens: int) -> list[str]:
        max_chars = max_tokens * self._chars_per_token
        if len(text) <= max_chars:
            return [text]

        # Extrair blocos atômicos (parágrafos, tabelas, code blocks)
        blocks = self._extract_atomic_blocks(text)
        sub_sections: list[str] = []
        current_sub: list[str] = []
        current_length = 0

        for block in blocks:
            block_len = len(block)
            if current_length + block_len <= max_chars or not current_sub:
                current_sub.append(block)
                current_length += block_len
            else:
                sub_sections.append("\n\n".join(current_sub).strip())
                current_sub = [block]
                current_length = block_len

        if current_sub:
            sub_sections.append("\n\n".join(current_sub).strip())

        return sub_sections

    def _extract_atomic_blocks(self, text: str) -> list[str]:
        """
        Divide o texto em blocos atômicos (tabelas e blocos ``` não são fragmentados).
        """
        lines = text.splitlines()
        blocks: list[str] = []
        current_block: list[str] = []
        in_code_block = False
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                current_block.append(line)
                if not in_code_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                continue

            if in_code_block:
                current_block.append(line)
                continue

            is_table_line = stripped.startswith("|") and stripped.endswith("|")
            if is_table_line:
                in_table = True
                current_block.append(line)
                continue
            elif in_table:
                in_table = False
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []

            if not stripped:
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
            else:
                current_block.append(line)

        if current_block:
            blocks.append("\n".join(current_block))

        return [b.strip() for b in blocks if b.strip()]

    def _create_child_chunks_from_parent(
        self,
        parent_content: str,
        child_tokens: int,
        overlap_tokens: int,
    ) -> list[str]:
        child_chars = child_tokens * self._chars_per_token
        overlap_chars = overlap_tokens * self._chars_per_token

        if len(parent_content) <= child_chars:
            return [parent_content]

        # Divide o conteúdo do parent respeitando pontuação / quebras de linha
        sentences = re.split(r"(?<=[.!?\n])\s+", parent_content)
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for sentence in sentences:
            s_len = len(sentence)
            if current_len + s_len <= child_chars or not current_chunk:
                current_chunk.append(sentence)
                current_len += s_len
            else:
                chunk_text = " ".join(current_chunk).strip()
                chunks.append(chunk_text)

                # Calcular overlap a partir das últimas sentenças
                overlap_chunk: list[str] = []
                accum_overlap = 0
                for prev_sent in reversed(current_chunk):
                    if accum_overlap + len(prev_sent) <= overlap_chars:
                        overlap_chunk.insert(0, prev_sent)
                        accum_overlap += len(prev_sent)
                    else:
                        break

                current_chunk = overlap_chunk + [sentence]
                current_len = sum(len(s) for s in current_chunk) + len(current_chunk)

        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if not chunks or chunks[-1] != chunk_text:
                chunks.append(chunk_text)

        return chunks
