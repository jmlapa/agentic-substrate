import tempfile
from typing import Any
from uuid import uuid4

import pytest

from src.kernel.domain.result import Err, Ok
from src.kernel.infrastructure.in_memory_event_bus import InMemoryEventBus
from src.kernel.infrastructure.in_memory_event_store import InMemoryEventStore
from src.modules.knowledge.application.sagas.document_ingestion_saga_coordinator import (
    DocumentIngestionSagaCoordinator,
)
from src.modules.knowledge.application.use_cases.attach_and_store_document import (
    AttachAndStoreDocumentRequest,
    AttachAndStoreDocumentUseCase,
)
from src.modules.knowledge.application.use_cases.create_knowledge_base import (
    CreateKnowledgeBaseRequest,
    CreateKnowledgeBaseUseCase,
)
from src.modules.knowledge.application.use_cases.query_knowledge import (
    QueryKnowledgeRequest,
    QueryKnowledgeUseCase,
)
from src.modules.knowledge.domain.ontology import (
    NodeTypeDefinition,
    OntologySchema,
    OntologyTemplate,
    PropertyDefinition,
    PropertyType,
    RelationshipTypeDefinition,
)
from src.modules.knowledge.domain.value_objects.document_status import DocumentStatus
from src.modules.knowledge.infrastructure.adapters.in_memory_graph_and_vector_store import (
    InMemoryGraphAndVectorStore,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_knowledge_base_repository import (
    InMemoryKnowledgeBaseRepository,
)
from src.modules.knowledge.infrastructure.adapters.in_memory_ontology_repository import (
    InMemoryOntologyRepository,
)
from src.modules.knowledge.infrastructure.adapters.local_file_system_storage_adapter import (
    LocalFileSystemStorageAdapter,
)
from src.modules.knowledge.infrastructure.adapters.markitdown_document_parser import (
    MarkItDownDocumentParser,
)
from src.modules.knowledge.infrastructure.extractors.dynamic_ontology_model_builder import (
    DynamicOntologyModelBuilder,
)
from src.modules.knowledge.infrastructure.extractors.structured_pydantic_graph_extractor import (
    StructuredPydanticGraphExtractor,
)


@pytest.fixture
def sample_ontology() -> OntologySchema:
    return OntologySchema(
        name="SoftwareArch",
        description="Ontologia de arquitetura de software",
        node_types=[
            NodeTypeDefinition(
                name="Microservice",
                description="Serviço de backend",
                properties=[
                    PropertyDefinition(
                        name="language",
                        type=PropertyType.STRING,
                        required=True,
                    ),
                    PropertyDefinition(
                        name="port",
                        type=PropertyType.INTEGER,
                        required=False,
                        default=8080,
                    ),
                ],
            ),
            NodeTypeDefinition(
                name="Database",
                description="Banco de dados",
                properties=[
                    PropertyDefinition(
                        name="engine",
                        type=PropertyType.STRING,
                        required=True,
                    )
                ],
            ),
        ],
        relationship_types=[
            RelationshipTypeDefinition(
                name="CONNECTS_TO",
                description="Serviço conecta no banco",
                source_node_type="Microservice",
                target_node_type="Database",
            )
        ],
    )


def test_dynamic_ontology_pydantic_builder(sample_ontology: OntologySchema) -> None:
    builder = DynamicOntologyModelBuilder()
    microservice_def = sample_ontology.get_node_type("Microservice")
    assert microservice_def is not None

    dynamic_model = builder.build_node_model(microservice_def)
    instance: Any = dynamic_model(id="service-auth", language="python", port=8000)
    assert instance.id == "service-auth"
    assert instance.language == "python"
    assert instance.port == 8000

    # Test default fallback
    instance_default: Any = dynamic_model(id="service-billing", language="go")
    assert instance_default.port == 8080


@pytest.mark.asyncio
async def test_full_knowledge_ingestion_saga(sample_ontology: OntologySchema) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        bus = InMemoryEventBus()
        store = InMemoryEventStore(event_bus=bus)
        repo = InMemoryKnowledgeBaseRepository()
        ontology_repo = InMemoryOntologyRepository()
        storage = LocalFileSystemStorageAdapter(base_directory=tmpdir)
        parser = MarkItDownDocumentParser()
        extractor = StructuredPydanticGraphExtractor()
        graph_store = InMemoryGraphAndVectorStore()

        # Coordinator listens to bus
        _ = DocumentIngestionSagaCoordinator(
            event_bus=bus,
            event_store=store,
            kb_repository=repo,
            storage=storage,
            parser=parser,
            extractor=extractor,
            graph_store=graph_store,
            vector_store=graph_store,
        )

        create_kb_use_case = CreateKnowledgeBaseUseCase(
            event_store=store,
            repository=repo,
            ontology_repository=ontology_repo,
        )
        attach_doc_use_case = AttachAndStoreDocumentUseCase(store, repo, storage)
        query_use_case = QueryKnowledgeUseCase(graph_store)

        # 1. Create Knowledge Base
        kb_res = await create_kb_use_case.execute(
            CreateKnowledgeBaseRequest(
                name="ArchKB",
                description="Base de conhecimento de arquitetura",
                ontology=sample_ontology,
            )
        )
        assert isinstance(kb_res, Ok)
        kb_id = kb_res.value.id

        # 2. Attach and Store raw document (triggers Saga)
        raw_doc = b"Document detailing Microservice auth connecting to Database postgres"
        doc_res = await attach_doc_use_case.execute(
            AttachAndStoreDocumentRequest(
                kb_id=kb_id,
                file_name="architecture_overview.txt",
                content_type="text/plain",
                file_content=raw_doc,
            )
        )
        assert isinstance(doc_res, Ok)
        doc_id = doc_res.value.document_id

        # 3. Verify that the Saga completed all steps
        updated_kb = await repo.get_by_id(kb_id)
        assert updated_kb is not None
        doc_info = updated_kb.documents[doc_id]
        assert doc_info["status"] == DocumentStatus.INDEXED
        assert doc_info.get("total_parents", 0) >= 1
        assert doc_info.get("total_children", 0) >= 1

        # 4. Verify vector chunks search
        chunks_res = await graph_store.search_similar_chunks(
            kb_id=kb_id, query_embedding=[0.1] * 768, top_k=5, document_ids=[doc_id]
        )
        assert len(chunks_res) >= 1
        assert chunks_res[0]["document_id"] == doc_id
        assert "Microservice auth" in chunks_res[0]["content"]

        # 5. Verify graph query
        query_res = await query_use_case.execute(
            QueryKnowledgeRequest(kb_id=kb_id, query="What databases are connected?")
        )
        assert isinstance(query_res, Ok)
        assert len(query_res.value.nodes) >= 1


@pytest.mark.asyncio
async def test_create_knowledge_base_with_ontology_template_id(
    sample_ontology: OntologySchema,
) -> None:
    bus = InMemoryEventBus()
    store = InMemoryEventStore(event_bus=bus)
    repo = InMemoryKnowledgeBaseRepository()
    ontology_repo = InMemoryOntologyRepository()

    # 1. Salvar template no repo de ontologia
    template_res = OntologyTemplate.create(
        name=sample_ontology.name,
        description=sample_ontology.description,
        node_types=sample_ontology.node_types,
        relationship_types=sample_ontology.relationship_types,
    )
    assert isinstance(template_res, Ok)
    template = template_res.value
    await ontology_repo.save(template)

    create_kb_use_case = CreateKnowledgeBaseUseCase(
        event_store=store,
        repository=repo,
        ontology_repository=ontology_repo,
    )

    # 2. Criar KB referenciando ontology_id
    kb_res = await create_kb_use_case.execute(
        CreateKnowledgeBaseRequest(
            name="TemplateLinkedKB",
            description="Base vinculada ao template",
            ontology_id=template.id,
        )
    )
    assert isinstance(kb_res, Ok)

    # 3. Tentar criar KB com ontology_id inexistente
    invalid_res = await create_kb_use_case.execute(
        CreateKnowledgeBaseRequest(
            name="InvalidKB",
            description="Teste id invalido",
            ontology_id=uuid4(),
        )
    )
    assert isinstance(invalid_res, Err)
    assert invalid_res.error.code == "ONTOLOGY_TEMPLATE_NOT_FOUND"
