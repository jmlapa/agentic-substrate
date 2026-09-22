import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { dataSourcesApi } from '../api/data-sources-api';
import {
  CreateDataSourceDTO,
  DataSourceRunSummary,
  DataSourceSummary,
} from '../api/types';

export const useDataSources = (kbId: string | undefined) => {
  return useQuery<DataSourceSummary[]>({
    queryKey: ['data-sources', kbId],
    queryFn: () =>
      kbId ? dataSourcesApi.listDataSources(kbId) : Promise.resolve([]),
    enabled: !!kbId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.length === 0) {
        return false;
      }
      const isSyncing = data.some((ds) => ds.status === 'SYNCING');
      return isSyncing ? 2500 : false;
    },
  });
};

export const useCreateDataSource = (kbId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateDataSourceDTO) =>
      dataSourcesApi.createDataSource(kbId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources', kbId] });
    },
  });
};

export const useDeleteDataSource = (kbId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dataSourceId: string) =>
      dataSourcesApi.deleteDataSource(kbId, dataSourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources', kbId] });
    },
  });
};

export const useSyncDataSource = (kbId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (dataSourceId: string) =>
      dataSourcesApi.syncDataSource(kbId, dataSourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-sources', kbId] });
      queryClient.invalidateQueries({ queryKey: ['data-source-runs', kbId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases', kbId] });
    },
  });
};

export const useDataSourceRuns = (
  kbId: string | undefined,
  dataSourceId: string | null
) => {
  return useQuery<DataSourceRunSummary[]>({
    queryKey: ['data-source-runs', kbId, dataSourceId],
    queryFn: () =>
      kbId && dataSourceId
        ? dataSourcesApi.listDataSourceRuns(kbId, dataSourceId)
        : Promise.resolve([]),
    enabled: !!kbId && !!dataSourceId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || data.length === 0) {
        return false;
      }
      const isRunning = data.some(
        (run) => run.status === 'EXTRACTING' || run.status === 'INGESTING'
      );
      return isRunning ? 2000 : false;
    },
  });
};
