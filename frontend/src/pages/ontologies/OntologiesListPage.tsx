import React from 'react';
import { useNavigate } from 'react-router-dom';
import { GitFork, Plus, ArrowRight, CircleDot } from 'lucide-react';
import { useOntologies } from '../../hooks/useOntologies';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/feedback/EmptyState';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export const OntologiesListPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: ontologies, isLoading, isError, error, refetch } = useOntologies();

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
              className="cursor-pointer flex flex-col justify-between group"
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
                  <Badge variant="purple">v{ont.version}</Badge>
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
    </PageContainer>
  );
};
