import tempfile

import pytest

from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)


@pytest.mark.asyncio
async def test_local_file_system_storage_implements_protocol() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        assert isinstance(adapter, IObjectStorage)


@pytest.mark.asyncio
async def test_local_file_system_storage_put_and_get_object() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        test_path = "kb-123/documents/doc-456.txt"
        test_content = b"Hello, local storage world!"

        await adapter.put_object(test_path, test_content, "text/plain")

        retrieved_content = await adapter.get_object(test_path)
        assert retrieved_content == test_content


@pytest.mark.asyncio
async def test_local_file_system_storage_get_nonexistent_object_raises() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        with pytest.raises(FileNotFoundError):
            await adapter.get_object("nonexistent.txt")


@pytest.mark.asyncio
async def test_local_file_system_storage_prevent_path_traversal() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        with pytest.raises(ValueError, match="Path traversal"):
            await adapter.put_object("../../etc/passwd", b"bad", "text/plain")


@pytest.mark.asyncio
async def test_local_file_system_storage_generate_upload_url() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        url = await adapter.generate_upload_url("kb-1/doc.pdf")
        assert url.startswith("file://")
        assert "kb-1/doc.pdf" in url
