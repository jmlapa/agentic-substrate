import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { knowledgeApi } from '../api/knowledge-api';
import { CreateKnowledgeBaseDTO } from '../api/types';

export const useKnowledgeBases = () => {
  return useQuery({
    queryKey: ['knowledge-bases'],
    queryFn: knowledgeApi.listBases,
  });
};

export const useKnowledgeBaseDetail = (kbId: string | undefined) => {
  return useQuery({
    queryKey: ['knowledge-bases', kbId],
    queryFn: () => (kbId ? knowledgeApi.getBaseById(kbId) : Promise.reject('KB ID missing')),
    enabled: !!kbId,
  });
};

export const useCreateKnowledgeBase = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateKnowledgeBaseDTO) => knowledgeApi.createBase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
  });
};

export const useUploadDocument = (kbId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => knowledgeApi.uploadDocument(kbId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases', kbId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
  });
};
