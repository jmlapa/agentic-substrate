import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { knowledgeApi } from '../api/knowledge-api';
import { CreateKnowledgeBaseDTO, UploadDocumentOptions } from '../api/types';

export interface UploadDocumentParams {
  file: File;
  options?: UploadDocumentOptions;
}

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
    mutationFn: (param: File | UploadDocumentParams) => {
      if ('file' in param) {
        return knowledgeApi.uploadDocument(kbId, param.file, param.options);
      }
      return knowledgeApi.uploadDocument(kbId, param);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases', kbId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
  });
};

export const useDeleteKnowledgeBase = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (kbId: string) => knowledgeApi.deleteBase(kbId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
  });
};

export const useDeleteDocument = (kbId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) => knowledgeApi.deleteDocument(kbId, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases', kbId] });
      queryClient.invalidateQueries({ queryKey: ['knowledge-bases'] });
    },
  });
};
