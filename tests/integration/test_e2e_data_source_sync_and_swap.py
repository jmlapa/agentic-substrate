import pytest

from src.api_gateway.container import create_app_container
from src.kernel.domain.result import Ok
from src.modules.knowledge.application.use_cases.create_data_source import (
    CreateDataSourceRequest,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseRequest,
)
from src.modules.knowledge.application.use_cases.list_data_source_runs import (
    ListDataSourceRunsRequest,
)
from src.modules.knowledge.application.use_cases.sync_data_source import (
    SyncDataSourceRequest,
)
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema
from src.modules.knowledge.domain.value_objects.data_source_type import (
    DataSourceType,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_data_source_connector import (
    InMemoryDataSourceConnector,
)


@pytest.mark.asyncio
async def test_e2e_data_source_sync_and_blue_green_swap() -> None:
    # 1. Initialize full app container with synchronous execution for deterministic assertions
    container = create_app_container(run_in_background=False)

    # 2. Create Knowledge Base
    kb_res = await container.create_kb_use_case.execute(
        CreateKnowledgeBaseRequest(
            name="E2E Swap Test KB",
            description="Knowledge base to validate blue/green document version swaps",
            ontology=OntologySchema(
                name="SwapTestOntology",
                description="Minimal ontology for testing",
                node_types=[],
                relationship_types=[],
            ),
        )
    )
    assert isinstance(kb_res, Ok), f"Failed to create KB: {kb_res}"
    kb_id = kb_res.value.id

    # 3. Register mock connector
    mock_connector = InMemoryDataSourceConnector()
    mock_connector.add_mock_file(
        external_id="ext-file-100",
        name="security_policy.txt",
        content=b"Security Policy V1: All employees must use complex passwords and MFA.",
        mime_type="text/plain",
        version_hash="v1_sha256_mock",
    )
    assert container.data_source_connector_registry is not None
    container.data_source_connector_registry.register(
        DataSourceType.GOOGLE_DRIVE_FOLDER, mock_connector
    )

    # 4. Create DataSource
    assert container.create_data_source_use_case is not None
    ds_res = await container.create_data_source_use_case.execute(
        CreateDataSourceRequest(
            kb_id=kb_id,
            name="Google Drive Security Policies",
            data_source_type=DataSourceType.GOOGLE_DRIVE_FOLDER,
            config={"folder_id": "google_drive_folder_sec_01"},
            sync_interval_minutes=15,
        )
    )
    assert isinstance(ds_res, Ok), f"Failed to create DataSource: {ds_res}"
    ds_id = ds_res.value.id

    # 5. First Sync: Ingest Document Version 1
    assert container.sync_data_source_use_case is not None
    sync1_res = await container.sync_data_source_use_case.execute(
        SyncDataSourceRequest(data_source_id=ds_id)
    )
    assert isinstance(sync1_res, Ok), f"First sync failed: {sync1_res}"
    assert sync1_res.value.total_items_discovered == 1
    run1_id = sync1_res.value.sync_run_id

    # Verify Knowledge Base documents after Sync 1
    kb_v1 = await container.kb_repository.get_by_id(kb_id)
    assert kb_v1 is not None
    assert len(kb_v1.documents) == 1
    doc_v1_id = list(kb_v1.documents.keys())[0]
    assert kb_v1.documents[doc_v1_id]["file_name"] == "security_policy.txt"

    # Verify Run 1 completed successfully via projector
    assert container.data_source_run_repository is not None
    run1 = await container.data_source_run_repository.get_by_id(run1_id)
    assert run1 is not None
    assert run1.status.value == "COMPLETED"
    assert run1.total_files_discovered == 1
    assert run1.indexed_files_count == 1
    assert run1.failed_files_count == 0

    # 6. Simulate File Update in Google Drive (Version 2)
    mock_connector.mock_items.clear()
    mock_connector.add_mock_file(
        external_id="ext-file-100",
        name="security_policy.txt",
        content=b"Security Policy V2: Passwords deprecated. Passkeys and FIDO2 keys mandatory.",
        mime_type="text/plain",
        version_hash="v2_sha256_mock_updated",
    )

    # 7. Second Sync: Ingest Document Version 2 and trigger Blue/Green Swap
    assert container.sync_data_source_use_case is not None
    sync2_res = await container.sync_data_source_use_case.execute(
        SyncDataSourceRequest(data_source_id=ds_id)
    )
    assert isinstance(sync2_res, Ok), f"Second sync failed: {sync2_res}"
    assert sync2_res.value.total_items_discovered == 1
    run2_id = sync2_res.value.sync_run_id

    # 8. Assertions on Blue/Green Swap outcome
    kb_v2 = await container.kb_repository.get_by_id(kb_id)
    assert kb_v2 is not None

    # Version 1 must have been purged atomically by BlueGreenDocumentSwapHandler
    assert doc_v1_id not in kb_v2.documents, (
        f"Old doc {doc_v1_id} should have been deleted by Blue/Green swap"
    )

    # Only Version 2 must be present in the Knowledge Base
    assert len(kb_v2.documents) == 1
    doc_v2_id = list(kb_v2.documents.keys())[0]
    assert doc_v2_id != doc_v1_id
    assert kb_v2.documents[doc_v2_id]["file_name"] == "security_policy.txt"

    # Verify Run 2 completed successfully
    assert container.data_source_run_repository is not None
    run2 = await container.data_source_run_repository.get_by_id(run2_id)
    assert run2 is not None
    assert run2.status.value == "COMPLETED"
    assert run2.total_files_discovered == 1
    assert run2.indexed_files_count == 1
    assert run2.failed_files_count == 0

    # Verify Run history list via use case
    assert container.list_data_source_runs_use_case is not None
    runs_res = await container.list_data_source_runs_use_case.execute(
        ListDataSourceRunsRequest(data_source_id=ds_id, limit=10)
    )
    assert isinstance(runs_res, Ok)
    assert len(runs_res.value.runs) == 2
