import { useQuery } from '@tanstack/react-query';
import { knowledgeApi } from '../api/knowledge-api';
import { KnowledgeBaseDetail } from '../api/types';

export const usePipelineMonitor = (kbId: string | undefined) => {
  return useQuery<KnowledgeBaseDetail>({
    queryKey: ['knowledge-bases', kbId],
    queryFn: () => (kbId ? knowledgeApi.getBaseById(kbId) : Promise.reject('Missing kbId')),
    enabled: !!kbId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data || !data.documents || data.documents.length === 0) {
        return false;
      }
      // Check if any document is still in progress
      const hasActive = data.documents.some(
        (doc) => doc.status !== 'INDEXED' && doc.status !== 'FAILED'
      );
      return hasActive ? 2000 : false;
    },
  });
};
