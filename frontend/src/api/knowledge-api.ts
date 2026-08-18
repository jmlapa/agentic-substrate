import { apiClient } from './client';
import {
  CreateKnowledgeBaseDTO,
  CreateKnowledgeBaseResponse,
  DocumentUploadResponse,
  KnowledgeBaseDetail,
  ListKnowledgeBasesResponse,
  QueryKnowledgeRequest,
  QueryKnowledgeResponse,
  UploadDocumentOptions,
} from './types';

export const knowledgeApi = {
  async listBases(): Promise<ListKnowledgeBasesResponse> {
    const response = await apiClient.get<ListKnowledgeBasesResponse>(
      '/api/v1/knowledge/bases'
    );
    return response.data;
  },

  async getBaseById(kbId: string): Promise<KnowledgeBaseDetail> {
    const response = await apiClient.get<KnowledgeBaseDetail>(
      `/api/v1/knowledge/bases/${kbId}`
    );
    return response.data;
  },

  async createBase(
    data: CreateKnowledgeBaseDTO
  ): Promise<CreateKnowledgeBaseResponse> {
    const response = await apiClient.post<CreateKnowledgeBaseResponse>(
      '/api/v1/knowledge/bases',
      data
    );
    return response.data;
  },

  async uploadDocument(
    kbId: string,
    file: File,
    options?: UploadDocumentOptions
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.enableOcr !== undefined) {
      formData.append('enable_ocr', String(options.enableOcr));
    }
    if (options?.ocrInstructions) {
      formData.append('ocr_instructions', options.ocrInstructions);
    }

    const response = await apiClient.post<DocumentUploadResponse>(
      `/api/v1/knowledge/bases/${kbId}/documents`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async reprocessDocument(
    kbId: string,
    documentId: string
  ): Promise<{ document_id: string; status: string; message: string }> {
    const response = await apiClient.post<{
      document_id: string;
      status: string;
      message: string;
    }>(`/api/v1/knowledge/bases/${kbId}/documents/${documentId}/reprocess`);
    return response.data;
  },

  async queryBase(
    kbId: string,
    data: QueryKnowledgeRequest
  ): Promise<QueryKnowledgeResponse> {
    const response = await apiClient.post<QueryKnowledgeResponse>(
      `/api/v1/knowledge/bases/${kbId}/query`,
      data
    );
    return response.data;
  },
};
