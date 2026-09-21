from datetime import UTC, datetime
from typing import Any

from src.modules.knowledge.domain.interfaces.i_data_source_connector import (
    IDataSourceConnector,
)
from src.modules.knowledge.domain.value_objects.data_source_changes_batch import (
    DataSourceChangesBatch,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)


class InMemoryDataSourceConnector(IDataSourceConnector):
    """
    Adaptador em memória para simulação e testes unitários de conectores de DataSource.
    Permite configurar lotes de arquivos descobertos e seus respectivos conteúdos binários.
    """

    def __init__(self) -> None:
        self.mock_items: list[DiscoveredDocumentItem] = []
        self.mock_next_cursor: str | None = None
        self.mock_deleted_ids: list[str] = []
        self.mock_contents: dict[str, tuple[bytes, str, str]] = {}
        self.fetch_changes_calls: list[tuple[dict[str, Any], str | None]] = []
        self.download_calls: list[tuple[str, str]] = []

    def add_mock_file(
        self,
        external_id: str,
        name: str,
        content: bytes,
        mime_type: str = "text/plain",
        version_hash: str | None = None,
        modified_time: datetime | None = None,
    ) -> None:
        v_hash = version_hash or f"hash_{external_id}"
        m_time = modified_time or datetime.now(UTC)
        self.mock_items.append(
            DiscoveredDocumentItem(
                external_id=external_id,
                name=name,
                mime_type=mime_type,
                version_hash=v_hash,
                size_bytes=len(content),
                modified_time=m_time,
            )
        )
        self.mock_contents[external_id] = (content, mime_type, v_hash)
        self.mock_next_cursor = f"cursor-token-{len(self.mock_items)}"

    async def fetch_changes(
        self, config: dict[str, Any], cursor: str | None
    ) -> DataSourceChangesBatch:
        self.fetch_changes_calls.append((config, cursor))
        return DataSourceChangesBatch(
            items=list(self.mock_items),
            next_cursor=self.mock_next_cursor,
            deleted_external_ids=list(self.mock_deleted_ids),
        )

    async def download_document(self, external_id: str, mime_type: str) -> tuple[bytes, str, str]:
        self.download_calls.append((external_id, mime_type))
        if external_id in self.mock_contents:
            return self.mock_contents[external_id]
        # Fallback padrão caso não esteja explicitamente configurado
        return (b"mock content", mime_type, f"hash_{external_id}")
