import React from 'react';
import { Wrench, Sparkles, Terminal, ArrowRight } from 'lucide-react';
import { McpToolInfo } from '../../../api/mcp-api';
import { Badge } from '../../../components/ui/Badge';

export interface McpToolsCatalogProps {
  tools: McpToolInfo[];
}

export const McpToolsCatalog: React.FC<McpToolsCatalogProps> = ({ tools }) => {
  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'GraphRAG':
        return <Badge variant="purple">{category}</Badge>;
      case 'Discovery':
        return <Badge variant="info">{category}</Badge>;
      case 'Fast-Path':
        return <Badge variant="success">{category}</Badge>;
      default:
        return <Badge variant="default">{category}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-300">
            Catálogo Dinâmico de Ferramentas ({tools.length})
          </h3>
        </div>
        <span className="text-xs text-zinc-500 font-mono">
          Introspecção via <code>GET /api/v1/mcp/info</code>
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {tools.map((tool) => (
          <div
            key={tool.name}
            className="flex flex-col justify-between rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 transition-all hover:border-zinc-700/80 hover:bg-zinc-900/60 shadow-md"
          >
            <div>
              {/* Header */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <Terminal className="h-4 w-4 text-zinc-400" />
                  <span className="font-mono text-sm font-bold text-white">
                    {tool.name}
                  </span>
                </div>
                {getCategoryBadge(tool.category)}
              </div>

              {/* Description */}
              <p className="mt-2.5 text-xs text-zinc-400 leading-relaxed min-h-[48px]">
                {tool.description}
              </p>

              {/* Parameters */}
              <div className="mt-4 pt-3 border-t border-zinc-800/60">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 block mb-2">
                  Parâmetros Aceitos:
                </span>

                {tool.parameters.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic">
                    Nenhum parâmetro necessário (chamada sem argumentos).
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {tool.parameters.map((param) => (
                      <li
                        key={param.name}
                        className="rounded-lg bg-zinc-950/60 border border-zinc-800/50 p-2 text-xs"
                      >
                        <div className="flex items-center justify-between gap-1 flex-wrap">
                          <span className="font-mono font-semibold text-zinc-200">
                            {param.name}
                          </span>
                          <div className="flex items-center gap-1">
                            <span className="text-[10px] font-mono text-zinc-400 bg-zinc-800/80 rounded px-1.5 py-0.5">
                              {param.type}
                            </span>
                            {param.required ? (
                              <span className="text-[10px] font-semibold text-rose-400 bg-rose-950/60 rounded px-1 py-0.5 border border-rose-900/40">
                                obrigatório
                              </span>
                            ) : (
                              <span className="text-[10px] text-zinc-500 bg-zinc-900 rounded px-1 py-0.5">
                                opcional
                              </span>
                            )}
                          </div>
                        </div>
                        {param.description && (
                          <p className="mt-1 text-[11px] text-zinc-400">
                            {param.description}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Footer capability hint */}
            <div className="mt-4 pt-2 flex items-center gap-1 text-[11px] text-indigo-400 font-medium">
              <Sparkles className="h-3 w-3" />
              <span>Invocável via JSON-RPC 2.0</span>
              <ArrowRight className="h-3 w-3 ml-auto text-zinc-600" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
