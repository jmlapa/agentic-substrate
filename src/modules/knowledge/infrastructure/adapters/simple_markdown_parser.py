from src.modules.knowledge.domain.interfaces.i_document_parser import (
    IDocumentParser,
)


class SimpleMarkdownParser(IDocumentParser):
    async def parse_to_markdown(self, raw_bytes: bytes, file_name: str, content_type: str) -> str:
        text = raw_bytes.decode("utf-8", errors="replace")
        return f"# {file_name}\n\n{text}"
