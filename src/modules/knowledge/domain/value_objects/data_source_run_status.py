from enum import StrEnum


class DataSourceRunStatus(StrEnum):
    EXTRACTING = "EXTRACTING"
    INGESTING = "INGESTING"
    COMPLETED = "COMPLETED"
    PARTIALLY_FAILED = "PARTIALLY_FAILED"
    FAILED = "FAILED"
