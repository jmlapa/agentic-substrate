import React from 'react';
import {
  Cloud,
  RefreshCw,
  History,
  Trash2,
  AlertCircle,
  Clock,
  CheckCircle,
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { DataSourceSummary } from '../../api/types';

interface DataSourceCardProps {
  dataSource: DataSourceSummary;
  onSync: (dsId: string) => Promise<void>;
  onViewRuns: (dataSource: DataSourceSummary) => void;
  onDelete: (dataSource: DataSourceSummary) => void;
  isSyncingCurrent: boolean;
}

export const DataSourceCard: React.FC<DataSourceCardProps> = ({
  dataSource,
  onSync,
  onViewRuns,
  onDelete,
  isSyncingCurrent,
}) => {
  const isSyncing = dataSource.status === 'SYNCING' || isSyncingCurrent;
  const config = dataSource.config as { folder_id?: string; recursive?: boolean };

  const formatTimestamp = (dateStr?: string | null) => {
    if (!dateStr) return 'Nunca sincronizado';
    try {
      return new Date(dateStr).toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = () => {
    switch (dataSource.status) {
      case 'SYNCING':
        return (
          <Badge variant="purple" className="flex items-center gap-1">
            <RefreshCw className="w-3 h-3 animate-spin text-indigo-400" />
            Sincronizando
          </Badge>
        );
      case 'FAILED':
        return (
          <Badge variant="error" className="flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-rose-400" />
            Falha
          </Badge>
        );
      case 'DISABLED':
        return <Badge variant="warning">Desativado</Badge>;
      case 'IDLE':
      default:
        return (
          <Badge variant="success" className="flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-emerald-400" />
            Pronto
          </Badge>
        );
    }
  };

  return (
    <Card className="space-y-4 bg-zinc-900/90 border-zinc-800">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-3 min-w-0">
          <div className="p-2 rounded-xl bg-indigo-950/80 border border-indigo-800 text-indigo-400 shrink-0">
            <Cloud className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-semibold text-sm text-zinc-100 truncate">
                {dataSource.name}
              </h4>
              {getStatusBadge()}
            </div>
            <p className="text-xs text-zinc-400 mt-0.5 flex items-center gap-1.5 flex-wrap">
              <span>Google Drive Folder</span>
              {config?.folder_id && (
                <>
                  <span>•</span>
                  <span className="font-mono text-zinc-300">ID: {config.folder_id}</span>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onSync(dataSource.id)}
            disabled={isSyncing}
            isLoading={isSyncing}
            leftIcon={<RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />}
            title="Iniciar sincronização delta imediatamente"
          >
            Sincronizar Agora
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewRuns(dataSource)}
            leftIcon={<History className="w-3.5 h-3.5 text-zinc-400" />}
            title="Ver histórico de execuções e logs de erro"
          >
            Histórico
          </Button>
          <button
            onClick={() => onDelete(dataSource)}
            className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-950/40 transition-colors"
            title="Excluir Conector"
            aria-label="Excluir conector"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {dataSource.error_message && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-rose-950/30 border border-rose-900/50 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span className="break-all">{dataSource.error_message}</span>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-zinc-800/60 text-xs text-zinc-400">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-zinc-500" />
          <span>Último sync: <strong className="text-zinc-200">{formatTimestamp(dataSource.last_synced_at)}</strong></span>
        </div>
        <div>
          <span>Intervalo: <strong className="text-zinc-200">{dataSource.sync_interval_minutes} min</strong></span>
        </div>
        <div>
          <span>Modo: <strong className="text-zinc-200">{config?.recursive !== false ? 'Recursivo' : 'Apenas raiz'}</strong></span>
        </div>
      </div>
    </Card>
  );
};
