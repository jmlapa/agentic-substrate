import React, { useState, useEffect, useRef } from 'react';
import { Search, Hash, FileText, X, CornerDownLeft } from 'lucide-react';
import { knowledgeApi } from '../../api/knowledge-api';
import { QuickSearchResult } from '../../api/types';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  kbId: string;
  onSelectResult: (docId: string, anchor?: string) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  kbId,
  onSelectResult,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<QuickSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (!isOpen || !kbId) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    const timer = setTimeout(async () => {
      try {
        const data = await knowledgeApi.quickSearchNotes(kbId, trimmed, 10);
        setResults(data.results);
        setSelectedIndex(0);
      } catch (err) {
        console.error('Falha na busca rápida do Command Palette', err);
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, isOpen, kbId]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (results.length > 0 ? (prev + 1) % results.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) =>
        results.length > 0 ? (prev - 1 + results.length) % results.length : 0
      );
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (results[selectedIndex]) {
        const item = results[selectedIndex];
        onSelectResult(item.document_id, item.anchor);
        onClose();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-zinc-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div
        className="w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-zinc-800 bg-zinc-900/90">
          <Search className="w-4 h-4 text-indigo-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar notas por título, seções ou conteúdo..."
            className="flex-1 bg-transparent border-0 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-0"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="p-1 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          <kbd className="hidden sm:inline-block text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {isLoading && (
            <div className="py-6 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
              <span className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              Pesquisando nas notas...
            </div>
          )}

          {!isLoading && query.trim() && results.length === 0 && (
            <div className="py-8 text-center text-xs text-zinc-500">
              Nenhuma nota ou seção encontrada para &ldquo;{query}&rdquo;.
            </div>
          )}

          {!isLoading && !query.trim() && (
            <div className="py-8 text-center text-xs text-zinc-500">
              Digite uma palavra-chave para buscar entre todos os documentos e seções desta Knowledge Base.
            </div>
          )}

          {!isLoading &&
            results.map((item, idx) => {
              const isSelected = selectedIndex === idx;
              return (
                <button
                  key={`${item.document_id}-${item.anchor || item.match_type}-${idx}`}
                  onClick={() => {
                    onSelectResult(item.document_id, item.anchor);
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full flex items-start justify-between gap-3 p-2.5 rounded-lg text-left transition-colors ${
                    isSelected
                      ? 'bg-indigo-950/60 border border-indigo-800/80 text-zinc-100'
                      : 'hover:bg-zinc-800/50 text-zinc-300 border border-transparent'
                  }`}
                >
                  <div className="flex items-start gap-2.5 min-w-0 flex-1">
                    <div className="mt-0.5 p-1 rounded bg-zinc-800 text-indigo-400 shrink-0">
                      {item.match_type === 'header' ? (
                        <Hash className="w-3.5 h-3.5" />
                      ) : (
                        <FileText className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-zinc-100 truncate">
                          {item.matched_title}
                        </span>
                        <span className="text-[10px] text-zinc-500 truncate">
                          em {item.document_name}
                        </span>
                      </div>
                      {item.preview && (
                        <p className="text-[11px] text-zinc-400 line-clamp-1 mt-0.5">
                          {item.preview}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0 self-center">
                    <span
                      className={`text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded border ${
                        item.match_type === 'header'
                          ? 'bg-purple-950/80 border-purple-800 text-purple-300'
                          : 'bg-zinc-800 border-zinc-700 text-zinc-400'
                      }`}
                    >
                      {item.match_type === 'header' ? 'Seção' : 'Nota'}
                    </span>
                    {isSelected && (
                      <CornerDownLeft className="w-3 h-3 text-indigo-400" />
                    )}
                  </div>
                </button>
              );
            })}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-zinc-950/60 border-t border-zinc-800/80 flex items-center justify-between text-[11px] text-zinc-500">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono bg-zinc-800 px-1 py-0.5 rounded text-zinc-400 border border-zinc-700">
                ↑
              </kbd>{' '}
              <kbd className="font-mono bg-zinc-800 px-1 py-0.5 rounded text-zinc-400 border border-zinc-700">
                ↓
              </kbd>{' '}
              para navegar
            </span>
            <span>
              <kbd className="font-mono bg-zinc-800 px-1 py-0.5 rounded text-zinc-400 border border-zinc-700">
                Enter
              </kbd>{' '}
              para abrir
            </span>
          </div>
          <span>Pressione ESC para fechar</span>
        </div>
      </div>
    </div>
  );
};
