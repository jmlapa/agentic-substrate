from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DataSourceSyncFailedEvent(DomainEvent):
    data_source_id: UUID
    run_id: UUID
    error_message: str
