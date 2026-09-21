import logging
from uuid import UUID

from src.kernel.application.logger import Logger
from src.kernel.domain.domain_event import DomainEvent
from src.kernel.domain.result import Err
from src.modules.knowledge.application.use_cases.delete_document import (
    DeleteDocumentRequest,
    DeleteDocumentUseCase,
)
from src.modules.knowledge.domain.events.document_knowledge_indexed_event import (
    DocumentKnowledgeIndexedEvent,
)

_standard_logger = logging.getLogger("agentic_substrate.handlers.blue_green_swap")


class BlueGreenDocumentSwapHandler:
    """
    Handler reativo que escuta a indexação bem-sucedida de um documento no FalkorDB.
    Caso o documento substitua uma versão anterior (replaces_doc_id presente nos metadados),
    invoca o DeleteDocumentUseCase para expurgar a versão obsoleta atomicamente sem downtime.
    """

    def __init__(
        self,
        delete_use_case: DeleteDocumentUseCase,
        logger: Logger | None = None,
    ) -> None:
        self._delete_use_case = delete_use_case
        self._logger = logger

    def _log_info(self, message: str) -> None:
        if self._logger:
            self._logger.info(message)
        else:
            _standard_logger.info(message)

    def _log_error(self, message: str) -> None:
        if self._logger:
            self._logger.error(message)
        else:
            _standard_logger.error(message)

    def _log_debug(self, message: str) -> None:
        if self._logger:
            self._logger.debug(message)
        else:
            _standard_logger.debug(message)

    async def handle(self, event: DomainEvent) -> None:
        if not isinstance(event, DocumentKnowledgeIndexedEvent):
            return

        replaces_doc_id_val = event.metadata.get("replaces_doc_id")
        if not replaces_doc_id_val:
            self._log_debug(
                f"[BlueGreenDocumentSwapHandler] Documento '{event.document_id}' "
                "não possui replaces_doc_id. No-Op."
            )
            return

        try:
            old_doc_id = UUID(str(replaces_doc_id_val))
        except (ValueError, AttributeError) as e:
            self._log_error(
                f"[BlueGreenDocumentSwapHandler] ID anterior inválido: '{replaces_doc_id_val}': {e}"
            )
            return

        self._log_info(
            f"[BlueGreenDocumentSwapHandler] Atomic swap: novo doc '{event.document_id}' "
            f"indexado. Expurgando versão antiga '{old_doc_id}' da KB '{event.aggregate_id}'"
        )

        result = await self._delete_use_case.execute(
            DeleteDocumentRequest(
                kb_id=event.aggregate_id,
                document_id=old_doc_id,
            )
        )

        if isinstance(result, Err):
            self._log_error(
                f"[BlueGreenDocumentSwapHandler] Falha ao expurgar doc '{old_doc_id}': "
                f"{result.error.message}"
            )
        else:
            self._log_info(
                f"[BlueGreenDocumentSwapHandler] Versão antiga '{old_doc_id}' expurgada."
            )
