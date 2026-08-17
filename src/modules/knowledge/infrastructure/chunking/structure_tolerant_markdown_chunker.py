import re
from uuid import UUID

from src.modules.knowledge.domain.interfaces.i_markdown_chunker import (
    IMarkdownChunker,
)
from src.modules.knowledge.domain.value_objects.atomic_block import AtomicBlock
from src.modules.knowledge.domain.value_objects.atomic_block_type import (
    AtomicBlockType,
)
from src.modules.knowledge.domain.value_objects.child_chunk import ChildChunk
from src.modules.knowledge.domain.value_objects.document_chunk_collection import (
    DocumentChunkCollection,
)
from src.modules.knowledge.domain.value_objects.parent_chunk import ParentChunk
from src.modules.knowledge.infrastructure.chunking.atomic_block_lexer import (
    AtomicBlockLexer,
)


class StructureTolerantMarkdownChunker(IMarkdownChunker):
    """
    Particionador universal structure-tolerant de Markdown.
    Utiliza um lexer sintático de blocos atômicos indivisíveis e empacotamento guloso
    para garantir Parent Chunks uniformes (800 a 1.200 tokens) e Child Chunks
    de alta precisão (150 a 250 tokens com overlap semântico).
    """

    def __init__(
        self,
        max_parent_tokens: int = 1200,
        child_chunk_tokens: int = 200,
        child_overlap_tokens: int = 30,
        chars_per_token: int = 4,
        lexer: AtomicBlockLexer | None = None,
    ) -> None:
        self._max_parent_tokens = max_parent_tokens
        self._child_chunk_tokens = child_chunk_tokens
        self._child_overlap_tokens = child_overlap_tokens
        self._chars_per_token = max(1, chars_per_token)
        self._lexer = lexer or AtomicBlockLexer(chars_per_token=self._chars_per_token)

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

        # 1. Extração de blocos atômicos indivisíveis via Lexer
        atomic_blocks = self._lexer.lex(markdown_text)
        if not atomic_blocks:
            return DocumentChunkCollection(
                document_id=str(document_id),
                parents=[],
                children=[],
            )

        # 2. Empacotamento guloso em Parent Chunks
        parent_chunks: list[ParentChunk] = []
        current_blocks: list[AtomicBlock] = []
        current_tokens = 0
        parent_counter = 0

        active_headers: dict[int, str] = {}
        current_header_path = f"[Doc: {document_name}]"
        had_explicit_headers = False

        def build_breadcrumb() -> str:
            if not active_headers:
                return f"[Doc: {document_name}]"
            parts = [f"[Doc: {document_name}]"]
            for k in sorted(active_headers.keys()):
                parts.append(active_headers[k])
            return " > ".join(parts)

        def flush_current_parent() -> None:
            nonlocal current_blocks, current_tokens, parent_counter
            if not current_blocks:
                return
            parent_counter += 1
            parent_id = f"{document_id}-p{parent_counter}"
            joined_content = "\n\n".join(b.content for b in current_blocks).strip()

            header_path = current_header_path
            if not had_explicit_headers:
                header_path = f"[Doc: {document_name}] > Part {parent_counter}"

            parent_chunks.append(
                ParentChunk(
                    id=parent_id,
                    header_path=header_path,
                    content=joined_content,
                    token_count=self._estimate_tokens(joined_content),
                    metadata={
                        "document_id": str(document_id),
                        "document_name": document_name,
                        "parent_index": parent_counter,
                    },
                )
            )
            current_blocks = []
            current_tokens = 0

        for block in atomic_blocks:
            # Se for cabeçalho, atualiza hierarquia
            if block.block_type == AtomicBlockType.HEADING and block.header_level:
                had_explicit_headers = True
                active_headers = {k: v for k, v in active_headers.items() if k < block.header_level}
                active_headers[block.header_level] = block.content
                current_header_path = build_breadcrumb()

            # Caso de overflow: o bloco individual sozinho excede o limite máximo
            if block.estimated_tokens > self._max_parent_tokens:
                flush_current_parent()
                sub_contents = self._split_large_block(block.content, self._max_parent_tokens)
                for idx, sub_txt in enumerate(sub_contents):
                    parent_counter += 1
                    parent_id = f"{document_id}-p{parent_counter}"
                    sub_header = current_header_path
                    if len(sub_contents) > 1:
                        sub_header = f"{current_header_path} (Part {idx + 1}/{len(sub_contents)})"

                    parent_chunks.append(
                        ParentChunk(
                            id=parent_id,
                            header_path=sub_header,
                            content=sub_txt,
                            token_count=self._estimate_tokens(sub_txt),
                            metadata={
                                "document_id": str(document_id),
                                "document_name": document_name,
                                "parent_index": parent_counter,
                                "part": idx + 1,
                                "total_parts": len(sub_contents),
                            },
                        )
                    )
                continue

            # Empacotamento normal
            if current_tokens + block.estimated_tokens <= self._max_parent_tokens:
                current_blocks.append(block)
                current_tokens += block.estimated_tokens
            else:
                flush_current_parent()
                current_blocks = [block]
                current_tokens = block.estimated_tokens

        flush_current_parent()

        # 3. Geração determinística de Child Chunks
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

    def _split_large_block(self, text: str, max_tokens: int) -> list[str]:
        max_chars = max_tokens * self._chars_per_token
        if len(text) <= max_chars:
            return [text]

        # 1. Tentar divisão por sentenças
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) > 1:
            parts: list[str] = []
            cur_part: list[str] = []
            cur_len = 0
            for sent in sentences:
                s_len = len(sent)
                if cur_len + s_len <= max_chars or not cur_part:
                    cur_part.append(sent)
                    cur_len += s_len
                else:
                    parts.append(" ".join(cur_part).strip())
                    cur_part = [sent]
                    cur_len = s_len
            if cur_part:
                parts.append(" ".join(cur_part).strip())
            return parts

        # 2. Tentar divisão por linhas (\n)
        lines = text.splitlines()
        if len(lines) > 1:
            parts = []
            cur_part = []
            cur_len = 0
            for line_item in lines:
                l_len = len(line_item)
                if cur_len + l_len <= max_chars or not cur_part:
                    cur_part.append(line_item)
                    cur_len += l_len
                else:
                    parts.append("\n".join(cur_part).strip())
                    cur_part = [line_item]
                    cur_len = l_len
            if cur_part:
                parts.append("\n".join(cur_part).strip())
            return parts

        # 3. Fallback estrito por palavras
        words = text.split()
        parts = []
        cur_part = []
        cur_len = 0
        for w in words:
            w_len = len(w) + 1
            if cur_len + w_len <= max_chars or not cur_part:
                cur_part.append(w)
                cur_len += w_len
            else:
                parts.append(" ".join(cur_part).strip())
                cur_part = [w]
                cur_len = w_len
        if cur_part:
            parts.append(" ".join(cur_part).strip())
        return parts

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
