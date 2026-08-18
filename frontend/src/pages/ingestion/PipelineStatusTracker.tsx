import React from 'react';
import {
  CheckCircle2,
  Clock,
  FileCode,
  Layers,
  Sparkles,
  Database,
  AlertCircle,
  Loader2,
  Eye,
} from 'lucide-react';
import { DocumentProcessingStatus } from '../../api/types';

export interface PipelineStatusTrackerProps {
  status: DocumentProcessingStatus | string;
  enableOcr?: boolean;
  totalParents?: number | null;
  totalChildren?: number | null;
  indexedNodesCount?: number;
  indexedEdgesCount?: number;
  errorStep?: string | null;
  errorMessage?: string | null;
  className?: string;
}

export const PipelineStatusTracker: React.FC<PipelineStatusTrackerProps> = ({
  status,
  enableOcr,
  totalParents,
  totalChildren,
  indexedNodesCount,
  indexedEdgesCount,
  errorStep,
  errorMessage,
  className = '',
}) => {
  const stages = [
    {
      key: 'UPLOADED',
      label: 'Upload',
      icon: Clock,
      sublabel: 'Persistido',
    },
    {
      key: 'PARSED',
      label: 'Parsing',
      icon: enableOcr ? Eye : FileCode,
      sublabel: enableOcr ? 'OCR Vision' : 'MarkItDown',
    },
    {
      key: 'CHUNKED',
      label: 'Chunking',
      icon: Layers,
      sublabel:
        totalParents && totalChildren
          ? `${totalParents}P / ${totalChildren}F`
          : 'Parent-Child',
    },
    {
      key: 'GRAPH_EXTRACTED',
      label: 'Grafo LLM',
      icon: Sparkles,
      sublabel:
        indexedNodesCount !== undefined && indexedNodesCount > 0
          ? `${indexedNodesCount}N / ${indexedEdgesCount || 0}A`
          : 'PydanticAI',
    },
    {
      key: 'INDEXED',
      label: 'Indexado',
      icon: Database,
      sublabel: 'FalkorDB + Vetor',
    },
  ];

  // Determina o índice de progresso da saga (0 a 5)
  const getStageIndex = (s: string) => {
    switch (s) {
      case 'PENDING_UPLOAD':
        return 0;
      case 'UPLOADED':
        return 1;
      case 'PARSED':
        return 2;
      case 'CHUNKED':
        return 3;
      case 'GRAPH_EXTRACTED':
        return 4;
      case 'INDEXED':
        return 5;
      default:
        return 0;
    }
  };

  const isFailed = status === 'FAILED';
  const currentIndex = getStageIndex(status);

  return (
    <div className={`w-full py-2.5 ${className}`}>
      <div className="flex items-center justify-between relative">
        {/* Linha de Conexão Base */}
        <div className="absolute top-4 left-6 right-6 h-0.5 bg-zinc-800 -z-0" />
        {/* Linha de Progresso Ativa */}
        <div
          className={`absolute top-4 left-6 h-0.5 transition-all duration-700 ease-out -z-0 ${
            isFailed ? 'bg-rose-500' : 'bg-emerald-500'
          }`}
          style={{
            width: isFailed
              ? '100%'
              : `${Math.min(
                  100,
                  Math.max(
                    0,
                    currentIndex === 5
                      ? 100
                      : ((currentIndex) / (stages.length - 1)) * 100
                  )
                )}%`,
          }}
        />

        {stages.map((stage, idx) => {
          const stageStep = idx + 1;
          // Quando INDEXED (5), todos os 5 passos são 'isDone = true'
          const isDone = currentIndex >= stageStep;
          // O passo atual em execução é o próximo a ser completado
          const isCurrent = !isDone && currentIndex === idx && !isFailed;
          const Icon = stage.icon;

          return (
            <div
              key={stage.key}
              className="flex flex-col items-center gap-1.5 z-10 min-w-[64px]"
            >
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border transition-all ${
                  isDone
                    ? 'border-emerald-500/80 bg-emerald-950 text-emerald-400 shadow-sm shadow-emerald-500/10'
                    : isCurrent
                    ? 'border-indigo-500 bg-indigo-950 text-indigo-300 shadow-md shadow-indigo-500/30 ring-2 ring-indigo-500/20'
                    : isFailed
                    ? 'border-zinc-800 bg-zinc-900 text-zinc-600'
                    : 'border-zinc-800 bg-zinc-900/90 text-zinc-500'
                }`}
                title={stage.label}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>

              <div className="flex flex-col items-center text-center">
                <span
                  className={`text-[11px] font-semibold tracking-tight whitespace-nowrap ${
                    isDone
                      ? 'text-emerald-400'
                      : isCurrent
                      ? 'text-indigo-300 font-bold'
                      : isFailed
                      ? 'text-zinc-600'
                      : 'text-zinc-500'
                  }`}
                >
                  {stage.label}
                </span>
                <span className="text-[9px] font-mono text-zinc-500 whitespace-nowrap">
                  {stage.sublabel}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {isFailed && (
        <div className="mt-3.5 flex items-start gap-2.5 rounded-lg border border-rose-900/60 bg-rose-950/30 p-2.5 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <p className="font-semibold text-rose-200">
              Falha no processamento (Etapa: {errorStep || 'Pipeline Ingestion'})
            </p>
            {errorMessage && (
              <p className="text-[11px] font-mono text-rose-400/90">{errorMessage}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
