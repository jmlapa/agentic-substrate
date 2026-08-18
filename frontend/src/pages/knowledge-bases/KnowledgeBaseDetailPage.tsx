import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Database,
  UploadCloud,
  Sparkles,
  FileText,
  CheckCircle2,
  HardDrive,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { usePipelineMonitor } from '../../hooks/usePipelineMonitor';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';
import { EmptyState } from '../../components/feedback/EmptyState';
import { DocumentUploadModal } from '../ingestion/DocumentUploadModal';
import { PipelineStatusTracker } from '../ingestion/PipelineStatusTracker';

export const KnowledgeBaseDetailPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const { data: kb, isLoading, isError, error, refetch, isFetching } = usePipelineMonitor(kbId);

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const docs = kb?.documents || [];
  const indexedDocsCount = docs.filter((d) => d.status === 'INDEXED').length;
  const processingDocsCount = docs.filter(
    (d) => d.status !== 'INDEXED' && d.status !== 'FAILED'
  ).length;

  return (
    <PageContainer
      title={kb ? kb.name : 'Detalhes da Knowledge Base'}
      description={kb?.description || 'Partição de armazenamento e pipeline GraphRAG'}
      actions={
        <>
          <Button
            variant="outline"
            onClick={() => navigate('/knowledge-bases')}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Voltar
          </Button>
          <Button
            variant="secondary"
            onClick={() => refetch()}
            isLoading={isFetching}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Atualizar
          </Button>
          <Button
            variant="primary"
            onClick={() => setIsUploadModalOpen(true)}
            leftIcon={<UploadCloud className="w-4 h-4" />}
          >
            Upload de Arquivo
          </Button>
          <Button
            variant="success"
            onClick={() => navigate(`/playground?kbId=${kbId}`)}
            leftIcon={<Sparkles className="w-4 h-4" />}
          >
            Abrir Playground
          </Button>
        </>
      }
    >
      {isLoading && <LoadingSpinner message="Carregando Knowledge Base..." />}

      {isError && (
        <ErrorBanner
          message={(error as Error)?.message || 'Erro ao carregar Knowledge Base.'}
          onRetry={() => refetch()}
        />
      )}

      {kb && (
        <div className="space-y-8">
          {/* Metrics summary */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-400">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Status da Base</p>
                <div className="mt-0.5 flex items-center gap-1.5 font-bold text-zinc-100">
                  <Badge variant="success">{kb.status}</Badge>
                </div>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-indigo-950/80 border border-indigo-800 text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Total de Documentos</p>
                <p className="text-base font-bold text-zinc-100">{docs.length} arquivos</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Indexados no Grafo</p>
                <p className="text-base font-bold text-emerald-400">{indexedDocsCount} concluídos</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-zinc-300">
                <HardDrive className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Partição de Storage</p>
                <p className="text-xs font-mono font-medium text-zinc-300 truncate max-w-[130px]">
                  {kb.storage_partition}
                </p>
              </div>
            </Card>
          </div>

          {/* Active processing warning/indicator */}
          {processingDocsCount > 0 && (
            <div className="flex items-center justify-between rounded-xl border border-indigo-800/80 bg-indigo-950/40 p-4 text-indigo-200">
              <div className="flex items-center gap-3">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                <span className="text-xs font-medium">
                  {processingDocsCount} documento(s) em processamento assíncrono. O monitor atualiza automaticamente a cada 2s.
                </span>
              </div>
            </div>
          )}

          {/* Documents Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-indigo-400" />
                Documentos & Status do Pipeline ({docs.length})
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsUploadModalOpen(true)}
                leftIcon={<UploadCloud className="w-3.5 h-3.5" />}
              >
                Adicionar Arquivo
              </Button>
            </div>

            {docs.length === 0 ? (
              <EmptyState
                icon={FileText}
                title="Nenhum arquivo enviado para esta KB"
                description="Faça o upload do seu primeiro arquivo (PDF, TXT, MD) para acompanhar a extração hierárquica e ontológica."
                actionLabel="Fazer Upload Agora"
                onAction={() => setIsUploadModalOpen(true)}
              />
            ) : (
              <div className="space-y-4">
                {docs.map((doc) => (
                  <Card key={doc.id} className="space-y-3 bg-zinc-900/80 border-zinc-800">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                        <span className="font-semibold text-sm text-zinc-100">{doc.file_name}</span>
                        <span className="text-[11px] font-mono text-zinc-500">({doc.id})</span>
                      </div>
                      <Badge
                        variant={
                          doc.status === 'INDEXED'
                            ? 'success'
                            : doc.status === 'FAILED'
                            ? 'error'
                            : 'purple'
                        }
                      >
                        {doc.status}
                      </Badge>
                    </div>

                    {/* Timeline stepper */}
                    <div className="pt-2 border-t border-zinc-800/60">
                      <PipelineStatusTracker status={doc.status} />
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {kbId && (
        <DocumentUploadModal
          isOpen={isUploadModalOpen}
          onClose={() => setIsUploadModalOpen(false)}
          kbId={kbId}
        />
      )}
    </PageContainer>
  );
};
