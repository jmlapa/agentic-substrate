import { apiClient } from './client';
import {
  CreateDataSourceDTO,
  DataSourceRunSummary,
  DataSourceSummary,
  RetryFailedDataSourceItemsResponse,
  SyncDataSourceResponse,
} from './types';

export const dataSourcesApi = {
  async listDataSources(kbId: string): Promise<DataSourceSummary[]> {
    const response = await apiClient.get<DataSourceSummary[]>(
      `/api/v1/knowledge-bases/${kbId}/data-sources`
    );
    return response.data;
  },

  async createDataSource(
    kbId: string,
    payload: CreateDataSourceDTO
  ): Promise<DataSourceSummary> {
    const response = await apiClient.post<DataSourceSummary>(
      `/api/v1/knowledge-bases/${kbId}/data-sources`,
      payload
    );
    return response.data;
  },

  async deleteDataSource(
    kbId: string,
    dataSourceId: string
  ): Promise<{ data_source_id: string; success: boolean }> {
    const response = await apiClient.delete<{
      data_source_id: string;
      success: boolean;
    }>(`/api/v1/knowledge-bases/${kbId}/data-sources/${dataSourceId}`);
    return response.data;
  },

  async syncDataSource(
    kbId: string,
    dataSourceId: string
  ): Promise<SyncDataSourceResponse> {
    const response = await apiClient.post<SyncDataSourceResponse>(
      `/api/v1/knowledge-bases/${kbId}/data-sources/${dataSourceId}/sync`
    );
    return response.data;
  },

  async listDataSourceRuns(
    kbId: string,
    dataSourceId: string,
    limit: number = 50
  ): Promise<DataSourceRunSummary[]> {
    const response = await apiClient.get<DataSourceRunSummary[]>(
      `/api/v1/knowledge-bases/${kbId}/data-sources/${dataSourceId}/runs`,
      { params: { limit } }
    );
    return response.data;
  },

  async retryFailedItems(
    kbId: string,
    dataSourceId: string,
    runId: string
  ): Promise<RetryFailedDataSourceItemsResponse> {
    const response = await apiClient.post<RetryFailedDataSourceItemsResponse>(
      `/api/v1/knowledge-bases/${kbId}/data-sources/${dataSourceId}/runs/${runId}/retry`
    );
    return response.data;
  },
};
