import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ontologiesApi } from '../api/ontologies-api';
import { CreateOntologyTemplateDTO } from '../api/types';

export const useOntologies = () => {
  return useQuery({
    queryKey: ['ontologies'],
    queryFn: ontologiesApi.list,
  });
};

export const useOntologyDetail = (id: string | undefined) => {
  return useQuery({
    queryKey: ['ontologies', id],
    queryFn: () => (id ? ontologiesApi.getById(id) : Promise.reject('ID missing')),
    enabled: !!id,
  });
};

export const useCreateOntology = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateOntologyTemplateDTO) => ontologiesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] });
    },
  });
};

export const useDeleteOntology = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => ontologiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontologies'] });
    },
  });
};
