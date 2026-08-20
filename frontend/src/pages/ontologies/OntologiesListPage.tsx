import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitFork, Plus, ArrowRight, CircleDot, Trash2, AlertTriangle } from 'lucide-react';
import { useOntologies, useDeleteOntology } from '../../hooks/useOntologies';
import { OntologyTemplate } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/feedback/EmptyState';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export const OntologiesListPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: ontologies, isLoading, isError, error, refetch } = useOntologies();
  const deleteOntologyMutation = useDeleteOntology();

  const [deletingOntology, setDeletingOntology] = useState<OntologyTemplate | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteConfirm = async () => {
    if (!deletingOntology) return;
    setDeleteError(null);
    try {
      await deleteOntologyMutation.mutateAsync(deletingOntology.id);
      setDeletingOntology(null);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data
          ?.detail?.message || 'Falha ao excluir ontologia.';
      setDeleteError(msg);
    }
  };

  return (
    <PageContainer
      title="Ontologias"
      description="Gerencie os esquemas ontológicos e tipos de entidades/relações para extração no FalkorDB."
      actions={
        <Button
          onClick={() => navigate('/ontologies/new')}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          Nova Ontologia
        </Button>
      }
    >
      {isLoading && <LoadingSpinner message="Carregando ontologias..." />}

      {isError && (
        <ErrorBanner
          message={(error as Error)?.message || 'Erro ao carregar ontologias.'}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && (!ontologies || ontologies.length === 0) && (
        <EmptyState
          icon={GitFork}
          title="Nenhuma ontologia cadastrada"
          description="Crie sua primeira ontologia definindo entidades e relacionamentos para orientar o extrator de grafos."
          actionLabel="Criar Ontologia"
          onAction={() => navigate('/ontologies/new')}
        />
      )}

      {!isLoading && !isError && ontologies && ontologies.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ontologies.map((ont) => (
            <Card
              key={ont.id}
              hoverable
              className="cursor-pointer flex flex-col justify-between group relative"
              onClick={() => navigate(`/ontologies/${ont.id}`)}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/60 text-indigo-400">
                      <GitFork className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-zinc-100 group-hover:text-indigo-400 transition-colors">
                      {ont.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="purple">v{ont.version}</Badge>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteError(null);
                        setDeletingOntology(ont);
                      }}
                      className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                      title="Excluir Ontologia"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <p className="mt-3 text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                  {ont.description || 'Sem descrição cadastrada.'}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-zinc-800/60 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                  <span className="flex items-center gap-1">
                    <CircleDot className="w-3 h-3 text-indigo-400" />
                    {ont.node_types.length} nós
                  </span>
                  <span>•</span>
                  <span>{ont.relationship_types.length} relações</span>
                </div>

                <div className="text-zinc-500 group-hover:text-zinc-300 group-hover:translate-x-0.5 transition-all">
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Confirmation Modal */}
      <Modal
        isOpen={!!deletingOntology}
        onClose={() => {
          setDeletingOntology(null);
          setDeleteError(null);
        }}
        title="Confirmar Exclusão de Ontologia"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-200">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-rose-300">Ação irreversível</p>
              <p className="text-zinc-300">
                Tem certeza que deseja excluir o template de ontologia <strong>&ldquo;{deletingOntology?.name}&rdquo;</strong>?
              </p>
              <p className="text-zinc-400">
                Se esta ontologia estiver vinculada a alguma Knowledge Base ativa, a exclusão será bloqueada para manter a integridade referencial.
              </p>
            </div>
          </div>

          {deleteError && <ErrorBanner message={deleteError} />}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDeletingOntology(null);
                setDeleteError(null);
              }}
              disabled={deleteOntologyMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteConfirm}
              isLoading={deleteOntologyMutation.isPending}
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              Excluir Definitivamente
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
};
