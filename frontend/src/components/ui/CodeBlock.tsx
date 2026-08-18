import React, { useState } from 'react';
import { Copy, Check, Code2 } from 'lucide-react';

export interface CodeBlockProps {
  language?: string;
  value: string;
  className?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  language = 'text',
  value,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code to clipboard', err);
    }
  };

  const displayLanguage = language.replace(/^language-/, '').trim() || 'text';

  return (
    <div
      className={`my-3 overflow-hidden rounded-lg border border-zinc-800/80 bg-zinc-950/90 shadow-lg shadow-black/20 ${className}`}
    >
      {/* Code Header Bar */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-3.5 py-1.5">
        <div className="flex items-center gap-2 text-xs text-zinc-400 font-mono">
          <Code2 className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-zinc-300 uppercase tracking-wider text-[10px]">
            {displayLanguage}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200 focus:outline-none"
          title="Copiar código"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copiado</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-zinc-400" />
              <span>Copiar</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div className="overflow-x-auto p-4 text-xs font-mono leading-relaxed text-zinc-200">
        <pre className="!bg-transparent !p-0 !m-0 font-mono">
          <code>{value}</code>
        </pre>
      </div>
    </div>
  );
};
