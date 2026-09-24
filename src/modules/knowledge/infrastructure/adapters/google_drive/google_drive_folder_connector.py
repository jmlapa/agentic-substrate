import asyncio
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.kernel.application.logger import Logger
from src.modules.knowledge.domain.interfaces.i_data_source_connector import (
    IDataSourceConnector,
)
from src.modules.knowledge.domain.value_objects.data_source_changes_batch import (
    DataSourceChangesBatch,
)
from src.modules.knowledge.domain.value_objects.discovered_document_item import (
    DiscoveredDocumentItem,
)
from src.modules.knowledge.infrastructure.adapters.google_drive.google_drive_http_client import (
    GoogleDriveHttpClient,
)

_standard_logger = logging.getLogger("agentic_substrate.connectors.google_drive")


class GoogleDriveFolderConnector(IDataSourceConnector):
    """
    Adaptador especializado para extração e sincronização de pastas do Google Drive v3
    através de Service Account do GCP.
    """

    def __init__(
        self,
        service_account_info: dict[str, Any] | None = None,
        service_account_path: str | None = None,
        drive_service: Any = None,
        http_client: GoogleDriveHttpClient | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._service_account_info = service_account_info
        self._service_account_path = service_account_path
        self._drive_service = drive_service
        self._http_client = http_client
        self._logger = logger

    def _log_info(self, message: str) -> None:
        if self._logger:
            self._logger.info(message)
        else:
            _standard_logger.info(message)

    def _log_error(self, message: str) -> None:
        if self._logger:
            self._logger.error(message)
        else:
            _standard_logger.error(message)

    def _log_debug(self, message: str) -> None:
        if self._logger:
            self._logger.debug(message)
        else:
            _standard_logger.debug(message)

    def _get_credentials(self) -> Any:
        from google.oauth2 import service_account

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]

        if self._service_account_info:
            return service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
                self._service_account_info, scopes=scopes
            )
        elif self._service_account_path:
            path = Path(self._service_account_path)
            if not path.is_file():
                # Suporte a variações comuns de nomenclatura (hífen vs underscore)
                filename = path.name
                alt_filename = (
                    filename.replace("-", "_") if "-" in filename else filename.replace("_", "-")
                )
                alt_path = path.with_name(alt_filename)
                if alt_path.is_file():
                    self._log_info(
                        f"[GoogleDriveFolderConnector] Caminho '{path}' não encontrado, "
                        f"usando correspondência alternativa: '{alt_path}'"
                    )
                    path = alt_path
                else:
                    raise FileNotFoundError(
                        "Arquivo de credenciais do Google Cloud não encontrado em "
                        f"'{self._service_account_path}'. Certifique-se de que o arquivo "
                        "existe no disco (ou volume montado no container) e que o caminho "
                        "em GOOGLE_APPLICATION_CREDENTIALS está correto."
                    )
            return service_account.Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
                str(path), scopes=scopes
            )
        else:
            # Tenta autenticação padrão do ambiente
            import google.auth

            creds, _ = google.auth.default(scopes=scopes)
            return creds

    def _get_service(self) -> Any:
        if self._drive_service is not None:
            return self._drive_service

        from googleapiclient.discovery import build

        creds = self._get_credentials()
        self._drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._drive_service

    def _get_http_client(self) -> GoogleDriveHttpClient:
        if self._http_client is None:
            creds = self._get_credentials()
            self._http_client = GoogleDriveHttpClient(credentials=creds)
        return self._http_client

    async def fetch_changes(
        self, config: dict[str, Any], cursor: str | None
    ) -> DataSourceChangesBatch:
        folder_id = config.get("folder_id", "").strip()
        if not folder_id:
            raise ValueError("Configuração do Google Drive exige 'folder_id'")

        baseline_days = int(config.get("baseline_days", 30))
        include_mimes: list[str] = config.get("include_mime_types", [])
        recursive: bool = bool(config.get("recursive", True))

        self._log_info(
            f"[GoogleDriveFolderConnector] Iniciando fetch_changes para folder_id='{folder_id}' "
            f"(cursor={'None (Baseline)' if cursor is None else cursor}, recursive={recursive})"
        )

        service = self._get_service()

        if cursor is None:
            return await asyncio.to_thread(
                self._execute_baseline_discovery,
                service,
                folder_id,
                baseline_days,
                include_mimes,
                recursive,
            )
        else:
            return await asyncio.to_thread(
                self._execute_delta_sync,
                service,
                folder_id,
                cursor,
                include_mimes,
            )

    def _execute_baseline_discovery(
        self,
        service: Any,
        folder_id: str,
        baseline_days: int,
        include_mimes: list[str],
        recursive: bool = True,
    ) -> DataSourceChangesBatch:
        cutoff = datetime.now(UTC) - timedelta(days=baseline_days) if baseline_days > 0 else None

        fields = (
            "nextPageToken, files(id, name, mimeType, modifiedTime, size, md5Checksum, "
            "version, shortcutDetails)"
        )

        discovered_items_by_id: dict[str, DiscoveredDocumentItem] = {}
        folders_to_scan: list[str] = [folder_id]
        scanned_folder_ids: set[str] = set()

        while folders_to_scan:
            current_folder_id = folders_to_scan.pop(0)
            if current_folder_id in scanned_folder_ids:
                continue
            scanned_folder_ids.add(current_folder_id)

            query = f"'{current_folder_id}' in parents and trashed = false"
            page_token: str | None = None

            while True:
                response = (
                    service.files()
                    .list(
                        q=query,
                        fields=fields,
                        pageSize=100,
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )

                files = response.get("files", [])
                for f in files:
                    mime = f.get("mimeType", "")
                    if mime == "application/vnd.google-apps.folder":
                        if recursive and f["id"] not in scanned_folder_ids:
                            folders_to_scan.append(f["id"])
                        continue

                    if mime == "application/vnd.google-apps.shortcut":
                        shortcut_details = f.get("shortcutDetails") or {}
                        if (
                            shortcut_details.get("targetMimeType")
                            == "application/vnd.google-apps.folder"
                        ):
                            target_folder_id = shortcut_details.get("targetId")
                            if (
                                recursive
                                and target_folder_id
                                and target_folder_id not in scanned_folder_ids
                            ):
                                folders_to_scan.append(target_folder_id)
                            continue

                    item = self._parse_file_to_item(f, include_mimes)
                    if item:
                        if cutoff and item.modified_time < cutoff:
                            continue
                        if item.external_id not in discovered_items_by_id:
                            discovered_items_by_id[item.external_id] = item

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        # Obtém o startPageToken atual para servir como cursor do próximo delta sync
        start_token_resp = service.changes().getStartPageToken(supportsAllDrives=True).execute()
        next_cursor = start_token_resp.get("startPageToken")

        items_list = list(discovered_items_by_id.values())
        self._log_info(
            f"[GoogleDriveFolderConnector] Baseline concluído: {len(items_list)} arquivos "
            f"encontrados em {len(scanned_folder_ids)} pasta(s). Próximo cursor: '{next_cursor}'"
        )

        return DataSourceChangesBatch(
            items=items_list,
            next_cursor=next_cursor,
            deleted_external_ids=[],
        )

    def _execute_delta_sync(
        self,
        service: Any,
        folder_id: str,
        cursor: str,
        include_mimes: list[str],
    ) -> DataSourceChangesBatch:
        changed_items: list[DiscoveredDocumentItem] = []
        deleted_ids: list[str] = []
        current_token: str | None = cursor
        new_start_token: str | None = None

        while current_token:
            response = (
                service.changes()
                .list(
                    pageToken=current_token,
                    fields=(
                        "nextPageToken, newStartPageToken, "
                        "changes(fileId, removed, file(id, name, mimeType, "
                        "modifiedTime, size, md5Checksum, version, parents, trashed, "
                        "shortcutDetails))"
                    ),
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageSize=100,
                )
                .execute()
            )

            changes = response.get("changes", [])
            for c in changes:
                file_id = c.get("fileId")
                if c.get("removed", False):
                    if file_id:
                        deleted_ids.append(file_id)
                    continue

                f_data = c.get("file")
                if not f_data:
                    continue

                if f_data.get("trashed", False):
                    if file_id:
                        deleted_ids.append(file_id)
                    continue

                parents = f_data.get("parents", [])
                if folder_id not in parents:
                    continue

                item = self._parse_file_to_item(f_data, include_mimes)
                if item:
                    changed_items.append(item)

            new_start_token = response.get("newStartPageToken")
            current_token = response.get("nextPageToken")

        final_cursor = new_start_token or cursor

        self._log_info(
            f"[GoogleDriveFolderConnector] Delta sync concluído: {len(changed_items)} alterados, "
            f"{len(deleted_ids)} excluídos. Novo cursor: '{final_cursor}'"
        )

        return DataSourceChangesBatch(
            items=changed_items,
            next_cursor=final_cursor,
            deleted_external_ids=deleted_ids,
        )

    def _parse_file_to_item(
        self, f: dict[str, Any], include_mimes: list[str]
    ) -> DiscoveredDocumentItem | None:
        mime = f.get("mimeType", "")
        # Ignora pastas filhas na listagem de arquivos
        if mime == "application/vnd.google-apps.folder":
            return None

        effective_id = f["id"]
        effective_mime = mime

        # Resolução de atalhos do Google Drive
        if mime == "application/vnd.google-apps.shortcut":
            shortcut_details = f.get("shortcutDetails") or {}
            target_id = shortcut_details.get("targetId")
            target_mime = shortcut_details.get("targetMimeType")
            if not target_id or target_mime == "application/vnd.google-apps.folder":
                return None
            effective_id = target_id
            effective_mime = target_mime

        if include_mimes and effective_mime not in include_mimes:
            return None

        mtime_str = f.get("modifiedTime")
        if mtime_str:
            try:
                mod_time = datetime.fromisoformat(mtime_str.replace("Z", "+00:00"))
            except Exception:
                mod_time = datetime.now(UTC)
        else:
            mod_time = datetime.now(UTC)

        version_hash = f.get("md5Checksum") or f.get("version") or str(int(mod_time.timestamp()))

        return DiscoveredDocumentItem(
            external_id=effective_id,
            name=f.get("name", effective_id),
            mime_type=effective_mime,
            version_hash=str(version_hash),
            modified_time=mod_time,
            size_bytes=int(f.get("size", 0)),
        )

    async def download_document(self, external_id: str, mime_type: str) -> tuple[bytes, str, str]:
        self._log_info(
            f"[GoogleDriveFolderConnector] Baixando arquivo external_id='{external_id}', "
            f"mime='{mime_type}'"
        )
        http_client = self._get_http_client()
        resolved_mime = mime_type

        # Tratamento de documentos nativos do Google Workspace
        if mime_type == "application/vnd.google-apps.document":
            self._log_debug(
                f"[GoogleDriveFolderConnector] Exportando Google Doc '{external_id}' "
                "para text/plain"
            )
            content = await http_client.export_file(external_id, "text/plain")
            resolved_mime = "text/plain"
        elif mime_type == "application/vnd.google-apps.spreadsheet":
            self._log_debug(
                f"[GoogleDriveFolderConnector] Exportando Google Sheet '{external_id}' "
                "para text/csv"
            )
            content = await http_client.export_file(external_id, "text/csv")
            resolved_mime = "text/csv"
        else:
            content = await http_client.download_file(external_id)

        v_hash = hashlib.sha256(content).hexdigest()
        self._log_info(
            f"[GoogleDriveFolderConnector] Download concluído: external_id='{external_id}' "
            f"({len(content)} bytes, sha256={v_hash[:12]}...)"
        )
        return content, resolved_mime, v_hash

    async def aclose(self) -> None:
        """Fecha o cliente HTTP assíncrono se inicializado."""
        if self._http_client is not None:
            await self._http_client.aclose()
