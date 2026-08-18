from pathlib import Path

import aiofiles

from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage


class LocalFileSystemStorageAdapter(IObjectStorage):
    def __init__(self, base_directory: str = "./data/storage") -> None:
        self._base_directory = Path(base_directory).resolve()
        self._base_directory.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: str) -> Path:
        clean_path = path.lstrip("/")
        resolved = (self._base_directory / clean_path).resolve()
        if not str(resolved).startswith(str(self._base_directory)):
            raise ValueError(f"Path traversal detected: {path}")
        return resolved

    async def put_object(self, path: str, content: bytes, content_type: str) -> None:
        target_path = self._resolve_path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)

    async def get_object(self, path: str) -> bytes:
        target_path = self._resolve_path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"Object not found at path: {path}")
        async with aiofiles.open(target_path, "rb") as f:
            return await f.read()

    async def exists(self, path: str) -> bool:
        target_path = self._resolve_path(path)
        return target_path.exists()

    async def list_objects(self, prefix: str) -> list[str]:
        target_dir = self._resolve_path(prefix)
        if not target_dir.exists():
            return []
        if target_dir.is_file():
            rel = target_dir.relative_to(self._base_directory).as_posix()
            return [rel]
        results: list[str] = []
        for p in target_dir.rglob("*"):
            if p.is_file():
                results.append(p.relative_to(self._base_directory).as_posix())
        return results

    async def generate_upload_url(self, path: str) -> str:
        target_path = self._resolve_path(path)
        return target_path.as_uri()
