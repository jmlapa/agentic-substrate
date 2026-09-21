from uuid import UUID

from src.kernel.domain.domain_event import DomainEvent


class DataSourceCreatedEvent(DomainEvent):
    data_source_id: UUID
    kb_id: UUID
    name: str
    data_source_type: str
