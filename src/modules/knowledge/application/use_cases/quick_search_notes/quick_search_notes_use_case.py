import re
import unicodedata
from uuid import UUID

from src.kernel.application.use_case import UseCase
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_notes_request import (  # noqa: E501
    QuickSearchNotesRequest,
)
from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_notes_response import (  # noqa: E501
    QuickSearchNotesResponse,
)
from src.modules.knowledge.application.use_cases.quick_search_notes.quick_search_result_item_dto import (  # noqa: E501
    QuickSearchResultItemDTO,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class QuickSearchNotesUseCase(UseCase[QuickSearchNotesRequest, QuickSearchNotesResponse]):
    """
    Caso de uso de busca rápida textual nos títulos, cabeçalhos e trechos
    das notas da Knowledge Base para o Command Palette (Ctrl+K).
    """

    def __init__(
        self,
        kb_repository: IKnowledgeBaseRepository,
        storage: IObjectStorage,
    ) -> None:
        self._kb_repo = kb_repository
        self._storage = storage

    def _normalize(self, text: str) -> str:
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8").lower()

    def _generate_anchor(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
        clean = re.sub(r"[^\w\s-]", "", normalized.lower()).strip()
        slug = re.sub(r"[-\s]+", "-", clean)
        return slug or "section"

    async def execute(
        self, request: QuickSearchNotesRequest
    ) -> Result[QuickSearchNotesResponse, DomainError]:
        kb = await self._kb_repo.get_by_id(request.kb_id)
        if not kb:
            return Err(
                DomainError(
                    code="NOT_FOUND",
                    message=f"Knowledge Base {request.kb_id} not found",
                )
            )

        norm_query = self._normalize(request.query.strip())
        if not norm_query:
            return Ok(QuickSearchNotesResponse(query=request.query, results=[]))

        results: list[QuickSearchResultItemDTO] = []
        seen_keys: set[tuple[UUID, str]] = set()

        for doc_id, doc_info in kb.documents.items():
            file_name = doc_info.get("file_name", "document.md")

            # 1. Correspondência por título do arquivo/nota (insensível a acentos)
            if norm_query in self._normalize(file_name):
                key = (doc_id, "title")
                if key not in seen_keys:
                    seen_keys.add(key)
                    preview = doc_info.get("markdown_preview", "")
                    results.append(
                        QuickSearchResultItemDTO(
                            document_id=doc_id,
                            document_name=file_name,
                            match_type="title",
                            matched_title=file_name,
                            anchor="",
                            preview=preview[:180] if preview else "Nota cadastrada na base",
                        )
                    )

            # 2. Correspondência por cabeçalhos nos Chunks Summary
            chunks_summary = doc_info.get("chunks_summary", [])
            for chunk_item in chunks_summary:
                header_path = chunk_item.get("header_path", "")
                if norm_query in self._normalize(header_path):
                    parts = [p.strip() for p in header_path.split(">") if p.strip()]
                    last_header = parts[-1] if parts else header_path
                    clean_title = re.sub(r"^#+\s*", "", last_header)
                    anchor = self._generate_anchor(clean_title)

                    key = (doc_id, anchor)
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(
                            QuickSearchResultItemDTO(
                                document_id=doc_id,
                                document_name=file_name,
                                match_type="header",
                                matched_title=clean_title,
                                anchor=anchor,
                                preview=f"Seção em {header_path}",
                            )
                        )

            # 3. Correspondência por cabeçalhos no Markdown persistido no Storage
            md_path = doc_info.get("markdown_path", f"{kb.storage_partition}/markdown/{doc_id}.md")
            if await self._storage.exists(md_path):
                md_bytes = await self._storage.get_object(md_path)
                md_text = md_bytes.decode("utf-8", errors="replace")
                for line in md_text.splitlines():
                    line_stripped = line.strip()
                    if line_stripped.startswith("#") and norm_query in self._normalize(
                        line_stripped
                    ):
                        clean_title = re.sub(r"^#+\s*", "", line_stripped)
                        anchor = self._generate_anchor(clean_title)
                        key = (doc_id, anchor)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            results.append(
                                QuickSearchResultItemDTO(
                                    document_id=doc_id,
                                    document_name=file_name,
                                    match_type="header",
                                    matched_title=clean_title,
                                    anchor=anchor,
                                    preview=f"Seção: {clean_title}",
                                )
                            )
                            if len(results) >= request.limit:
                                break

            if len(results) >= request.limit:
                break

        return Ok(
            QuickSearchNotesResponse(
                query=request.query,
                results=results[: request.limit],
            )
        )
