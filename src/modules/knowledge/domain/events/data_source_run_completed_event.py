from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DataSourceRunCompletedEvent(DomainEvent):
    run_id: UUID
    data_source_id: UUID
    kb_id: UUID
    status: str
    total_files: int
    indexed_files: int
    failed_files: int
