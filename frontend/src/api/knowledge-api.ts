import { apiClient } from './client';
import {
  CreateKnowledgeBaseDTO,
  CreateKnowledgeBaseResponse,
  DocumentUploadResponse,
  KnowledgeBaseDetail,
  ListKnowledgeBasesResponse,
  QueryKnowledgeRequest,
  QueryKnowledgeResponse,
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
    file: File
  ): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

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
