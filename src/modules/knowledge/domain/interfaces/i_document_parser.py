from typing import Protocol, runtime_checkable


@runtime_checkable
class IDocumentParser(Protocol):
    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
    ) -> str: ...
