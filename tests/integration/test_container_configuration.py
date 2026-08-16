import tempfile
from unittest.mock import MagicMock

import pytest

from src.api_gateway.container import create_app_container
from src.modules.knowledge.infrastructure.adapters.falkordb_graph_store_adapter import (
    FalkorDbGraphStoreAdapter,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)


@pytest.mark.asyncio
async def test_container_creates_local_adapters_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        container = create_app_container(storage_base_dir=tmpdir)
        assert isinstance(container.object_storage, LocalFileSystemStorageAdapter)
        assert isinstance(container.parser, MarkItDownDocumentParser)


@pytest.mark.asyncio
async def test_container_creates_falkordb_adapter() -> None:
    mock_client = MagicMock()
    container = create_app_container(
        graph_store_type="falkordb",
        falkordb_client=mock_client,
    )
    assert isinstance(container.graph_store, FalkorDbGraphStoreAdapter)
