from enum import StrEnum


class DataSourceStatus(StrEnum):
    IDLE = "IDLE"
    SYNCING = "SYNCING"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
