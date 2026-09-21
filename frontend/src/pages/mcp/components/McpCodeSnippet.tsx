import React, { useState } from 'react';
import { Copy, Check, FileCode, Terminal } from 'lucide-react';

export interface McpCodeSnippetProps {
  code: string;
  language?: string;
  title?: string;
  badge?: string;
  isCommand?: boolean;
}

export const McpCodeSnippet: React.FC<McpCodeSnippetProps> = ({
  code,
  language = 'json',
  title,
  badge,
  isCommand = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Falha ao copiar snippet', err);
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-950/80 shadow-lg shadow-black/20">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-2.5">
        <div className="flex items-center gap-2">
          {isCommand ? (
            <Terminal className="h-4 w-4 text-emerald-400" />
          ) : (
            <FileCode className="h-4 w-4 text-indigo-400" />
          )}
          {title && (
            <span className="font-mono text-xs font-semibold text-zinc-200">
              {title}
            </span>
          )}
          <span className="rounded bg-zinc-800/80 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400 border border-zinc-700/50 uppercase">
            {language}
          </span>
          {badge && (
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 border border-zinc-700/50">
              {badge}
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
            copied
              ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
              : 'bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700 hover:text-white border border-zinc-700/40'
          }`}
          title="Copiar para área de transferência"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span>Copiado!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copiar</span>
            </>
          )}
        </button>
      </div>

      {/* Code contents */}
      <div className="overflow-x-auto p-4 font-mono text-xs leading-relaxed text-zinc-200">
        <pre className="!m-0 !p-0 !bg-transparent font-mono whitespace-pre">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
};
