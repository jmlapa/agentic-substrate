from datetime import UTC, datetime

import pytest

from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)
from src.modules.knowledge.infrastructure.adapters.data_source_connector_registry import (
    DataSourceConnectorRegistry,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_connector import (
    InMemoryDataSourceConnector,
)


@pytest.mark.asyncio
async def test_in_memory_data_source_connector() -> None:
    connector = InMemoryDataSourceConnector()
    item = DiscoveredDocumentItem(
        external_id="file_1",
        name="Documento.pdf",
        mime_type="application/pdf",
        version_hash="v1_hash",
        modified_time=datetime.now(UTC),
        size_bytes=1024,
    )
    connector.mock_items = [item]
    connector.mock_next_cursor = "next_page_123"
    connector.mock_contents["file_1"] = (b"%PDF-1.4 content", "application/pdf", "v1_hash")

    batch = await connector.fetch_changes(config={"folder_id": "root"}, cursor=None)
    assert len(batch.items) == 1
    assert batch.items[0].external_id == "file_1"
    assert batch.next_cursor == "next_page_123"

    content, mime, v_hash = await connector.download_document("file_1", "application/pdf")
    assert content == b"%PDF-1.4 content"
    assert mime == "application/pdf"
    assert v_hash == "v1_hash"

    # Teste de fallback quando não explicitamente mockado
    fallback_content, fallback_mime, fallback_hash = await connector.download_document(
        "file_other", "text/plain"
    )
    assert fallback_content == b"mock content"
    assert fallback_mime == "text/plain"
    assert fallback_hash == "hash_file_other"


def test_data_source_connector_registry() -> None:
    registry = DataSourceConnectorRegistry()
    connector = InMemoryDataSourceConnector()

    registry.register(DataSourceType.GOOGLE_DRIVE_FOLDER, connector)

    resolved = registry.get_connector(DataSourceType.GOOGLE_DRIVE_FOLDER)
    assert resolved is connector

    with pytest.raises(KeyError, match="No connector registered"):
        registry.get_connector(DataSourceType.LOCAL_DIRECTORY)
