import logging

from src.kernel.application.logger import Logger
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)

from .delete_data_source_request import DeleteDataSourceRequest
from .delete_data_source_response import DeleteDataSourceResponse

_standard_logger = logging.getLogger("agentic_substrate.use_cases.delete_data_source")


class DeleteDataSourceUseCase:
    def __init__(
        self,
        data_source_repository: IDataSourceRepository,
        logger: Logger | None = None,
    ) -> None:
        self._ds_repo = data_source_repository
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

    async def execute(
        self, request: DeleteDataSourceRequest
    ) -> Result[DeleteDataSourceResponse, DomainError]:
        self._log_info(
            f"[DeleteDataSourceUseCase] Removendo DataSource id='{request.data_source_id}'"
        )

        existing = await self._ds_repo.get_by_id(request.data_source_id)
        if existing is None:
            msg = f"DataSource com ID '{request.data_source_id}' não foi encontrado."
            self._log_error(f"[DeleteDataSourceUseCase] {msg}")
            return Err(DomainError(msg, "DATA_SOURCE_NOT_FOUND"))

        deleted = await self._ds_repo.delete(request.data_source_id)
        self._log_info(
            f"[DeleteDataSourceUseCase] DataSource '{request.data_source_id}' removido: {deleted}"
        )

        return Ok(
            DeleteDataSourceResponse(
                data_source_id=request.data_source_id,
                success=deleted,
            )
        )
