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
  GitFork,
  Layers,
  Eye,
  Tag,
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { usePipelineMonitor } from '../../hooks/usePipelineMonitor';
import { useDeleteKnowledgeBase, useDeleteDocument } from '../../hooks/useKnowledgeBases';
import { knowledgeApi } from '../../api/knowledge-api';
import { DocumentSummary } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';
import { EmptyState } from '../../components/feedback/EmptyState';
import { DocumentUploadModal } from '../ingestion/DocumentUploadModal';
import { PipelineStatusTracker } from '../ingestion/PipelineStatusTracker';

export const KnowledgeBaseDetailPage: React.FC = () => {
  const { kbId } = useParams<{ kbId: string }>();
  const navigate = useNavigate();
  const { data: kb, isLoading, isError, error, refetch, isFetching } = usePipelineMonitor(kbId);
  const deleteKbMutation = useDeleteKnowledgeBase();
  const deleteDocMutation = useDeleteDocument(kbId || '');

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [reprocessingDocId, setReprocessingDocId] = useState<string | null>(null);

  const [isDeleteKbModalOpen, setIsDeleteKbModalOpen] = useState(false);
  const [deletingDoc, setDeletingDoc] = useState<DocumentSummary | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteKbConfirm = async () => {
    if (!kbId) return;
    setDeleteError(null);
    try {
      await deleteKbMutation.mutateAsync(kbId);
      navigate('/knowledge-bases');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data
          ?.detail?.message || 'Falha ao excluir Knowledge Base.';
      setDeleteError(msg);
    }
  };

  const handleDeleteDocConfirm = async () => {
    if (!deletingDoc) return;
    setDeleteError(null);
    try {
      await deleteDocMutation.mutateAsync(deletingDoc.id);
      setDeletingDoc(null);
      await refetch();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } } } })?.response?.data
          ?.detail?.message || 'Falha ao excluir Documento.';
      setDeleteError(msg);
    }
  };

  const handleReprocess = async (docId: string) => {
    if (!kbId) return;
    setReprocessingDocId(docId);
    try {
      await knowledgeApi.reprocessDocument(kbId, docId);
      await refetch();
    } catch (err) {
      console.error('Falha ao reiniciar saga', err);
    } finally {
      setReprocessingDocId(null);
    }
  };

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
          <Button
            variant="danger"
            onClick={() => {
              setDeleteError(null);
              setIsDeleteKbModalOpen(true);
            }}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            Excluir Base
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
                  {processingDocsCount} documento(s) em processamento assíncrono na saga. O monitor atualiza automaticamente a cada 2s.
                </span>
              </div>
            </div>
          )}

          {/* Ontologia Vinculada (Schema do Grafo) */}
          <Card className="space-y-4 border-zinc-800 bg-zinc-900/60">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-400">
                  <GitFork className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">
                    Ontologia Vinculada (Schema do Grafo)
                  </h3>
                  <p className="text-xs text-zinc-400">
                    {kb.ontology
                      ? `${kb.ontology.name} — ${kb.ontology.description}`
                      : 'Nenhuma ontologia de domínio foi vinculada a esta Knowledge Base.'}
                  </p>
                </div>
              </div>
              {kb.ontology && (
                <div className="flex items-center gap-2">
                  <Badge variant="purple">
                    {kb.ontology.node_types.length} Tipos de Entidades
                  </Badge>
                  <Badge variant="default">
                    {kb.ontology.relationship_types.length} Tipos de Relações
                  </Badge>
                </div>
              )}
            </div>

            {kb.ontology ? (
              <div className="space-y-3">
                <div>
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block mb-2">
                    Entidades Reconhecidas pelo Extrator LLM:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {kb.ontology.node_types.map((nt) => (
                      <div
                        key={nt.name}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-800/80 border border-zinc-700/60 text-xs text-zinc-200"
                        title={nt.description}
                      >
                        <Tag className="w-3 h-3 text-indigo-400" />
                        <span className="font-semibold text-zinc-100">{nt.name}</span>
                        {nt.properties.length > 0 && (
                          <span className="text-[10px] text-zinc-400">
                            ({nt.properties.length} props)
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {kb.ontology.relationship_types.length > 0 && (
                  <div>
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 block mb-2">
                      Relações Válidas:
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {kb.ontology.relationship_types.map((rt) => (
                        <div
                          key={rt.name}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-[11px] font-mono text-zinc-300"
                        >
                          <span className="text-zinc-400">{rt.source_node_type}</span>
                          <span className="text-indigo-400 font-bold">➔ {rt.name} ➔</span>
                          <span className="text-zinc-400">{rt.target_node_type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-zinc-500 italic">
                A indexação operou em modo puramente estrutural (Document ➔ ParentChunk ➔ ChildChunk + Embeddings Vetoriais).
              </p>
            )}
          </Card>

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
                  <Card key={doc.id} className="space-y-4 bg-zinc-900/90 border-zinc-800">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                        <span className="font-semibold text-sm text-zinc-100">{doc.file_name}</span>
                        <span className="text-[11px] font-mono text-zinc-500">({doc.id})</span>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Media badge */}
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                            doc.file_name.match(/\.(mp3|m4a|ogg|opus|wav|webm|aac|caf|amr|3gp)$/i)
                              ? 'bg-amber-950/80 border border-amber-800/80 text-amber-300'
                              : doc.file_name.match(/\.(png|jpg|jpeg|webp|heic|heif)$/i)
                              ? 'bg-purple-950/80 border border-purple-800/80 text-purple-300'
                              : 'bg-zinc-800 border border-zinc-700 text-zinc-300'
                          }`}
                        >
                          {doc.file_name.match(/\.(mp3|m4a|ogg|opus|wav|webm|aac|caf|amr|3gp)$/i)
                            ? '🎙️ Áudio'
                            : doc.file_name.match(/\.(png|jpg|jpeg|webp|heic|heif)$/i)
                            ? '🖼️ Imagem'
                            : '📄 Doc'}
                        </span>
                        {doc.enable_ocr && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300">
                            <Eye className="w-3 h-3 text-emerald-400" /> OCR Vision Ativo
                          </span>
                        )}

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
                        {doc.status !== 'INDEXED' && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleReprocess(doc.id)}
                            isLoading={reprocessingDocId === doc.id}
                            leftIcon={<RefreshCw className="w-3 h-3" />}
                            title="Reinicia a saga reaproveitando páginas e chunks já gravados em cache ($0.00)"
                          >
                            Retomar Ingestão
                          </Button>
                        )}
                        <button
                          onClick={() => {
                            setDeleteError(null);
                            setDeletingDoc(doc);
                          }}
                          className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
                          title="Excluir Documento"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* OCR Instructions if provided */}
                    {doc.ocr_instructions && (
                      <div className="text-xs bg-zinc-950/70 border border-zinc-800/80 rounded-lg p-2.5 text-zinc-300">
                        <span className="font-semibold text-zinc-400 block text-[10px] uppercase tracking-wider mb-1">
                          Diretrizes de OCR / MarkItDown:
                        </span>
                        <p className="italic text-zinc-300 font-mono text-[11px]">
                          &ldquo;{doc.ocr_instructions}&rdquo;
                        </p>
                      </div>
                    )}

                    {/* Metadata Chips: Chunks & Graph Stats */}
                    {(doc.total_parents || doc.total_children || doc.indexed_nodes_count) && (
                      <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-300 pt-1">
                        {doc.total_parents && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-800/80 border border-zinc-700/60 text-[11px]">
                            <Layers className="w-3 h-3 text-indigo-400" />
                            <strong>{doc.total_parents}</strong> Seções Parent
                          </span>
                        )}
                        {doc.total_children && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-800/80 border border-zinc-700/60 text-[11px]">
                            <Layers className="w-3 h-3 text-emerald-400" />
                            <strong>{doc.total_children}</strong> Chunks Filhos (pgvector)
                          </span>
                        )}
                        {doc.indexed_nodes_count !== undefined && (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-800/80 border border-zinc-700/60 text-[11px]">
                            <Sparkles className="w-3 h-3 text-amber-400" />
                            <strong>{doc.indexed_nodes_count}</strong> Nós / <strong>{doc.indexed_edges_count || 0}</strong> Arestas (FalkorDB)
                          </span>
                        )}
                      </div>
                    )}

                    {/* Timeline stepper */}
                    <div className="pt-2 border-t border-zinc-800/60">
                      <PipelineStatusTracker
                        status={doc.status}
                        enableOcr={doc.enable_ocr}
                        totalParents={doc.total_parents}
                        totalChildren={doc.total_children}
                        indexedNodesCount={doc.indexed_nodes_count}
                        indexedEdgesCount={doc.indexed_edges_count}
                        progressStep={doc.progress_step}
                        progressCurrent={doc.progress_current}
                        progressTotal={doc.progress_total}
                        progressPercentage={doc.progress_percentage}
                        progressMessage={doc.progress_message}
                        errorStep={doc.error?.step}
                        errorMessage={doc.error?.message}
                      />
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

      {/* Delete KB Modal */}
      <Modal
        isOpen={isDeleteKbModalOpen}
        onClose={() => {
          setIsDeleteKbModalOpen(false);
          setDeleteError(null);
        }}
        title="Confirmar Exclusão de Knowledge Base"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-200">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-rose-300">Ação irreversível</p>
              <p className="text-zinc-300">
                Tem certeza que deseja excluir esta Knowledge Base (<strong>&ldquo;{kb?.name}&rdquo;</strong>)?
              </p>
              <p className="text-zinc-400">
                Todos os {docs.length} documento(s), arquivos locais em disco e grafos indexados no FalkorDB serão destruídos.
              </p>
            </div>
          </div>

          {deleteError && <ErrorBanner message={deleteError} />}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsDeleteKbModalOpen(false);
                setDeleteError(null);
              }}
              disabled={deleteKbMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteKbConfirm}
              isLoading={deleteKbMutation.isPending}
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              Excluir Definitivamente
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Document Modal */}
      <Modal
        isOpen={!!deletingDoc}
        onClose={() => {
          setDeletingDoc(null);
          setDeleteError(null);
        }}
        title="Confirmar Exclusão de Documento"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-200">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-rose-300">Ação irreversível</p>
              <p className="text-zinc-300">
                Tem certeza que deseja excluir o documento <strong>&ldquo;{deletingDoc?.file_name}&rdquo;</strong>?
              </p>
              <p className="text-zinc-400">
                Os chunks hierárquicos, embeddings e subgrafos extraídos deste documento no FalkorDB serão removidos.
              </p>
            </div>
          </div>

          {deleteError && <ErrorBanner message={deleteError} />}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDeletingDoc(null);
                setDeleteError(null);
              }}
              disabled={deleteDocMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteDocConfirm}
              isLoading={deleteDocMutation.isPending}
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              Excluir Documento
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
};
