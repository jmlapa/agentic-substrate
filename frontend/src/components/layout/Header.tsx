import React from 'react';
import { ExternalLink, Terminal } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="h-16 border-b border-zinc-800/80 bg-zinc-950/60 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-zinc-500 bg-zinc-900 border border-zinc-800 px-2.5 py-1 rounded-md flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          agentic-substrate-console
        </span>
      </div>

      <div className="flex items-center gap-3">
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors bg-zinc-900/50 hover:bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg"
        >
          <span>Documentação API</span>
          <ExternalLink className="w-3 h-3 text-zinc-500" />
        </a>
      </div>
    </header>
  );
};
