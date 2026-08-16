from src.modules.knowledge.domain.interfaces.i_document_parser import (
    IDocumentParser,
)
from src.modules.knowledge.domain.interfaces.i_graph_extractor import (
    IGraphExtractor,
)
from src.modules.knowledge.domain.interfaces.i_graph_store import IGraphStore
from src.modules.knowledge.domain.interfaces.i_knowledge_base_repository import (
    IKnowledgeBaseRepository,
)
from src.modules.knowledge.domain.interfaces.i_object_storage import IObjectStorage
from src.modules.knowledge.domain.interfaces.i_ontology_repository import (
    IOntologyRepository,
)
from src.modules.knowledge.domain.interfaces.i_vector_store import IVectorStore

__all__ = [
    "IDocumentParser",
    "IGraphExtractor",
    "IGraphStore",
    "IKnowledgeBaseRepository",
    "IObjectStorage",
    "IOntologyRepository",
    "IVectorStore",
]
