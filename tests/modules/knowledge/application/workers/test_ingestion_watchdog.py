import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.kernel.domain.domain_error import DomainError
from src.kernel.domain.result import Err, Ok
from src.modules.knowledge.application.use_cases.reprocess_document.reprocess_document_response import (  # noqa: E501
    ReprocessDocumentResponse,
)
from src.modules.knowledge.application.use_cases.reprocess_document.reprocess_document_use_case import (  # noqa: E501
    ReprocessDocumentUseCase,
)
from src.modules.knowledge.application.workers.ingestion_watchdog import IngestionWatchdog


@pytest.mark.asyncio
async def test_watchdog_recovers_stale_document_successfully() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    doc_id = uuid4()
    kb_id = uuid4()
    old_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)

    # 1. select_query retorna 1 documento estagnado
    mock_conn.fetch.return_value = [
        {
            "id": doc_id,
            "kb_id": kb_id,
            "status": "CHUNKED",
            "updated_at": old_time,
            "recovery_attempt": 0,
        }
    ]

    # 2. lease_query adquire com sucesso
    mock_conn.fetchrow.return_value = {"id": doc_id}

    # 3. reprocess_use_case mock
    reprocess_mock = MagicMock(spec=ReprocessDocumentUseCase)
    reprocess_mock.execute = AsyncMock(
        return_value=Ok(
            ReprocessDocumentResponse(
                document_id=doc_id,
                status="UPLOADED",
                message="Retomado com sucesso",
            )
        )
    )

    watchdog = IngestionWatchdog(
        pool=mock_pool,
        reprocess_use_case=reprocess_mock,
        threshold_minutes=10,
        max_attempts=3,
    )

    recovered = await watchdog.check_and_recover_stale_documents()

    assert recovered == [doc_id]
    reprocess_mock.execute.assert_awaited_once()
    mock_conn.fetchrow.assert_awaited_once()


@pytest.mark.asyncio
async def test_watchdog_skips_when_lease_not_acquired() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    doc_id = uuid4()
    kb_id = uuid4()
    old_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)

    mock_conn.fetch.return_value = [
        {
            "id": doc_id,
            "kb_id": kb_id,
            "status": "UPLOADED",
            "updated_at": old_time,
            "recovery_attempt": 0,
        }
    ]

    # Simula que outra instância adquiriu o lease primeiro (retorna None)
    mock_conn.fetchrow.return_value = None

    reprocess_mock = MagicMock(spec=ReprocessDocumentUseCase)
    reprocess_mock.execute = AsyncMock()

    watchdog = IngestionWatchdog(
        pool=mock_pool,
        reprocess_use_case=reprocess_mock,
        threshold_minutes=10,
    )

    recovered = await watchdog.check_and_recover_stale_documents()

    # Zero documentos recuperados e use_case não foi chamado (zero duplicação!)
    assert recovered == []
    reprocess_mock.execute.assert_not_called()


@pytest.mark.asyncio
async def test_watchdog_marks_failed_on_max_attempts_exhausted() -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    doc_id = uuid4()
    kb_id = uuid4()
    old_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=20)

    # Documento já na 2ª tentativa (tentativa atual será 3, que atinge max_attempts=3)
    mock_conn.fetch.return_value = [
        {
            "id": doc_id,
            "kb_id": kb_id,
            "status": "PARSED",
            "updated_at": old_time,
            "recovery_attempt": 2,
        }
    ]

    mock_conn.fetchrow.return_value = {"id": doc_id}

    reprocess_mock = MagicMock(spec=ReprocessDocumentUseCase)
    reprocess_mock.execute = AsyncMock(
        return_value=Err(DomainError("Arquivo corrompido irreparável", code="CORRUPT_FILE"))
    )

    watchdog = IngestionWatchdog(
        pool=mock_pool,
        reprocess_use_case=reprocess_mock,
        max_attempts=3,
        threshold_minutes=10,
    )

    recovered = await watchdog.check_and_recover_stale_documents()

    assert recovered == []
    # Verifica que marcou como FAILED após estourar as tentativas
    assert mock_conn.execute.called
    update_call_sql = mock_conn.execute.call_args[0][0]
    assert "UPDATE attached_documents" in update_call_sql
    assert "SET status = 'FAILED'" in update_call_sql
