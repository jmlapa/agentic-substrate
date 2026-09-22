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
  error_message?: string;
}

export type DocumentSourceType = 'document' | 'image' | 'audio';

export interface DocumentSummary {
  id: string;
  file_name: string;
  status: DocumentProcessingStatus | string;
  source_type?: DocumentSourceType;
  ingested_at?: number | null;
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
  document_id?: string;
  document_name?: string;
  source_type?: DocumentSourceType | string;
  ingested_at?: number | null;
  header_path: string;
  parent_content: string;
  relevance_score: number;
  retrieval_source?: string;
  prev_chunk_id?: string | null;
  next_chunk_id?: string | null;
  related_triples?: string[];
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
  source_types?: string[] | null;
  time_from?: number | null;
  time_to?: number | null;
  [key: string]: unknown;
}

export interface QueryKnowledgeRequest {
  query: string;
  top_k?: number;
  mode?: 'synthesis' | 'retrieve';
  max_tokens_budget?: number;
  include_graph_triples?: boolean;
  source_types?: DocumentSourceType[] | string[] | null;
  time_from?: number | null;
  time_to?: number | null;
  document_id?: string | null;
}

export interface QueryKnowledgeResponse {
  answer: string;
  results: HybridSearchResult[];
  total_tokens_estimated?: number;
  retrieval_trace?: RetrievalTrace;
}

export interface TocItem {
  level: number;
  title: string;
  anchor: string;
}

export interface DocumentContentResponse {
  document_id: string;
  kb_id: string;
  file_name: string;
  source_type: string;
  status: string;
  total_parents: number;
  total_children: number;
  markdown_content: string;
  toc_tree: TocItem[];
  ingested_at?: number | null;
}

export interface QuickSearchResult {
  document_id: string;
  document_name: string;
  match_type: 'title' | 'header' | 'content';
  matched_title: string;
  anchor: string;
  preview: string;
}

export interface QuickSearchResponse {
  query: string;
  results: QuickSearchResult[];
}

export type DataSourceType = 'google_drive_folder' | 'local_directory';

export type DataSourceStatus = 'IDLE' | 'SYNCING' | 'FAILED' | 'DISABLED';

export type DataSourceRunStatus =
  | 'EXTRACTING'
  | 'INGESTING'
  | 'COMPLETED'
  | 'PARTIALLY_FAILED'
  | 'FAILED';

export interface GoogleDriveFolderConfigDTO {
  folder_id: string;
  recursive?: boolean;
  baseline_days?: number;
  include_mime_types?: string[];
}

export interface DataSourceSummary {
  id: string;
  kb_id: string;
  name: string;
  data_source_type: DataSourceType | string;
  status: DataSourceStatus | string;
  cursor?: string | null;
  sync_interval_minutes: number;
  last_synced_at?: string | null;
  error_message?: string | null;
  config: GoogleDriveFolderConfigDTO | Record<string, unknown>;
  created_at: string;
  updated_at?: string | null;
}

export interface CreateDataSourceDTO {
  name: string;
  data_source_type: DataSourceType;
  config: GoogleDriveFolderConfigDTO | Record<string, unknown>;
  sync_interval_minutes: number;
}

export interface SyncDataSourceResponse {
  data_source_id: string;
  sync_run_id: string;
  total_items_discovered: number;
  status: string;
  message: string;
}

export interface DataSourceRunFailureItem {
  item_id?: string;
  name?: string;
  error: string;
}

export interface DataSourceRunSummary {
  id: string;
  data_source_id: string;
  kb_id: string;
  status: DataSourceRunStatus | string;
  total_files_discovered: number;
  indexed_files_count: number;
  failed_files_count: number;
  failure_summary: DataSourceRunFailureItem[];
  started_at: string;
  completed_at?: string | null;
}

