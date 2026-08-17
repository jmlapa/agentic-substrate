import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Plus, FileText, ArrowRight, HardDrive, CheckCircle2 } from 'lucide-react';
import { useKnowledgeBases } from '../../hooks/useKnowledgeBases';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { EmptyState } from '../../components/feedback/EmptyState';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export const KnowledgeBasesListPage: React.FC = () => {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useKnowledgeBases();

  const kbs = data?.knowledge_bases || [];

  return (
    <PageContainer
      title="Knowledge Bases"
      description="Gerencie partições de armazenamento, documentos indexados e conexões com o FalkorDB GraphRAG."
      actions={
        <Button
          onClick={() => navigate('/knowledge-bases/new')}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          Nova Knowledge Base
        </Button>
      }
    >
      {isLoading && <LoadingSpinner message="Carregando Knowledge Bases..." />}

      {isError && (
        <ErrorBanner
          message={(error as Error)?.message || 'Erro ao carregar Knowledge Bases.'}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !isError && kbs.length === 0 && (
        <EmptyState
          icon={Database}
          title="Nenhuma Knowledge Base criada"
          description="Crie uma Knowledge Base vinculando uma ontologia para iniciar a ingestão e extração de grafos de documentos."
          actionLabel="Criar Knowledge Base"
          onAction={() => navigate('/knowledge-bases/new')}
        />
      )}

      {!isLoading && !isError && kbs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {kbs.map((kb) => (
            <Card
              key={kb.id}
              hoverable
              className="cursor-pointer flex flex-col justify-between group"
              onClick={() => navigate(`/knowledge-bases/${kb.id}`)}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-400">
                      <Database className="w-4 h-4" />
                    </div>
                    <h3 className="font-semibold text-zinc-100 group-hover:text-emerald-400 transition-colors">
                      {kb.name}
                    </h3>
                  </div>
                  <Badge variant={kb.status === 'ACTIVE' ? 'success' : 'default'}>
                    <CheckCircle2 className="w-3 h-3" />
                    {kb.status}
                  </Badge>
                </div>

                <p className="mt-3 text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                  {kb.description || 'Sem descrição.'}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-zinc-800/60 flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
                  <span className="flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-indigo-400" />
                    {kb.documents_count} docs
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1 text-[11px] text-zinc-500">
                    <HardDrive className="w-3 h-3" />
                    {kb.storage_partition}
                  </span>
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
