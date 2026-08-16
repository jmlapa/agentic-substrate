from src.kernel.domain.domain_event import DomainEvent
from src.modules.knowledge.domain.ontology.ontology_schema import OntologySchema


class KnowledgeBaseCreatedEvent(DomainEvent):
    name: str
    description: str
    ontology: OntologySchema
    storage_partition: str
