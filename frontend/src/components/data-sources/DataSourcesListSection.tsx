import React, { useState } from 'react';
import { Cloud, FolderGit2, AlertTriangle, Trash2, Plus } from 'lucide-react';
import { DataSourceCard } from './DataSourceCard';
import { CreateDataSourceModal } from './CreateDataSourceModal';
import { DataSourceRunsModal } from './DataSourceRunsModal';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { EmptyState } from '../feedback/EmptyState';
import { ErrorBanner } from '../feedback/ErrorBanner';
import { LoadingSpinner } from '../feedback/LoadingSpinner';
import {
  useDataSources,
  useDeleteDataSource,
  useSyncDataSource,
} from '../../hooks/useDataSources';
import { DataSourceSummary } from '../../api/types';

interface DataSourcesListSectionProps {
  kbId: string;
}

export const DataSourcesListSection: React.FC<DataSourcesListSectionProps> = ({
  kbId,
}) => {
  const { data: dataSources, isLoading, isError, error, refetch } = useDataSources(kbId);
  const deleteMutation = useDeleteDataSource(kbId);
  const syncMutation = useSyncDataSource(kbId);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [runsDataSource, setRunsDataSource] = useState<DataSourceSummary | null>(null);
  const [deletingDataSource, setDeletingDataSource] = useState<DataSourceSummary | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const handleSync = async (dsId: string) => {
    setSyncingId(dsId);
    try {
      await syncMutation.mutateAsync(dsId);
    } catch (err) {
      console.error('Falha ao acionar sincronização', err);
    } finally {
      setSyncingId(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingDataSource) return;
    setDeleteError(null);
    try {
      await deleteMutation.mutateAsync(deletingDataSource.id);
      setDeletingDataSource(null);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } } } })
          ?.response?.data?.detail?.message ||
        (err as Error)?.message ||
        'Falha ao excluir o conector de dados.';
      setDeleteError(msg);
    }
  };

  const sources = dataSources || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3 flex-wrap gap-2">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-2">
          <Cloud className="w-4 h-4 text-indigo-400" />
          Fontes de Dados & Conectores ({sources.length})
        </h3>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setIsCreateModalOpen(true)}
          leftIcon={<Plus className="w-3.5 h-3.5" />}
        >
          Conectar Google Drive
        </Button>
      </div>

      {isLoading && <LoadingSpinner message="Carregando conectores de fontes de dados..." />}

      {isError && (
        <ErrorBanner
          message={(error as Error)?.message || 'Erro ao carregar fontes de dados.'}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && sources.length === 0 && (
        <EmptyState
          icon={FolderGit2}
          title="Nenhum conector de dados configurado"
          description="Conecte uma pasta do Google Drive para importar documentos continuamente com sincronização delta e blue/green swap."
          actionLabel="Conectar Google Drive"
          onAction={() => setIsCreateModalOpen(true)}
        />
      )}

      {!isLoading && sources.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {sources.map((ds) => (
            <DataSourceCard
              key={ds.id}
              dataSource={ds}
              onSync={handleSync}
              onViewRuns={(source) => setRunsDataSource(source)}
              onDelete={(source) => {
                setDeleteError(null);
                setDeletingDataSource(source);
              }}
              isSyncingCurrent={syncingId === ds.id}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateDataSourceModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        kbId={kbId}
      />

      {/* Runs History Modal */}
      <DataSourceRunsModal
        isOpen={!!runsDataSource}
        onClose={() => setRunsDataSource(null)}
        kbId={kbId}
        dataSource={runsDataSource}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deletingDataSource}
        onClose={() => {
          setDeletingDataSource(null);
          setDeleteError(null);
        }}
        title="Confirmar Exclusão de Conector"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 text-rose-200">
            <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <p className="font-semibold text-rose-300">Ação irreversível</p>
              <p className="text-zinc-300">
                Deseja realmente desconectar a fonte <strong>&ldquo;{deletingDataSource?.name}&rdquo;</strong>?
              </p>
              <p className="text-zinc-400">
                O agendador não executará mais sincronizações para esta pasta. Documentos já ingeridos anteriormente permanecerão na base.
              </p>
            </div>
          </div>

          {deleteError && <ErrorBanner message={deleteError} />}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDeletingDataSource(null);
                setDeleteError(null);
              }}
              disabled={deleteMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleDeleteConfirm}
              isLoading={deleteMutation.isPending}
              leftIcon={<Trash2 className="w-4 h-4" />}
            >
              Excluir Conector
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
