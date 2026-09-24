import asyncio

import httpx
import pytest

from src.modules.knowledge.infrastructure.adapters.google_drive.google_drive_http_client import (
    GoogleDriveHttpClient,
)


class DummyCredentials:
    def __init__(self, token: str = "valid-token", valid: bool = True) -> None:
        self.token = token
        self.valid = valid
        self.refresh_call_count = 0

    def refresh(self, request: object) -> None:
        self.refresh_call_count += 1
        self.valid = True
        self.token = f"refreshed-token-{self.refresh_call_count}"


@pytest.mark.asyncio
async def test_download_file_success() -> None:
    creds = DummyCredentials(token="test-token-123", valid=True)

    def custom_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token-123"
        assert "alt=media" in str(request.url)
        assert "supportsAllDrives=true" in str(request.url)
        assert request.url.path == "/drive/v3/files/file-abc-123"
        return httpx.Response(200, content=b"fake file binary content")

    transport = httpx.MockTransport(custom_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    drive_client = GoogleDriveHttpClient(credentials=creds, client=mock_client)
    try:
        content = await drive_client.download_file("file-abc-123")
        assert content == b"fake file binary content"
    finally:
        await drive_client.aclose()


@pytest.mark.asyncio
async def test_export_file_success() -> None:
    creds = DummyCredentials(token="test-token-export", valid=True)

    def custom_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token-export"
        assert request.url.path == "/drive/v3/files/doc-999/export"
        assert request.url.params["mimeType"] == "text/plain"
        assert request.url.params["supportsAllDrives"] == "true"
        return httpx.Response(200, content=b"Document text exported")

    transport = httpx.MockTransport(custom_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    drive_client = GoogleDriveHttpClient(credentials=creds, client=mock_client)
    try:
        content = await drive_client.export_file("doc-999", "text/plain")
        assert content == b"Document text exported"
    finally:
        await drive_client.aclose()


@pytest.mark.asyncio
async def test_token_refresh_lock_concurrency() -> None:
    creds = DummyCredentials(token="", valid=False)

    def custom_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"].startswith("Bearer refreshed-token-")
        return httpx.Response(200, content=b"content")

    transport = httpx.MockTransport(custom_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    drive_client = GoogleDriveHttpClient(credentials=creds, client=mock_client)
    try:
        # Dispara 10 downloads concorrentes com token inválido
        results = await asyncio.gather(
            *[drive_client.download_file(f"file-{i}") for i in range(10)]
        )
        assert len(results) == 10
        # O lock garante que refresh foi chamado apenas 1 vez, sem chamadas simultâneas
        assert creds.refresh_call_count == 1
    finally:
        await drive_client.aclose()


@pytest.mark.asyncio
async def test_permission_error_mapping() -> None:
    creds = DummyCredentials()

    def custom_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden access")

    transport = httpx.MockTransport(custom_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    drive_client = GoogleDriveHttpClient(credentials=creds, client=mock_client)
    try:
        with pytest.raises(PermissionError) as exc_info:
            await drive_client.download_file("file-secret")
        assert "Falha de acesso ao arquivo 'file-secret' no Google Drive (status 403)" in str(
            exc_info.value
        )
    finally:
        await drive_client.aclose()


@pytest.mark.asyncio
async def test_not_found_error_mapping() -> None:
    creds = DummyCredentials()

    def custom_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(custom_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    drive_client = GoogleDriveHttpClient(credentials=creds, client=mock_client)
    try:
        with pytest.raises(FileNotFoundError) as exc_info:
            await drive_client.download_file("file-missing")
        assert "Arquivo 'file-missing' não encontrado no Google Drive (status 404)" in str(
            exc_info.value
        )
    finally:
        await drive_client.aclose()
