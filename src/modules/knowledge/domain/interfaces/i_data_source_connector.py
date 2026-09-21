from typing import Any, Protocol, runtime_checkable

from src.modules.knowledge.domain.value_objects.data_source_changes_batch import (
    DataSourceChangesBatch,
)


@runtime_checkable
class IDataSourceConnector(Protocol):
    async def fetch_changes(
        self, config: dict[str, Any], cursor: str | None
    ) -> DataSourceChangesBatch: ...

    async def download_document(
        self, external_id: str, mime_type: str
    ) -> tuple[bytes, str, str]:
        """
        Baixa o documento identificado por external_id.
        Retorna uma tupla (content_bytes, resolved_content_type, version_hash).
        """
        ...
