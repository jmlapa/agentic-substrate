from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.knowledge.infrastructure.adapters.google_drive import (
    GoogleDriveFolderConnector,
)


@pytest.mark.asyncio
async def test_fetch_changes_validation_error_without_folder_id() -> None:
    connector = GoogleDriveFolderConnector()
    with pytest.raises(ValueError, match="folder_id"):
        await connector.fetch_changes(config={}, cursor=None)


@pytest.mark.asyncio
async def test_fetch_changes_baseline_discovery() -> None:
    mock_service = MagicMock()
    connector = GoogleDriveFolderConnector(drive_service=mock_service)

    # Mock files().list().execute()
    mock_files_list_request = MagicMock()
    mock_files_list_request.execute.return_value = {
        "files": [
            {
                "id": "doc-1",
                "name": "Report.pdf",
                "mimeType": "application/pdf",
                "modifiedTime": "2026-09-20T10:00:00Z",
                "size": "1024",
                "md5Checksum": "hash-1",
            },
            {
                "id": "subfolder-1",
                "name": "Subfolder",
                "mimeType": "application/vnd.google-apps.folder",
            },
        ],
        "nextPageToken": None,
    }
    mock_service.files().list.return_value = mock_files_list_request

    # Mock changes().getStartPageToken().execute()
    mock_start_token_request = MagicMock()
    mock_start_token_request.execute.return_value = {"startPageToken": "token-123"}
    mock_service.changes().getStartPageToken.return_value = mock_start_token_request

    batch = await connector.fetch_changes(
        config={"folder_id": "root-folder-123", "baseline_days": 30},
        cursor=None,
    )

    assert len(batch.items) == 1
    assert batch.items[0].external_id == "doc-1"
    assert batch.items[0].name == "Report.pdf"
    assert batch.items[0].mime_type == "application/pdf"
    assert batch.items[0].version_hash == "hash-1"
    assert batch.items[0].size_bytes == 1024
    assert batch.next_cursor == "token-123"
    assert batch.deleted_external_ids == []


@pytest.mark.asyncio
async def test_fetch_changes_delta_sync() -> None:
    mock_service = MagicMock()
    connector = GoogleDriveFolderConnector(drive_service=mock_service)

    # Mock changes().list().execute()
    mock_changes_request = MagicMock()
    mock_changes_request.execute.return_value = {
        "changes": [
            {
                "fileId": "doc-updated",
                "removed": False,
                "file": {
                    "id": "doc-updated",
                    "name": "Notes.gdoc",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": "2026-09-21T12:00:00Z",
                    "version": "v2",
                    "parents": ["root-folder-123"],
                    "trashed": False,
                },
            },
            {
                "fileId": "doc-other-folder",
                "removed": False,
                "file": {
                    "id": "doc-other-folder",
                    "parents": ["other-folder-456"],
                },
            },
            {
                "fileId": "doc-deleted",
                "removed": True,
            },
        ],
        "nextPageToken": None,
        "newStartPageToken": "token-456",
    }
    mock_service.changes().list.return_value = mock_changes_request

    batch = await connector.fetch_changes(
        config={"folder_id": "root-folder-123"},
        cursor="token-123",
    )

    assert len(batch.items) == 1
    assert batch.items[0].external_id == "doc-updated"
    assert batch.items[0].name == "Notes.gdoc"
    assert batch.next_cursor == "token-456"
    assert "doc-deleted" in batch.deleted_external_ids


@pytest.mark.asyncio
async def test_download_document_regular_binary() -> None:
    mock_service = MagicMock()
    connector = GoogleDriveFolderConnector(drive_service=mock_service)

    fake_content = b"PDF binary content"

    def fake_downloader_init(fh: MagicMock, req: MagicMock) -> MagicMock:
        downloader = MagicMock()

        def next_chunk() -> tuple[MagicMock, bool]:
            fh.write(fake_content)
            return (MagicMock(), True)

        downloader.next_chunk = next_chunk
        return downloader

    with patch(
        "googleapiclient.http.MediaIoBaseDownload",
        side_effect=fake_downloader_init,
    ):
        content, mime, v_hash = await connector.download_document(
            external_id="file-1",
            mime_type="application/pdf",
        )

    assert content == fake_content
    assert mime == "application/pdf"
    assert len(v_hash) == 64  # sha256 hex string


@pytest.mark.asyncio
async def test_download_document_google_doc_export() -> None:
    mock_service = MagicMock()
    connector = GoogleDriveFolderConnector(drive_service=mock_service)

    fake_content = b"PlainText representation of Google Doc"

    def fake_downloader_init(fh: MagicMock, req: MagicMock) -> MagicMock:
        downloader = MagicMock()

        def next_chunk() -> tuple[MagicMock, bool]:
            fh.write(fake_content)
            return (MagicMock(), True)

        downloader.next_chunk = next_chunk
        return downloader

    with patch(
        "googleapiclient.http.MediaIoBaseDownload",
        side_effect=fake_downloader_init,
    ):
        content, mime, v_hash = await connector.download_document(
            external_id="gdoc-1",
            mime_type="application/vnd.google-apps.document",
        )

    assert content == fake_content
    assert mime == "text/plain"
    assert len(v_hash) == 64
    mock_service.files().export_media.assert_called_with(fileId="gdoc-1", mimeType="text/plain")


def test_get_service_raises_clear_error_when_service_account_path_not_found(tmp_path: Path) -> None:
    missing_file = tmp_path / "non_existent_credentials.json"
    connector = GoogleDriveFolderConnector(service_account_path=str(missing_file))
    with pytest.raises(
        FileNotFoundError, match="Arquivo de credenciais do Google Cloud não encontrado"
    ):
        connector._get_service()


def test_get_service_resolves_alternative_hyphen_underscore_filename(tmp_path: Path) -> None:
    # File created with underscores on disk
    real_file = tmp_path / "google_application_credentials.json"
    real_file.write_text("{}", encoding="utf-8")

    # Configured path uses hyphens
    configured_path = tmp_path / "google-application-credentials.json"
    connector = GoogleDriveFolderConnector(service_account_path=str(configured_path))

    with (
        patch(
            "google.oauth2.service_account.Credentials.from_service_account_file"
        ) as mock_from_file,
        patch("googleapiclient.discovery.build") as mock_build,
    ):
        mock_creds = MagicMock()
        mock_from_file.return_value = mock_creds
        mock_build.return_value = MagicMock()

        connector._get_service()

        mock_from_file.assert_called_once_with(
            str(real_file), scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
