import { apiClient } from './client';
import {
  CreateOntologyTemplateDTO,
  ListOntologyTemplatesResponse,
  OntologyTemplate,
} from './types';

export const ontologiesApi = {
  async list(): Promise<OntologyTemplate[]> {
    const response = await apiClient.get<ListOntologyTemplatesResponse>(
      '/api/v1/ontologies'
    );
    return response.data.templates;
  },

  async getById(id: string): Promise<OntologyTemplate> {
    const response = await apiClient.get<OntologyTemplate>(
      `/api/v1/ontologies/${id}`
    );
    return response.data;
  },

  async create(data: CreateOntologyTemplateDTO): Promise<OntologyTemplate> {
    const response = await apiClient.post<OntologyTemplate>(
      '/api/v1/ontologies',
      data
    );
    return response.data;
  },

  async delete(
    id: string
  ): Promise<{ ontology_id: string; success: boolean; message: string }> {
    const response = await apiClient.delete<{
      ontology_id: string;
      success: boolean;
      message: string;
    }>(`/api/v1/ontologies/${id}`);
    return response.data;
  },
};
