from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DataSourceSyncCompletedEvent(DomainEvent):
    data_source_id: UUID
    run_id: UUID
    synced_files_count: int
    new_cursor: str | None = None
