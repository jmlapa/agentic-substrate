from datetime import datetime

from src.kernel.domain.value_object import ValueObject


class DiscoveredDocumentItem(ValueObject):
    external_id: str
    name: str
    mime_type: str
    version_hash: str
    modified_time: datetime
    size_bytes: int = 0
