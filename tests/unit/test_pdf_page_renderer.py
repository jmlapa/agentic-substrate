import asyncio
import base64
from io import BytesIO

import pypdfium2 as pdfium
import pytest
from PIL import Image

from src.modules.knowledge.infrastructure.adapters.pdf_page_renderer import (
    PdfPageRenderer,
)


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    # Cria um PDF sintético de 3 páginas em memória
    doc = pdfium.PdfDocument.new()
    for _ in range(3):
        doc.new_page(width=200, height=200)
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_get_page_count(sample_pdf_bytes: bytes) -> None:
    renderer = PdfPageRenderer()
    count = await renderer.get_page_count(sample_pdf_bytes)
    assert count == 3


@pytest.mark.asyncio
async def test_render_page_low_res_returns_base64_jpeg(sample_pdf_bytes: bytes) -> None:
    renderer = PdfPageRenderer(low_res_scale=1.0)
    b64_img = await renderer.render_page_low_res(sample_pdf_bytes, page_index=0)
    assert isinstance(b64_img, str)
    raw_img = base64.b64decode(b64_img)
    pil_img = Image.open(BytesIO(raw_img))
    assert pil_img.format == "JPEG"


@pytest.mark.asyncio
async def test_render_page_high_res_returns_higher_resolution(sample_pdf_bytes: bytes) -> None:
    renderer = PdfPageRenderer(low_res_scale=1.0, high_res_scale=2.0)
    low_b64 = await renderer.render_page_low_res(sample_pdf_bytes, page_index=0)
    high_b64 = await renderer.render_page_high_res(sample_pdf_bytes, page_index=0)

    low_img = Image.open(BytesIO(base64.b64decode(low_b64)))
    high_img = Image.open(BytesIO(base64.b64decode(high_b64)))

    assert high_img.width > low_img.width
    assert high_img.height > low_img.height


@pytest.mark.asyncio
async def test_invalid_pdf_raises_error() -> None:
    renderer = PdfPageRenderer()
    with pytest.raises(ValueError, match="invalido"):
        await renderer.get_page_count(b"not a valid pdf content")


@pytest.mark.asyncio
async def test_concurrent_rendering_stress(sample_pdf_bytes: bytes) -> None:
    renderer = PdfPageRenderer()
    # Simula 20 requisições simultâneas de renderização para validar isolamento de threads
    tasks = [renderer.render_page_low_res(sample_pdf_bytes, page_index=i % 3) for i in range(20)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 20
    for res in results:
        assert isinstance(res, str)
        assert len(res) > 0
