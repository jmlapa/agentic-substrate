from src.kernel.domain.domain_error import DomainError
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class InMemoryObjectStorage(IObjectStorage):
    def __init__(self) -> None:
        self._files: dict[str, tuple[bytes, str]] = {}

    async def put_object(self, path: str, content: bytes, content_type: str) -> None:
        self._files[path] = (content, content_type)

    async def get_object(self, path: str) -> bytes:
        if path not in self._files:
            raise DomainError(f"File not found in storage: {path}", code="FILE_NOT_FOUND")
        return self._files[path][0]

    async def generate_upload_url(self, path: str) -> str:
        return f"http://mock-storage.local/{path}?token=mock-signature"
