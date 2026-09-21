from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.kernel.domain.entity import Entity
from src.modules.knowledge.domain.value_objects.data_source_status import (
    DataSourceStatus,
)
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)


class DataSource(Entity[UUID]):
    def __init__(
        self,
        id: UUID | None = None,
        kb_id: UUID | None = None,
        name: str = "",
        data_source_type: DataSourceType = DataSourceType.GOOGLE_DRIVE_FOLDER,
        status: DataSourceStatus = DataSourceStatus.IDLE,
        cursor: str | None = None,
        sync_interval_minutes: int = 15,
        last_synced_at: datetime | None = None,
        error_message: str | None = None,
        config: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        super().__init__(id or uuid4())
        if kb_id is None:
            raise ValueError("kb_id is required for DataSource")
        self._kb_id = kb_id
        self._name = name.strip()
        if not self._name:
            raise ValueError("name cannot be empty")
        self._data_source_type = data_source_type
        self._status = status
        self._cursor = cursor
        self._sync_interval_minutes = max(1, sync_interval_minutes)
        self._last_synced_at = last_synced_at
        self._error_message = error_message
        self._config = dict(config or {})
        now = datetime.now(UTC)
        self._created_at = created_at or now
        self._updated_at = updated_at or now

    @property
    def kb_id(self) -> UUID:
        return self._kb_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def data_source_type(self) -> DataSourceType:
        return self._data_source_type

    @property
    def status(self) -> DataSourceStatus:
        return self._status

    @property
    def cursor(self) -> str | None:
        return self._cursor

    @property
    def sync_interval_minutes(self) -> int:
        return self._sync_interval_minutes

    @property
    def last_synced_at(self) -> datetime | None:
        return self._last_synced_at

    @property
    def error_message(self) -> str | None:
        return self._error_message

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def start_sync(self) -> None:
        if self._status == DataSourceStatus.SYNCING:
            raise ValueError(f"DataSource {self.id} is already syncing")
        self._status = DataSourceStatus.SYNCING
        self._error_message = None
        self._updated_at = datetime.now(UTC)

    def complete_sync(
        self, new_cursor: str | None = None, synced_at: datetime | None = None
    ) -> None:
        self._status = DataSourceStatus.IDLE
        self._last_synced_at = synced_at or datetime.now(UTC)
        if new_cursor is not None:
            self._cursor = new_cursor
        self._error_message = None
        self._updated_at = datetime.now(UTC)

    def fail_sync(self, error_message: str) -> None:
        self._status = DataSourceStatus.FAILED
        self._error_message = error_message
        self._updated_at = datetime.now(UTC)

    def disable(self) -> None:
        self._status = DataSourceStatus.DISABLED
        self._updated_at = datetime.now(UTC)

    def enable(self) -> None:
        self._status = DataSourceStatus.IDLE
        self._updated_at = datetime.now(UTC)
