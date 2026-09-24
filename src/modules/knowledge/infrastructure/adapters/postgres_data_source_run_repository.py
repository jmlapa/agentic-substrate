import json
from uuid import UUID

import asyncpg

from src.modules.knowledge.domain.entities.data_source_run import DataSourceRun
from src.modules.knowledge.domain.interfaces.i_data_source_run_repository import (
    IDataSourceRunRepository,
)
from src.modules.knowledge.domain.value_objects.data_source_run_status import (
    DataSourceRunStatus,
)


class PostgresDataSourceRunRepository(IDataSourceRunRepository):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def save(self, run: DataSourceRun) -> None:
        query = """
        INSERT INTO knowledge_data_source_runs (
            id, data_source_id, kb_id, status, total_files_discovered,
            indexed_files_count, failed_files_count, failure_summary,
            started_at, completed_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10
        )
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            total_files_discovered = EXCLUDED.total_files_discovered,
            indexed_files_count = EXCLUDED.indexed_files_count,
            failed_files_count = EXCLUDED.failed_files_count,
            failure_summary = EXCLUDED.failure_summary,
            completed_at = EXCLUDED.completed_at;
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                run.id,
                run.data_source_id,
                run.kb_id,
                str(run.status),
                run.total_files_discovered,
                run.indexed_files_count,
                run.failed_files_count,
                json.dumps(run.failure_summary),
                run.started_at,
                run.completed_at,
            )

    async def get_by_id(self, run_id: UUID) -> DataSourceRun | None:
        query = """
        SELECT id, data_source_id, kb_id, status, total_files_discovered,
               indexed_files_count, failed_files_count, failure_summary,
               started_at, completed_at
        FROM knowledge_data_source_runs
        WHERE id = $1;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, run_id)
            if not row:
                return None
            return self._map_row_to_entity(row)

    async def list_by_data_source_id(
        self, data_source_id: UUID, limit: int = 50
    ) -> list[DataSourceRun]:
        query = """
        SELECT id, data_source_id, kb_id, status, total_files_discovered,
               indexed_files_count, failed_files_count, failure_summary,
               started_at, completed_at
        FROM knowledge_data_source_runs
        WHERE data_source_id = $1
        ORDER BY started_at DESC
        LIMIT $2;
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, data_source_id, limit)
            return [self._map_row_to_entity(r) for r in rows]

    async def record_document_indexed(
        self, run_id: UUID
    ) -> tuple[UUID, UUID, int, int, int, str] | None:
        query = """
        UPDATE knowledge_data_source_runs
        SET indexed_files_count = indexed_files_count + 1,
            status = CASE 
                WHEN total_files_discovered > 0 
                     AND indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN
                    CASE WHEN failed_files_count > 0 THEN 'PARTIALLY_FAILED' ELSE 'COMPLETED' END
                ELSE status 
            END,
            completed_at = CASE 
                WHEN total_files_discovered > 0 
                     AND indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN
                    NOW()
                ELSE completed_at 
            END
        WHERE id = $1 AND status NOT IN ('COMPLETED', 'PARTIALLY_FAILED', 'FAILED')
        RETURNING 
            data_source_id, kb_id, indexed_files_count, failed_files_count, 
            total_files_discovered, status;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, run_id)
            if not row:
                return None
            return (
                row["data_source_id"],
                row["kb_id"],
                row["indexed_files_count"],
                row["failed_files_count"],
                row["total_files_discovered"],
                str(row["status"]),
            )

    async def record_document_failed(
        self, run_id: UUID, failure_item: dict[str, object]
    ) -> tuple[UUID, UUID, int, int, int, str] | None:
        query = """
        UPDATE knowledge_data_source_runs
        SET failed_files_count = failed_files_count + 1,
            failure_summary = (
                COALESCE(failure_summary, '[]'::jsonb) || jsonb_build_array($2::jsonb)
            ),
            status = CASE 
                WHEN total_files_discovered > 0 
                     AND indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN
                    CASE WHEN indexed_files_count > 0 THEN 'PARTIALLY_FAILED' ELSE 'FAILED' END
                ELSE status 
            END,
            completed_at = CASE 
                WHEN total_files_discovered > 0 
                     AND indexed_files_count + failed_files_count + 1 >= total_files_discovered THEN
                    NOW()
                ELSE completed_at 
            END
        WHERE id = $1 AND status NOT IN ('COMPLETED', 'PARTIALLY_FAILED', 'FAILED')
        RETURNING 
            data_source_id, kb_id, indexed_files_count, failed_files_count, 
            total_files_discovered, status;
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, run_id, json.dumps(failure_item))
            if not row:
                return None
            return (
                row["data_source_id"],
                row["kb_id"],
                row["indexed_files_count"],
                row["failed_files_count"],
                row["total_files_discovered"],
                str(row["status"]),
            )

    def _map_row_to_entity(self, row: asyncpg.Record) -> DataSourceRun:
        raw_summary = row["failure_summary"]
        summary_list = (
            json.loads(raw_summary) if isinstance(raw_summary, str) else list(raw_summary or [])
        )
        return DataSourceRun(
            id=row["id"],
            data_source_id=row["data_source_id"],
            kb_id=row["kb_id"],
            status=DataSourceRunStatus(row["status"]),
            total_files_discovered=row["total_files_discovered"],
            indexed_files_count=row["indexed_files_count"],
            failed_files_count=row["failed_files_count"],
            failure_summary=summary_list,
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
