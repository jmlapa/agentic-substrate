import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Layers,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Badge } from '../ui/Badge';
import { LoadingSpinner } from '../feedback/LoadingSpinner';
import { useDataSourceRuns } from '../../hooks/useDataSources';
import { DataSourceRunSummary, DataSourceSummary } from '../../api/types';

interface DataSourceRunsModalProps {
  isOpen: boolean;
  onClose: () => void;
  kbId: string;
  dataSource: DataSourceSummary | null;
}

export const DataSourceRunsModal: React.FC<DataSourceRunsModalProps> = ({
  isOpen,
  onClose,
  kbId,
  dataSource,
}) => {
  const { data: runs, isLoading, isFetching } = useDataSourceRuns(
    kbId,
    dataSource?.id || null
  );
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  if (!dataSource) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success">Concluído</Badge>;
      case 'PARTIALLY_FAILED':
        return <Badge variant="warning">Parcial</Badge>;
      case 'FAILED':
        return <Badge variant="error">Falhou</Badge>;
      case 'EXTRACTING':
      case 'INGESTING':
        return (
          <Badge variant="purple" className="flex items-center gap-1">
            <RefreshCw className="w-3 h-3 animate-spin text-indigo-400" />
            {status === 'EXTRACTING' ? 'Buscando' : 'Ingerindo'}
          </Badge>
        );
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return '-';
    try {
      return new Date(isoString).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Execuções: ${dataSource.name}`}
      description="Histórico de sincronizações, arquivos indexados e falhas delta."
      maxWidth="2xl"
    >
      <div className="space-y-4">
        {isLoading && <LoadingSpinner message="Carregando histórico de sincronização..." />}

        {!isLoading && (!runs || runs.length === 0) && (
          <div className="py-10 text-center text-zinc-400 text-xs">
            <Clock className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
            <p className="font-semibold text-zinc-300">Nenhuma execução registrada</p>
            <p className="mt-1">
              Clique em &ldquo;Sincronizar Agora&rdquo; para rodar a primeira extração desta pasta.
            </p>
          </div>
        )}

        {runs && runs.length > 0 && (
          <div className="space-y-3">
            {runs.map((run: DataSourceRunSummary) => {
              const isExpanded = expandedRunId === run.id;
              const hasFailures = run.failure_summary && run.failure_summary.length > 0;

              return (
                <div
                  key={run.id}
                  className="rounded-xl border border-zinc-800 bg-zinc-900/80 p-3.5 space-y-3"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(run.status)}
                      <span className="text-[11px] font-mono text-zinc-500">
                        {run.id.slice(0, 8)}...
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-zinc-400">
                      <span>Início: <strong className="text-zinc-300">{formatDate(run.started_at)}</strong></span>
                      {run.completed_at && (
                        <span>Fim: <strong className="text-zinc-300">{formatDate(run.completed_at)}</strong></span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap text-xs pt-1 border-t border-zinc-800/60">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700/60 text-zinc-300">
                      <Layers className="w-3 h-3 text-indigo-400" />
                      Descobertos: <strong>{run.total_files_discovered}</strong>
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      Indexados: <strong>{run.indexed_files_count}</strong>
                    </span>
                    {run.failed_files_count > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-rose-950/60 border border-rose-800/60 text-rose-300">
                        <XCircle className="w-3 h-3 text-rose-400" />
                        Falhas: <strong>{run.failed_files_count}</strong>
                      </span>
                    )}

                    {hasFailures && (
                      <button
                        type="button"
                        onClick={() => setExpandedRunId(isExpanded ? null : run.id)}
                        className="ml-auto inline-flex items-center gap-1 text-[11px] text-amber-400 hover:text-amber-300"
                      >
                        <AlertTriangle className="w-3 h-3" />
                        {isExpanded ? 'Ocultar Detalhes' : 'Ver Falhas'}
                        {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                    )}
                  </div>

                  {isExpanded && hasFailures && (
                    <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-1.5 text-xs">
                      <p className="font-semibold text-zinc-400 text-[10px] uppercase tracking-wider">
                        Erros Reportados ({run.failure_summary.length}):
                      </p>
                      <ul className="space-y-1">
                        {run.failure_summary.map((fail, idx) => (
                          <li key={idx} className="text-rose-300 text-[11px] font-mono break-all">
                            • {fail.name ? `${fail.name}: ` : ''}{fail.error}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {isFetching && !isLoading && (
          <div className="flex items-center justify-center gap-2 text-[11px] text-zinc-500 pt-2">
            <RefreshCw className="w-3 h-3 animate-spin" /> Atualizando status em tempo real...
          </div>
        )}
      </div>
    </Modal>
  );
};
