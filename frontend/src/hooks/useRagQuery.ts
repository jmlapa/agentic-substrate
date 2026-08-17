import { useMutation } from '@tanstack/react-query';
import { knowledgeApi } from '../api/knowledge-api';
import { QueryKnowledgeRequest, QueryKnowledgeResponse } from '../api/types';

export interface SubmitRagQueryParams {
  kbId: string;
  payload: QueryKnowledgeRequest;
}

export const useRagQuery = () => {
  return useMutation<QueryKnowledgeResponse, Error, SubmitRagQueryParams>({
    mutationFn: ({ kbId, payload }) => knowledgeApi.queryBase(kbId, payload),
  });
};
