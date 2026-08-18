from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api_gateway.container import AppContainer
from src.api_gateway.main import create_app
from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.reprocess_document import (
    ReprocessDocumentResponse,
)


@pytest.mark.asyncio
async def test_reprocess_document_endpoint() -> None:
    mock_container = MagicMock(spec=AppContainer)
    mock_reprocess = AsyncMock()
    mock_container.reprocess_document_use_case = mock_reprocess

    kb_id = uuid4()
    doc_id = uuid4()

    mock_reprocess.execute.return_value = Ok(
        ReprocessDocumentResponse(
            document_id=doc_id,
            status="UPLOADED",
            message="Saga reiniciada com sucesso a partir dos checkpoints existentes.",
        )
    )

    app = create_app(container=mock_container)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.post(f"/api/v1/knowledge/bases/{kb_id}/documents/{doc_id}/reprocess")
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == str(doc_id)
        assert data["status"] == "UPLOADED"
        assert "Saga reiniciada" in data["message"]
