import logging
from typing import Any

from src.modules.knowledge.domain.interfaces.i_document_parser import IDocumentParser
from src.modules.knowledge.domain.value_objects.document_source_type import (
    DocumentSourceType,
)

logger = logging.getLogger(__name__)


class CompositeDocumentParser(IDocumentParser):
    """
    Orquestrador composto (Dispatcher) que inspeciona o arquivo e encaminha
    a chamada para o parser especializado correspondente (documentos, imagens/OCR ou áudios).
    """

    def __init__(
        self,
        document_parser: IDocumentParser,
        image_parser: IDocumentParser | None = None,
        audio_parser: IDocumentParser | None = None,
    ) -> None:
        self._document_parser = document_parser
        self._image_parser = image_parser
        self._audio_parser = audio_parser

    async def parse_to_markdown(
        self,
        raw_bytes: bytes,
        file_name: str,
        content_type: str,
        enable_ocr: bool = False,
        ocr_instructions: str | None = None,
        doc_id: Any = None,
        kb_partition: str | None = None,
        progress_callback: Any = None,
        ingested_at: float | None = None,
    ) -> str:
        source_type = DocumentSourceType.infer(file_name=file_name, content_type=content_type)

        if source_type == DocumentSourceType.IMAGE:
            if self._image_parser is not None:
                return await self._image_parser.parse_to_markdown(
                    raw_bytes=raw_bytes,
                    file_name=file_name,
                    content_type=content_type,
                    enable_ocr=enable_ocr,
                    ocr_instructions=ocr_instructions,
                    doc_id=doc_id,
                    kb_partition=kb_partition,
                    progress_callback=progress_callback,
                    ingested_at=ingested_at,
                )
            logger.warning(
                "No image parser configured, falling back to document parser for %s", file_name
            )

        elif source_type == DocumentSourceType.AUDIO:
            if self._audio_parser is not None:
                return await self._audio_parser.parse_to_markdown(
                    raw_bytes=raw_bytes,
                    file_name=file_name,
                    content_type=content_type,
                    enable_ocr=enable_ocr,
                    ocr_instructions=ocr_instructions,
                    doc_id=doc_id,
                    kb_partition=kb_partition,
                    progress_callback=progress_callback,
                    ingested_at=ingested_at,
                )
            logger.warning(
                "No audio parser configured, falling back to document parser for %s", file_name
            )

        return await self._document_parser.parse_to_markdown(
            raw_bytes=raw_bytes,
            file_name=file_name,
            content_type=content_type,
            enable_ocr=enable_ocr,
            ocr_instructions=ocr_instructions,
            doc_id=doc_id,
            kb_partition=kb_partition,
            progress_callback=progress_callback,
            ingested_at=ingested_at,
        )
