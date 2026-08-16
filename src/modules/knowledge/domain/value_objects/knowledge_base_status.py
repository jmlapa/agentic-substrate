from enum import StrEnum


class KnowledgeBaseStatus(StrEnum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
