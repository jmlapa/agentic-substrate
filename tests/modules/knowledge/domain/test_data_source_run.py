from uuid import uuid4

from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)


def test_data_source_run_pending_cursor_and_metadata() -> None:
    ds_id = uuid4()
    kb_id = uuid4()
    run = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)

    assert run.pending_cursor is None
    run.set_pending_cursor("token-12345")
    assert run.pending_cursor == "token-12345"

    run.mark_ingesting(total_files=2)
    assert run.status.value == DataSourceRunStatus.INGESTING.value

    run.record_document_failed(
        doc_id=None,
        file_name="daily_2026_09_09.docx",
        error="[SSL] record layer failure",
        external_id="ext-file-123",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        version_hash="sha-999",
        size_bytes=1024,
    )

    assert run.failed_files_count == 1
    assert len(run.failure_summary) == 1
    fail_item = run.failure_summary[0]
    assert fail_item["file_name"] == "daily_2026_09_09.docx"
    assert fail_item["external_id"] == "ext-file-123"
    assert fail_item["mime_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # Resolve o item com sucesso durante retry
    run.resolve_item_success("daily_2026_09_09.docx")
    assert run.failed_files_count == 0
    assert len(run.failure_summary) == 0
    assert run.indexed_files_count == 1

    # Indexa o segundo item
    run.record_document_indexed()
    assert run.status.value == DataSourceRunStatus.COMPLETED.value
