from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.kernel.domain.entity import Entity
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)


class DataSourceRun(Entity[UUID]):
    def __init__(
        self,
        id: UUID | None = None,
        data_source_id: UUID | None = None,
        kb_id: UUID | None = None,
        status: DataSourceRunStatus = DataSourceRunStatus.EXTRACTING,
        total_files_discovered: int = 0,
        indexed_files_count: int = 0,
        failed_files_count: int = 0,
        failure_summary: list[dict[str, Any]] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        super().__init__(id or uuid4())
        if data_source_id is None:
            raise ValueError("data_source_id is required for DataSourceRun")
        if kb_id is None:
            raise ValueError("kb_id is required for DataSourceRun")
        self._data_source_id = data_source_id
        self._kb_id = kb_id
        self._status = status
        self._total_files_discovered = max(0, total_files_discovered)
        self._indexed_files_count = max(0, indexed_files_count)
        self._failed_files_count = max(0, failed_files_count)
        self._failure_summary: list[dict[str, Any]] = list(failure_summary or [])
        now = datetime.now(UTC)
        self._started_at = started_at or now
        self._completed_at = completed_at

    @property
    def data_source_id(self) -> UUID:
        return self._data_source_id

    @property
    def kb_id(self) -> UUID:
        return self._kb_id

    @property
    def status(self) -> DataSourceRunStatus:
        return self._status

    @property
    def total_files_discovered(self) -> int:
        return self._total_files_discovered

    @property
    def indexed_files_count(self) -> int:
        return self._indexed_files_count

    @property
    def failed_files_count(self) -> int:
        return self._failed_files_count

    @property
    def failure_summary(self) -> list[dict[str, Any]]:
        return list(self._failure_summary)

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    def mark_ingesting(self, total_files: int) -> None:
        self._total_files_discovered = max(0, total_files)
        if self._total_files_discovered == 0:
            self._status = DataSourceRunStatus.COMPLETED
            self._completed_at = datetime.now(UTC)
        else:
            self._status = DataSourceRunStatus.INGESTING

    def record_document_indexed(self) -> None:
        self._indexed_files_count += 1
        self._check_completion()

    def record_document_failed(self, doc_id: UUID | None, file_name: str, error: str) -> None:
        self._failed_files_count += 1
        self._failure_summary.append(
            {
                "doc_id": str(doc_id) if doc_id else None,
                "file_name": file_name,
                "error": error,
            }
        )
        self._check_completion()

    def _check_completion(self) -> None:
        if self._indexed_files_count + self._failed_files_count >= self._total_files_discovered:
            if self._failed_files_count == 0:
                self._status = DataSourceRunStatus.COMPLETED
            elif self._indexed_files_count > 0:
                self._status = DataSourceRunStatus.PARTIALLY_FAILED
            else:
                self._status = DataSourceRunStatus.FAILED
            self._completed_at = datetime.now(UTC)
