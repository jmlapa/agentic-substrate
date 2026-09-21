import React, { useState } from 'react';
import { Activity, Check, Copy, Globe, RefreshCw, Sparkles } from 'lucide-react';
import { Badge } from '../../../components/ui/Badge';

export interface McpHealthBannerProps {
  status: 'online' | 'offline' | 'loading';
  baseUrl: string;
  onBaseUrlChange: (url: string) => void;
  onResetBaseUrl: () => void;
  toolsCount: number;
  transport?: string;
  version?: string;
}

export const McpHealthBanner: React.FC<McpHealthBannerProps> = ({
  status,
  baseUrl,
  onBaseUrlChange,
  onResetBaseUrl,
  toolsCount,
  transport = 'sse',
  version = 'v0.8.0',
}) => {
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const sseEndpoint = `${baseUrl.replace(/\/+$/, '')}/mcp/sse`;

  const handleCopyEndpoint = async () => {
    try {
      await navigator.clipboard.writeText(sseEndpoint);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } catch (err) {
      console.error('Falha ao copiar URL do endpoint', err);
    }
  };

  return (
    <div className="rounded-2xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 p-5 shadow-xl shadow-black/40 backdrop-blur-md">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        {/* Left column: Status & Badges */}
        <div className="flex items-start gap-3.5">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shadow-inner">
            <Activity className="h-5 w-5" />
          </div>

          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-base font-bold text-white tracking-tight">
                Substrate MCP Server
              </h2>
              <Badge variant="purple" size="sm">
                {version}
              </Badge>

              {status === 'online' && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-950/70 border border-emerald-800/60 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  SSE Ready & Online
                </span>
              )}

              {status === 'loading' && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-950/70 border border-amber-800/60 px-2.5 py-0.5 text-xs font-semibold text-amber-300">
                  <RefreshCw className="h-3 w-3 animate-spin text-amber-400" />
                  Verificando...
                </span>
              )}

              {status === 'offline' && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-950/70 border border-rose-800/60 px-2.5 py-0.5 text-xs font-semibold text-rose-300">
                  <span className="h-2 w-2 rounded-full bg-rose-500" />
                  Offline / Inacessível
                </span>
              )}
            </div>

            <p className="mt-1 text-xs text-zinc-400 flex items-center gap-2 flex-wrap">
              <span>Transporte: <code className="text-zinc-300 font-mono uppercase">{transport}</code></span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-indigo-400" />
                <strong className="text-zinc-200">{toolsCount}</strong> ferramentas cognitivas ativas
              </span>
            </p>
          </div>
        </div>

        {/* Right column: Endpoint URL & Copy */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-xl border border-zinc-800 bg-zinc-950/90 px-3 py-1.5 shadow-inner">
            <Globe className="h-3.5 w-3.5 text-zinc-500 shrink-0" />
            {isEditing ? (
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => onBaseUrlChange(e.target.value)}
                onBlur={() => setIsEditing(false)}
                autoFocus
                className="bg-transparent font-mono text-xs text-zinc-200 focus:outline-none w-48 sm:w-64"
                placeholder="http://localhost:8000"
              />
            ) : (
              <span
                onClick={() => setIsEditing(true)}
                className="font-mono text-xs text-zinc-300 truncate max-w-[200px] sm:max-w-[280px] cursor-pointer hover:text-indigo-300 transition-colors"
                title="Clique para customizar a URL base"
              >
                {sseEndpoint}
              </span>
            )}

            <button
              type="button"
              onClick={onResetBaseUrl}
              className="text-zinc-500 hover:text-zinc-300 p-0.5 text-[10px] rounded transition-colors"
              title="Restaurar URL padrão detectada"
            >
              <RefreshCw className="h-3 w-3" />
            </button>
          </div>

          <button
            type="button"
            onClick={handleCopyEndpoint}
            className={`flex items-center justify-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold transition-all shadow-sm ${
              copiedUrl
                ? 'bg-emerald-600 text-white shadow-emerald-600/30'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20'
            }`}
          >
            {copiedUrl ? (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>URL Copiada!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copiar SSE URL</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
