from uuid import UUID

from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)


class InMemoryDataSourceRunRepository(IDataSourceRunRepository):
    def __init__(self) -> None:
        self._runs: dict[UUID, DataSourceRun] = {}

    async def save(self, run: DataSourceRun) -> None:
        self._runs[run.id] = run

    async def get_by_id(self, run_id: UUID) -> DataSourceRun | None:
        return self._runs.get(run_id)

    async def list_by_data_source_id(
        self, data_source_id: UUID, limit: int = 50
    ) -> list[DataSourceRun]:
        matching = [r for r in self._runs.values() if r.data_source_id == data_source_id]
        matching.sort(key=lambda r: r.started_at, reverse=True)
        return matching[:limit]

    async def record_document_indexed(
        self, run_id: UUID
    ) -> tuple[UUID, UUID, int, int, int, str] | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        if run.status.value in ("COMPLETED", "PARTIALLY_FAILED", "FAILED"):
            return None
        run.record_document_indexed()
        return (
            run.data_source_id,
            run.kb_id,
            run.indexed_files_count,
            run.failed_files_count,
            run.total_files_discovered,
            run.status.value,
        )

    async def record_document_failed(
        self, run_id: UUID, failure_item: dict[str, object]
    ) -> tuple[UUID, UUID, int, int, int, str] | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        if run.status.value in ("COMPLETED", "PARTIALLY_FAILED", "FAILED"):
            return None
        doc_id_val = failure_item.get("doc_id")
        doc_uuid = UUID(str(doc_id_val)) if doc_id_val else run.id
        run.record_document_failed(
            doc_id=doc_uuid,
            file_name=str(failure_item.get("file_name", "")),
            error=str(failure_item.get("error", "")),
        )
        return (
            run.data_source_id,
            run.kb_id,
            run.indexed_files_count,
            run.failed_files_count,
            run.total_files_discovered,
            run.status.value,
        )
