from uuid import uuid4

import pytest

from src.modules.knowledge.domain.entities.data_source import DataSource
from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.events.data_source_created_event import (
    DataSourceCreatedEvent,
)
from src.modules.knowledge.domain.events.data_source_run_completed_event import (
    DataSourceRunCompletedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_completed_event import (
    DataSourceSyncCompletedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_failed_event import (
    DataSourceSyncFailedEvent,
)
from src.modules.knowledge.domain.events.data_source_sync_started_event import (
    DataSourceSyncStartedEvent,
)
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.domain.value_objects.google_drive_folder_config import (
    GoogleDriveFolderConfig,
)


def test_data_source_initialization_and_validation() -> None:
    kb_id = uuid4()
    ds = DataSource(
        kb_id=kb_id,
        name="Pastas de Engenharia",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
        config={"folder_id": "folder_123"},
    )
    assert ds.kb_id == kb_id
    assert ds.name == "Pastas de Engenharia"
    assert ds.data_source_type == DataSourceType.GOOGLE_DRIVE_FOLDER
    assert ds.status == DataSourceStatus.IDLE
    assert ds.config == {"folder_id": "folder_123"}
    assert ds.cursor is None

    with pytest.raises(ValueError, match="name cannot be empty"):
        DataSource(kb_id=kb_id, name="   ")

    with pytest.raises(ValueError, match="kb_id is required"):
        DataSource(kb_id=None, name="Valido")


def test_data_source_start_sync() -> None:
    kb_id = uuid4()
    ds = DataSource(kb_id=kb_id, name="Docs")
    ds.start_sync()
    assert ds.status == DataSourceStatus.SYNCING

    with pytest.raises(ValueError, match="already syncing"):
        ds.start_sync()


def test_data_source_complete_sync() -> None:
    kb_id = uuid4()
    ds = DataSource(kb_id=kb_id, name="Docs", status=DataSourceStatus.SYNCING)
    ds.complete_sync(new_cursor="token_next_page")
    assert ds.status == DataSourceStatus.IDLE
    assert ds.cursor == "token_next_page"
    assert ds.last_synced_at is not None


def test_data_source_fail_sync() -> None:
    kb_id = uuid4()
    ds = DataSource(kb_id=kb_id, name="Docs", status=DataSourceStatus.SYNCING)
    ds.fail_sync("Erro de conexão com o Google Drive")
    assert ds.status == DataSourceStatus.FAILED
    assert ds.error_message == "Erro de conexão com o Google Drive"


def test_data_source_disable() -> None:
    kb_id = uuid4()
    ds = DataSource(kb_id=kb_id, name="Docs")
    ds.disable()
    assert ds.status == DataSourceStatus.DISABLED


def test_data_source_enable() -> None:
    kb_id = uuid4()
    ds = DataSource(kb_id=kb_id, name="Docs", status=DataSourceStatus.DISABLED)
    ds.enable()
    assert ds.status == DataSourceStatus.IDLE


def test_data_source_run_initial_state() -> None:
    run = DataSourceRun(
        data_source_id=uuid4(),
        kb_id=uuid4(),
    )
    assert run.status == DataSourceRunStatus.EXTRACTING
    assert run.total_files_discovered == 0
    assert run.completed_at is None


def test_data_source_run_lifecycle_and_completion() -> None:
    ds_id = uuid4()
    kb_id = uuid4()

    run = DataSourceRun(
        data_source_id=ds_id,
        kb_id=kb_id,
    )
    # Transição para ingesting
    run.mark_ingesting(total_files=2)
    assert run.total_files_discovered == 2

    # Primeiro arquivo indexado
    run.record_document_indexed()
    assert run.indexed_files_count == 1

    # Segundo arquivo indexado -> Finaliza como COMPLETED
    run.record_document_indexed()
    assert run.indexed_files_count == 2
    assert run.status == DataSourceRunStatus.COMPLETED
    assert run.completed_at is not None


def test_data_source_run_zero_files() -> None:
    ds_id = uuid4()
    kb_id = uuid4()
    run = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)
    run.mark_ingesting(total_files=0)
    assert run.status == DataSourceRunStatus.COMPLETED
    assert run.completed_at is not None


def test_data_source_run_partial_failure() -> None:
    ds_id = uuid4()
    kb_id = uuid4()

    run = DataSourceRun(
        data_source_id=ds_id,
        kb_id=kb_id,
    )
    run.mark_ingesting(total_files=2)

    # 1 arquivo indexado
    run.record_document_indexed()
    # 1 arquivo falha
    failed_doc_id = uuid4()
    run.record_document_failed(
        doc_id=failed_doc_id,
        file_name="corrupt.pdf",
        error="VLM OCR parser crashed",
    )

    assert run.status == DataSourceRunStatus.PARTIALLY_FAILED
    assert run.indexed_files_count == 1
    assert run.failed_files_count == 1
    assert len(run.failure_summary) == 1
    assert run.failure_summary[0]["file_name"] == "corrupt.pdf"
    assert run.completed_at is not None


def test_data_source_run_total_failure() -> None:
    ds_id = uuid4()
    kb_id = uuid4()
    run = DataSourceRun(data_source_id=ds_id, kb_id=kb_id)
    run.mark_ingesting(total_files=1)
    run.record_document_failed(doc_id=uuid4(), file_name="broken.pdf", error="Timeout")
    assert run.status == DataSourceRunStatus.FAILED
    assert run.completed_at is not None


def test_google_drive_folder_config_validation() -> None:
    cfg = GoogleDriveFolderConfig(folder_id="root_folder_1", baseline_days=15)
    assert cfg.folder_id == "root_folder_1"
    assert cfg.baseline_days == 15
    assert cfg.recursive is True

    with pytest.raises(ValueError, match="folder_id cannot be empty"):
        GoogleDriveFolderConfig(folder_id="   ")

    with pytest.raises(ValueError, match="baseline_days must be non-negative"):
        GoogleDriveFolderConfig(folder_id="valid", baseline_days=-5)


def test_domain_events_instantiation() -> None:
    ds_id = uuid4()
    kb_id = uuid4()
    run_id = uuid4()

    ev_created = DataSourceCreatedEvent(
        aggregate_id=ds_id,
        aggregate_type="DataSource",
        data_source_id=ds_id,
        kb_id=kb_id,
        name="Drive Legal",
        data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
    )
    assert ev_created.name == "Drive Legal"

    ev_started = DataSourceSyncStartedEvent(
        aggregate_id=ds_id,
        aggregate_type="DataSource",
        data_source_id=ds_id,
        run_id=run_id,
        kb_id=kb_id,
    )
    assert ev_started.run_id == run_id

    ev_completed = DataSourceSyncCompletedEvent(
        aggregate_id=ds_id,
        aggregate_type="DataSource",
        data_source_id=ds_id,
        run_id=run_id,
        synced_files_count=10,
        new_cursor="cursor_abc",
    )
    assert ev_completed.synced_files_count == 10

    ev_failed = DataSourceSyncFailedEvent(
        aggregate_id=ds_id,
        aggregate_type="DataSource",
        data_source_id=ds_id,
        run_id=run_id,
        error_message="Quotas exceeded",
    )
    assert ev_failed.error_message == "Quotas exceeded"

    ev_run_done = DataSourceRunCompletedEvent(
        aggregate_id=run_id,
        aggregate_type="DataSourceRun",
        run_id=run_id,
        data_source_id=ds_id,
        kb_id=kb_id,
        status="COMPLETED",
        total_files=5,
        indexed_files=5,
        failed_files=0,
    )
    assert ev_run_done.total_files == 5
