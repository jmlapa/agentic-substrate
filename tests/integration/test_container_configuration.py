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
from src.modules.knowledge.infrastructure.adapters.simple_markdown_parser import (
    SimpleMarkdownParser,
)


@pytest.mark.asyncio
async def test_container_creates_local_adapters() -> None:
    container = create_app_container(
        storage_type="local",
        parser_type="markitdown",
    )
    assert isinstance(container.object_storage, LocalFileSystemStorageAdapter)
    assert isinstance(container.parser, MarkItDownDocumentParser)


@pytest.mark.asyncio
async def test_container_creates_in_memory_and_simple_parser() -> None:
    container = create_app_container(
        storage_type="memory",
        parser_type="simple",
    )
    assert isinstance(container.parser, SimpleMarkdownParser)


@pytest.mark.asyncio
async def test_container_creates_falkordb_adapter() -> None:
    mock_client = MagicMock()
    container = create_app_container(
        graph_store_type="falkordb",
        falkordb_client=mock_client,
    )
    assert isinstance(container.graph_store, FalkorDbGraphStoreAdapter)
