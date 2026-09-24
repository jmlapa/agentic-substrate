import re
import unicodedata

from src.kernel.application.use_case import UseCase
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.application.use_cases.get_document_content.document_toc_item_dto import (
    DocumentTocItemDTO,
)
from src.modules.knowledge.application.use_cases.get_document_content.get_document_content_request import (  # noqa: E501
    GetDocumentContentRequest,
)
from src.modules.knowledge.application.use_cases.get_document_content.get_document_content_response import (  # noqa: E501
    GetDocumentContentResponse,
)
from src.modules.knowledge.domain.interfaces.i_document_repository import (
    IDocumentRepository,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class GetDocumentContentUseCase(UseCase[GetDocumentContentRequest, GetDocumentContentResponse]):
    """
    Caso de uso para recuperar o Markdown canônico e a estrutura hierárquica
    de seções (ToC) de um documento para visualização no Portal de Notas.
    """

    def __init__(
        self,
        kb_repository: IKnowledgeBaseRepository,
        storage: IObjectStorage,
        document_repo: IDocumentRepository | None = None,
    ) -> None:
        self._kb_repo = kb_repository
        self._storage = storage
        self._doc_repo = document_repo
        self._heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    def _generate_anchor(self, text: str) -> str:
        # Remove acentos para gerar slugs ascii limpos e consistentes
        normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
        clean = re.sub(r"[^\w\s-]", "", normalized.lower()).strip()
        slug = re.sub(r"[-\s]+", "-", clean)
        return slug or "section"

    def _extract_toc(self, markdown_text: str) -> list[DocumentTocItemDTO]:
        toc: list[DocumentTocItemDTO] = []
        for line in markdown_text.splitlines():
            match = self._heading_pattern.match(line.strip())
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                anchor = self._generate_anchor(title)
                toc.append(DocumentTocItemDTO(level=level, title=title, anchor=anchor))
        return toc

    async def execute(
        self, request: GetDocumentContentRequest
    ) -> Result[GetDocumentContentResponse, DomainError]:
        kb = await self._kb_repo.get_by_id(request.kb_id)
        if not kb:
            return Err(
                DomainError(
                    code="NOT_FOUND",
                    message=f"Knowledge Base {request.kb_id} not found",
                )
            )

        doc_info = kb.documents.get(request.document_id)
        if not doc_info and self._doc_repo is not None:
            doc = await self._doc_repo.get_by_id(request.document_id)
            if doc is not None and doc.kb_id == request.kb_id:
                doc_info = {
                    "file_name": doc.file_name,
                    "source_type": doc.source_type,
                    "status": doc.status,
                    "markdown_path": doc.markdown_storage_path,
                    "total_parents": doc.total_parents,
                    "total_children": doc.total_children,
                    "ingested_at": doc.ingested_at,
                }

        if not doc_info:
            return Err(
                DomainError(
                    code="NOT_FOUND",
                    message=f"Document {request.document_id} not found in KB {request.kb_id}",
                )
            )

        status_val = (
            doc_info["status"].value
            if hasattr(doc_info.get("status"), "value")
            else str(doc_info.get("status", "UNKNOWN"))
        )

        md_path = doc_info.get(
            "markdown_path",
            f"{kb.storage_partition}/markdown/{request.document_id}.md",
        )

        markdown_content = ""
        if await self._storage.exists(md_path):
            raw_bytes = await self._storage.get_object(md_path)
            markdown_content = raw_bytes.decode("utf-8", errors="replace")

        toc_tree = self._extract_toc(markdown_content)

        return Ok(
            GetDocumentContentResponse(
                document_id=request.document_id,
                kb_id=request.kb_id,
                file_name=doc_info.get("file_name", "document.md"),
                source_type=doc_info.get("source_type", "document"),
                status=status_val,
                total_parents=doc_info.get("total_parents") or 0,
                total_children=doc_info.get("total_children") or 0,
                markdown_content=markdown_content,
                toc_tree=toc_tree,
                ingested_at=doc_info.get("ingested_at"),
            )
        )
