import React, { useState } from 'react';
import { Layers, FileText, Share2, ChevronDown, ChevronUp } from 'lucide-react';
import { HybridSearchResult } from '../../api/types';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';

export interface EvidenceInspectorProps {
  results: HybridSearchResult[];
}

export const EvidenceInspector: React.FC<EvidenceInspectorProps> = ({ results }) => {
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({
    0: true, // open first by default
  });

  const toggleExpand = (index: number) => {
    setExpandedIndices((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  if (!results || results.length === 0) {
    return (
      <Card className="text-center p-8 text-zinc-500 text-xs">
        Nenhuma evidência retornada pelo FalkorDB para esta consulta.
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          Evidências Recuperadas do Grafo ({results.length})
        </h4>
        <span className="text-[11px] text-zinc-500 font-mono">Busca Híbrida Vetorial + Cypher</span>
      </div>

      <div className="space-y-3">
        {results.map((res, idx) => {
          const isExpanded = !!expandedIndices[idx];
          const hasGraph = res.related_entities && res.related_entities.length > 0;

          return (
            <Card
              key={idx}
              className="space-y-3 bg-zinc-950/70 border-zinc-800/90 transition-all"
            >
              {/* Header card info */}
              <div
                className="flex items-center justify-between cursor-pointer select-none"
                onClick={() => toggleExpand(idx)}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <span className="flex h-5 w-5 items-center justify-center rounded bg-zinc-800 text-[10px] font-mono font-bold text-zinc-400">
                    #{idx + 1}
                  </span>
                  <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                  <span className="text-xs font-medium text-zinc-200 truncate">
                    {res.header_path || 'Conteúdo Geral'}
                  </span>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <Badge variant={res.relevance_score > 0.8 ? 'success' : 'default'}>
                    Score: {res.relevance_score.toFixed(3)}
                  </Badge>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-zinc-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-zinc-400" />
                  )}
                </div>
              </div>

              {/* Collapsible content */}
              {isExpanded && (
                <div className="space-y-3 pt-3 border-t border-zinc-800/60 text-xs">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 block mb-1">
                      Texto do Parent Chunk ({res.parent_chunk_id}):
                    </span>
                    <p className="text-zinc-300 leading-relaxed bg-zinc-900/60 p-3 rounded-lg border border-zinc-800 font-mono text-[11px] whitespace-pre-wrap">
                      {res.parent_content}
                    </p>
                  </div>

                  {hasGraph && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                        <Share2 className="w-3 h-3 text-emerald-400" />
                        Nós & Relacionamentos Conectados ({res.related_entities.length}):
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {res.related_entities.map((entity, eIdx) => (
                          <span
                            key={eIdx}
                            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 text-[11px] text-emerald-300 font-mono"
                          >
                            <span className="font-bold">{String(entity.type || 'Entity')}</span>
                            <span className="text-emerald-500/80">•</span>
                            <span>{JSON.stringify(entity.properties || {})}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};
