import asyncio
from typing import Any

import httpx


class GoogleDriveHttpClient:
    """Cliente HTTP assíncrono nativo para a API v3 do Google Drive via httpx.

    Elimina o uso de bibliotecas síncronas/thread-unsafe (como httplib2) para downloads,
    garantindo isolamento de conexões TLS e renovação coroutine-safe de tokens OAuth2.
    """

    def __init__(
        self,
        credentials: Any,
        client: httpx.AsyncClient | None = None,
        base_url: str = "https://www.googleapis.com/drive/v3",
    ) -> None:
        self._credentials = credentials
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._refresh_lock = asyncio.Lock()
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=60.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
            self._owns_client = True
        return self._client

    async def _get_access_token(self) -> str:
        async with self._refresh_lock:
            # Verifica se o token precisa ser atualizado
            is_valid = getattr(self._credentials, "valid", False)
            if not is_valid:
                from google.auth.transport.requests import Request as GoogleAuthRequest

                # Refresh síncrono do google-auth: despacha em thread separada
                await asyncio.to_thread(self._credentials.refresh, GoogleAuthRequest())

            token: str = str(getattr(self._credentials, "token", ""))
            return token

    async def download_file(self, file_id: str) -> bytes:
        """Baixa o conteúdo binário bruto de um arquivo no Google Drive."""
        client = await self._get_client()
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}/files/{file_id}"
        params = {"alt": "media", "supportsAllDrives": "true"}

        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e, file_id)
            raise

    async def export_file(self, file_id: str, mime_type: str) -> bytes:
        """Exporta um documento nativo do Google Workspace para o MIME type solicitado."""
        client = await self._get_client()
        token = await self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._base_url}/files/{file_id}/export"
        params = {"mimeType": mime_type, "supportsAllDrives": "true"}

        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            self._handle_http_error(e, file_id)
            raise

    def _handle_http_error(self, e: httpx.HTTPStatusError, file_id: str) -> None:
        status = e.response.status_code
        if status in (403, 401):
            raise PermissionError(
                f"Falha de acesso ao arquivo '{file_id}' no Google Drive (status {status}). "
                "Se este arquivo for proveniente de um atalho ou pasta compartilhada (como "
                "reuniões gravadas ou notas do Meet/Gemini), certifique-se de que o arquivo "
                "original ou sua pasta de origem foi compartilhado com a Service Account "
                "com permissão de Leitor."
            ) from e
        elif status == 404:
            raise FileNotFoundError(
                f"Arquivo '{file_id}' não encontrado no Google Drive (status 404)."
            ) from e

    async def aclose(self) -> None:
        """Fecha a sessão HTTP assíncrona se criada internamente."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
