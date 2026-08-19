export type PropertyType = 'string' | 'integer' | 'float' | 'boolean' | 'date' | 'list';

export interface PropertyDefinition {
  name: string;
  type: PropertyType;
  required: boolean;
  default?: string | number | boolean | null;
  description?: string;
}

export interface NodeTypeDefinition {
  name: string;
  description: string;
  properties: PropertyDefinition[];
}

export interface RelationshipTypeDefinition {
  name: string;
  source_node_type: string;
  target_node_type: string;
  description: string;
  properties: PropertyDefinition[];
}

export interface OntologySchema {
  name: string;
  description: string;
  node_types: NodeTypeDefinition[];
  relationship_types: RelationshipTypeDefinition[];
}

export interface OntologyTemplate {
  id: string;
  name: string;
  description: string;
  node_types: NodeTypeDefinition[];
  relationship_types: RelationshipTypeDefinition[];
  version: number;
}

export interface CreateOntologyTemplateDTO {
  name: string;
  description: string;
  node_types: NodeTypeDefinition[];
  relationship_types: RelationshipTypeDefinition[];
  version?: number;
}

export interface ListOntologyTemplatesResponse {
  templates: OntologyTemplate[];
}

export interface KnowledgeBaseSummary {
  id: string;
  name: string;
  description: string;
  status: string;
  storage_partition: string;
  documents_count: number;
}

export interface ListKnowledgeBasesResponse {
  knowledge_bases: KnowledgeBaseSummary[];
}

export type DocumentProcessingStatus =
  | 'PENDING_UPLOAD'
  | 'UPLOADED'
  | 'PARSED'
  | 'CHUNKED'
  | 'EMBEDDED'
  | 'GRAPH_EXTRACTED'
  | 'INDEXED'
  | 'FAILED';

export interface DocumentProcessingError {
  step?: string;
  message?: string;
}

export interface DocumentSummary {
  id: string;
  file_name: string;
  status: DocumentProcessingStatus | string;
  enable_ocr?: boolean;
  ocr_instructions?: string | null;
  total_parents?: number | null;
  total_children?: number | null;
  indexed_nodes_count?: number;
  indexed_edges_count?: number;
  progress_step?: string | null;
  progress_current?: number;
  progress_total?: number;
  progress_percentage?: number;
  progress_message?: string | null;
  error?: DocumentProcessingError | null;
}

export interface ReprocessDocumentResponse {
  document_id: string;
  status: string;
  message: string;
}

export interface KnowledgeBaseDetail {
  id: string;
  name: string;
  description: string;
  status: string;
  storage_partition: string;
  ontology?: OntologySchema | null;
  documents: DocumentSummary[];
}

export interface CreateKnowledgeBaseDTO {
  name: string;
  description: string;
  ontology_id?: string | null;
  ontology?: OntologySchema | null;
}

export interface CreateKnowledgeBaseResponse {
  id: string;
  name: string;
  status: string;
  storage_partition: string;
}

export interface UploadDocumentOptions {
  enableOcr?: boolean;
  ocrInstructions?: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  storage_path: string;
  status: string;
}

export interface HybridSearchResult {
  parent_chunk_id: string;
  header_path: string;
  parent_content: string;
  relevance_score: number;
  related_entities: Record<string, unknown>[];
}

export interface RetrievalTrace {
  candidate_k?: number;
  top_k?: number;
  mode?: string;
  token_budget_limit?: number;
  token_budget_consumed?: number;
  budget_truncated?: boolean;
  results_count?: number;
  synthesis_error?: boolean;
  retrieval_sources?: string[];
  [key: string]: unknown;
}

export interface QueryKnowledgeRequest {
  query: string;
  top_k?: number;
  mode?: 'synthesis' | 'retrieve';
  max_tokens_budget?: number;
  include_graph_triples?: boolean;
}

export interface QueryKnowledgeResponse {
  answer: string;
  results: HybridSearchResult[];
  total_tokens_estimated?: number;
  retrieval_trace?: RetrievalTrace;
}
