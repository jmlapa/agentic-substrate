import logging

from src.kernel.application.event_bus import EventBus
from src.kernel.application.logger import Logger
from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok, Result
from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.events.data_source_created_event import (
    DataSourceCreatedEvent,
)
from src.modules.knowledge.domain.interfaces.i_data_source_repository import (
    IDataSourceRepository,
)
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.domain.value_objects.google_drive_folder_config import (
    GoogleDriveFolderConfig,
)

from .create_data_source_request import CreateDataSourceRequest
from .create_data_source_response import CreateDataSourceResponse

_standard_logger = logging.getLogger("agentic_substrate.use_cases.create_data_source")


class CreateDataSourceUseCase:
    def __init__(
        self,
        kb_repository: IKnowledgeBaseRepository,
        data_source_repository: IDataSourceRepository,
        event_bus: EventBus | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._kb_repo = kb_repository
        self._ds_repo = data_source_repository
        self._event_bus = event_bus
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
        self, request: CreateDataSourceRequest
    ) -> Result[CreateDataSourceResponse, DomainError]:
        self._log_info(
            f"[CreateDataSourceUseCase] Criando DataSource '{request.name}' "
            f"(tipo={request.data_source_type.value}) para KB '{request.kb_id}'"
        )

        kb = await self._kb_repo.get_by_id(request.kb_id)
        if kb is None:
            msg = f"KnowledgeBase com ID '{request.kb_id}' não foi encontrada."
            self._log_error(f"[CreateDataSourceUseCase] {msg}")
            return Err(DomainError(msg, "KNOWLEDGE_BASE_NOT_FOUND"))

        if request.data_source_type == DataSourceType.GOOGLE_DRIVE_FOLDER:
            try:
                GoogleDriveFolderConfig.model_validate(request.config)
            except Exception as e:
                msg = f"Configuração inválida para GoogleDriveFolder: {e}"
                self._log_error(f"[CreateDataSourceUseCase] {msg}")
                return Err(DomainError(msg, "INVALID_DATA_SOURCE_CONFIG"))

        data_source = DataSource(
            kb_id=request.kb_id,
            name=request.name,
            data_source_type=request.data_source_type,
            config=request.config,
            sync_interval_minutes=request.sync_interval_minutes,
        )

        await self._ds_repo.save(data_source)
        self._log_info(
            f"[CreateDataSourceUseCase] DataSource salvo com sucesso. ID='{data_source.id}'"
        )

        if self._event_bus:
            event = DataSourceCreatedEvent(
                aggregate_id=data_source.id,
                aggregate_type="DataSource",
                data_source_id=data_source.id,
                kb_id=data_source.kb_id,
                name=data_source.name,
                data_source_type=data_source.data_source_type.value,
            )
            await self._event_bus.publish([event])
            self._log_info(
                f"[CreateDataSourceUseCase] DataSourceCreatedEvent publicado ID='{data_source.id}'"
            )

        return Ok(
            CreateDataSourceResponse(
                id=data_source.id,
                kb_id=data_source.kb_id,
                name=data_source.name,
                data_source_type=data_source.data_source_type.value,
                status=data_source.status.value,
                sync_interval_minutes=data_source.sync_interval_minutes,
                config=data_source.config,
                created_at=data_source.created_at,
            )
        )
