import React, { useState } from 'react';
import {
  Sparkles,
  X,
  Send,
  FileText,
  Globe,
  Layers,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { knowledgeApi } from '../../api/knowledge-api';
import { HybridSearchResult } from '../../api/types';
import { MarkdownRenderer } from '../ui/MarkdownRenderer';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  scope: 'doc' | 'kb';
  results?: HybridSearchResult[];
}

interface DocumentChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  kbId: string;
  kbName: string;
  documentId?: string;
  documentName?: string;
}

export const DocumentChatDrawer: React.FC<DocumentChatDrawerProps> = ({
  isOpen,
  onClose,
  kbId,
  kbName,
  documentId,
  documentName,
}) => {
  const [scope, setScope] = useState<'doc' | 'kb'>(() => (documentId ? 'doc' : 'kb'));
  const [inputQuery, setInputQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedEvidenceId, setExpandedEvidenceId] = useState<string | null>(null);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      scope: scope,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await knowledgeApi.queryBase(kbId, {
        query,
        document_id: scope === 'doc' && documentId ? documentId : null,
        mode: 'synthesis',
        top_k: 5,
      });

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        scope: scope,
        results: response.results,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error('Erro ao consultar assistente de IA', err);
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Ocorreu um erro ao consultar a base de conhecimento. Verifique sua conexão e tente novamente.',
        scope: scope,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <aside className="w-96 bg-zinc-900 border-l border-zinc-800 flex flex-col h-full shrink-0 shadow-2xl z-30 animate-in slide-in-from-right duration-200">
      {/* Drawer Header */}
      <div className="p-3.5 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/90">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-indigo-950 border border-indigo-800 text-indigo-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-100">Assistente Contextual</h3>
            <p className="text-[10px] text-zinc-500 truncate max-w-[200px]">
              {scope === 'doc' && documentName ? documentName : kbName}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scope Selector */}
      <div className="px-3 py-2 bg-zinc-950/60 border-b border-zinc-800/80 flex items-center gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          Escopo:
        </span>
        <div className="flex-1 flex rounded-md bg-zinc-900 p-0.5 border border-zinc-800 text-[11px]">
          <button
            type="button"
            disabled={!documentId}
            onClick={() => setScope('doc')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2 rounded font-medium transition-colors ${
              scope === 'doc'
                ? 'bg-indigo-950 text-indigo-200 border border-indigo-700/60 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed'
            }`}
            title={documentId ? `Buscar apenas em ${documentName}` : 'Nenhum documento aberto'}
          >
            <FileText className="w-3 h-3 text-indigo-400" />
            <span className="truncate">Doc Atual</span>
          </button>
          <button
            type="button"
            onClick={() => setScope('kb')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2 rounded font-medium transition-colors ${
              scope === 'kb'
                ? 'bg-indigo-950 text-indigo-200 border border-indigo-700/60 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            title={`Buscar em toda a KB (${kbName})`}
          >
            <Globe className="w-3 h-3 text-indigo-400" />
            <span className="truncate">Toda a KB</span>
          </button>
        </div>
      </div>

      {/* Message Thread */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3.5">
        {messages.length === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-500 space-y-2">
            <Sparkles className="w-6 h-6 text-indigo-400/60 mx-auto" />
            <p className="font-medium text-zinc-300">Tire dúvidas sobre o documento</p>
            <p className="text-[11px] text-zinc-500 max-w-[240px] mx-auto">
              Pergunte sobre resumos, regras, definições ou dados contidos nesta nota.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`space-y-1.5 text-xs ${
                msg.role === 'user' ? 'text-right' : 'text-left'
              }`}
            >
              {/* Message Bubble */}
              <div
                className={`inline-block p-3 rounded-xl max-w-[90%] text-left ${
                  msg.role === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none font-medium'
                    : 'bg-zinc-800/80 border border-zinc-700/60 text-zinc-200 rounded-bl-none'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <MarkdownRenderer content={msg.content} />
                )}
              </div>

              {/* Scope badge & Evidence toggle */}
              {msg.role === 'assistant' && msg.results && msg.results.length > 0 && (
                <div className="pt-1">
                  <button
                    onClick={() =>
                      setExpandedEvidenceId(
                        expandedEvidenceId === msg.id ? null : msg.id
                      )
                    }
                    className="inline-flex items-center gap-1.5 text-[10px] text-zinc-400 hover:text-indigo-300 font-medium px-2 py-0.5 rounded bg-zinc-950/80 border border-zinc-800"
                  >
                    <Layers className="w-3 h-3 text-indigo-400" />
                    <span>{msg.results.length} fontes consultadas</span>
                    {expandedEvidenceId === msg.id ? (
                      <ChevronUp className="w-2.5 h-2.5" />
                    ) : (
                      <ChevronDown className="w-2.5 h-2.5" />
                    )}
                  </button>

                  {/* Evidence Drawer */}
                  {expandedEvidenceId === msg.id && (
                    <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-indigo-500/50">
                      {msg.results.map((res, rIdx) => (
                        <div
                          key={`${res.parent_chunk_id}-${rIdx}`}
                          className="p-2 rounded bg-zinc-950/90 border border-zinc-800 text-[11px] text-zinc-300 space-y-1"
                        >
                          <div className="flex items-center justify-between text-indigo-300 font-medium text-[10px]">
                            <span className="truncate">{res.document_name}</span>
                            <span className="font-mono text-zinc-500">
                              {(res.relevance_score * 100).toFixed(0)}% match
                            </span>
                          </div>
                          <p className="text-zinc-400 line-clamp-2 text-[10px] italic">
                            &ldquo;{res.parent_content}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-indigo-300 bg-indigo-950/30 p-2.5 rounded-lg border border-indigo-800/40 animate-pulse">
            <Sparkles className="w-3.5 h-3.5 animate-spin text-indigo-400" />
            <span>Sintetizando resposta contextual...</span>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="p-3 border-t border-zinc-800 bg-zinc-900/90">
        <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-800 rounded-lg p-1.5 focus-within:border-indigo-600 transition-colors">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={
              scope === 'doc'
                ? `Perguntar sobre ${documentName || 'este doc'}...`
                : `Perguntar em toda a KB (${kbName})...`
            }
            className="flex-1 bg-transparent border-0 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-0 px-2"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isLoading}
            className="p-1.5 rounded-md bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </form>
    </aside>
  );
};
