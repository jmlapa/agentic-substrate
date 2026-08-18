import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.page_checkpoint_storage import (
    PageCheckpointStorage,
)


@pytest.mark.asyncio
async def test_page_checkpoint_storage_save_and_get() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        checkpoint_storage = PageCheckpointStorage(storage=storage)

        doc_id = uuid4()
        partition = "kb-123"

        # Check initially false
        assert not await checkpoint_storage.has_page(partition, doc_id, 1)
        assert await checkpoint_storage.get_page(partition, doc_id, 1) is None

        # Save page 1
        await checkpoint_storage.save_page(partition, doc_id, 1, "# Page 1 Content")
        assert await checkpoint_storage.has_page(partition, doc_id, 1)
        content = await checkpoint_storage.get_page(partition, doc_id, 1)
        assert content == "# Page 1 Content"

        # Save page 2
        await checkpoint_storage.save_page(partition, doc_id, 2, "## Page 2 Content")
        completed = await checkpoint_storage.get_completed_pages(partition, doc_id)
        assert completed == {1, 2}

        # Verify raw path formatted with 4 digits padding
        expected_file = Path(tmpdir) / partition / "ocr_cache" / str(doc_id) / "page_0001.md"
        assert expected_file.exists()
