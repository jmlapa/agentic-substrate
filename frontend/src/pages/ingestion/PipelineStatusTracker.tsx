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
} from 'lucide-react';
import { DocumentProcessingStatus } from '../../api/types';

export interface PipelineStatusTrackerProps {
  status: DocumentProcessingStatus | string;
  className?: string;
}

export const PipelineStatusTracker: React.FC<PipelineStatusTrackerProps> = ({
  status,
  className = '',
}) => {
  const stages = [
    { key: 'UPLOADED', label: 'Upload', icon: Clock },
    { key: 'PARSED', label: 'Parsing', icon: FileCode },
    { key: 'CHUNKED', label: 'Chunking', icon: Layers },
    { key: 'GRAPH_EXTRACTED', label: 'Grafo LLM', icon: Sparkles },
    { key: 'INDEXED', label: 'Indexado', icon: Database },
  ];

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
    <div className={`w-full py-2 ${className}`}>
      <div className="flex items-center justify-between relative">
        {/* Connecting Line */}
        <div className="absolute top-1/2 left-4 right-4 -translate-y-1/2 h-0.5 bg-zinc-800 -z-0" />
        <div
          className={`absolute top-1/2 left-4 -translate-y-1/2 h-0.5 transition-all duration-500 -z-0 ${
            isFailed ? 'bg-rose-500' : 'bg-indigo-500'
          }`}
          style={{
            width: isFailed
              ? '100%'
              : `${Math.min(100, Math.max(0, ((currentIndex - 1) / (stages.length - 1)) * 100))}%`,
          }}
        />

        {stages.map((stage, idx) => {
          const stageStep = idx + 1;
          const isDone = currentIndex > stageStep;
          const isCurrent = currentIndex === stageStep && !isFailed;
          const Icon = stage.icon;

          return (
            <div key={stage.key} className="flex flex-col items-center gap-1.5 z-10">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border transition-all ${
                  isDone
                    ? 'border-emerald-500 bg-emerald-950 text-emerald-400'
                    : isCurrent
                    ? 'border-indigo-500 bg-indigo-950 text-indigo-400 shadow-md shadow-indigo-500/20'
                    : isFailed
                    ? 'border-zinc-800 bg-zinc-900 text-zinc-600'
                    : 'border-zinc-800 bg-zinc-900 text-zinc-500'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                ) : (
                  <Icon className="w-3.5 h-3.5" />
                )}
              </div>
              <span
                className={`text-[10px] font-medium tracking-tight whitespace-nowrap ${
                  isDone
                    ? 'text-emerald-400'
                    : isCurrent
                    ? 'text-indigo-300 font-bold'
                    : 'text-zinc-500'
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {isFailed && (
        <div className="mt-3 flex items-center justify-center gap-1.5 text-xs text-rose-400 font-medium">
          <AlertCircle className="w-3.5 h-3.5" />
          Falha no processamento durante a extração do pipeline
        </div>
      )}
    </div>
  );
};
