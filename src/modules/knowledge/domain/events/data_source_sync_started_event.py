from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DataSourceSyncStartedEvent(DomainEvent):
    data_source_id: UUID
    run_id: UUID
    kb_id: UUID
