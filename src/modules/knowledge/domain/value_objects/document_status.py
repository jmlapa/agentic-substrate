from enum import StrEnum


class DocumentStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    GRAPH_EXTRACTED = "GRAPH_EXTRACTED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
