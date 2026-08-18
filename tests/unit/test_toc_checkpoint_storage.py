from uuid import uuid4

import pytest

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)
from src.modules.knowledge.domain.value_objects.toc_batch_state import (
    TocBatchState,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.toc_checkpoint_storage import (
    TocCheckpointStorage,
)


@pytest.mark.asyncio
async def test_toc_checkpoint_storage_save_and_get_batch(tmp_path: pytest.TempPathFactory) -> None:
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    toc_storage = TocCheckpointStorage(storage=storage)

    partition = "kb-test"
    doc_id = uuid4()
    batch_index = 1

    assert not await toc_storage.has_batch(partition, doc_id, batch_index)
    assert await toc_storage.get_batch(partition, doc_id, batch_index) is None

    items = [
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="1. Introduction",
            page=1,
            parent_section=None,
        ),
        HierarchicalTocItem(
            type="subsection",
            markdown_level="###",
            title="1.1 Overview",
            page=2,
            parent_section="1. Introduction",
        ),
    ]
    state = TocBatchState(
        active_section="1. Introduction",
        active_subsection="1.1 Overview",
        active_markdown_level="###",
        last_page_processed=2,
    )

    await toc_storage.save_batch(partition, doc_id, batch_index, items, state)

    assert await toc_storage.has_batch(partition, doc_id, batch_index)
    result = await toc_storage.get_batch(partition, doc_id, batch_index)
    assert result is not None
    loaded_items, loaded_state = result

    assert len(loaded_items) == 2
    assert loaded_items[0].title == "1. Introduction"
    assert loaded_items[1].title == "1.1 Overview"
    assert loaded_state.active_section == "1. Introduction"
    assert loaded_state.active_subsection == "1.1 Overview"
    assert loaded_state.active_markdown_level == "###"
    assert loaded_state.last_page_processed == 2


@pytest.mark.asyncio
async def test_toc_checkpoint_storage_save_and_get_full_toc(
    tmp_path: pytest.TempPathFactory,
) -> None:
    storage = LocalFileSystemStorageAdapter(base_directory=str(tmp_path))
    toc_storage = TocCheckpointStorage(storage=storage)

    partition = "kb-test"
    doc_id = uuid4()

    assert not await toc_storage.has_toc(partition, doc_id)
    assert await toc_storage.get_toc(partition, doc_id) is None

    items = [
        HierarchicalTocItem(
            type="document_title",
            markdown_level="#",
            title="Constitution",
            page=1,
        ),
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="Title I",
            page=2,
        ),
    ]
    full_toc = SyntheticDocumentToc(items=items)

    await toc_storage.save_toc(partition, doc_id, full_toc)

    assert await toc_storage.has_toc(partition, doc_id)
    loaded_toc = await toc_storage.get_toc(partition, doc_id)
    assert loaded_toc is not None
    assert loaded_toc.total_headings == 2
    assert loaded_toc.document_title == "Constitution"
