import React, { useState } from 'react';
import {
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  FileText,
  Search,
  BookOpen,
  Image,
  Mic,
} from 'lucide-react';
import { KnowledgeBaseSummary, DocumentSummary } from '../../api/types';

interface NotesSidebarTreeProps {
  knowledgeBases: KnowledgeBaseSummary[];
  selectedKbId?: string;
  selectedDocId?: string;
  kbDocumentsMap: Record<string, DocumentSummary[]>;
  onSelectDocument: (kbId: string, docId: string) => void;
  onOpenCommandPalette: () => void;
  isCollapsed?: boolean;
}

export const NotesSidebarTree: React.FC<NotesSidebarTreeProps> = ({
  knowledgeBases,
  selectedKbId,
  selectedDocId,
  kbDocumentsMap,
  onSelectDocument,
  onOpenCommandPalette,
}) => {
  const [expandedKbs, setExpandedKbs] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    if (selectedKbId) {
      initial[selectedKbId] = true;
    } else if (knowledgeBases.length > 0) {
      initial[knowledgeBases[0].id] = true;
    }
    return initial;
  });

  const toggleKb = (kbId: string) => {
    setExpandedKbs((prev) => ({
      ...prev,
      [kbId]: !prev[kbId],
    }));
  };

  const getSourceIcon = (fileName: string) => {
    if (fileName.match(/\.(mp3|m4a|ogg|opus|wav|webm|aac|caf|amr|3gp)$/i)) {
      return <Mic className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
    }
    if (fileName.match(/\.(png|jpg|jpeg|webp|heic|heif)$/i)) {
      return <Image className="w-3.5 h-3.5 text-purple-400 shrink-0" />;
    }
    return <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />;
  };

  return (
    <aside className="w-72 bg-zinc-900/90 border-r border-zinc-800 flex flex-col h-full shrink-0 select-none">
      {/* Header & Quick Search Trigger */}
      <div className="p-3 border-b border-zinc-800/80 space-y-2.5">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            Portal de Notas
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">
            {knowledgeBases.length} KBs
          </span>
        </div>

        {/* Command Palette Trigger Button */}
        <button
          onClick={onOpenCommandPalette}
          className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg bg-zinc-950/80 border border-zinc-800 text-xs text-zinc-400 hover:border-zinc-700 hover:text-zinc-200 transition-colors shadow-inner group"
        >
          <span className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
            <span>Buscar notas...</span>
          </span>
          <kbd className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-400 border border-zinc-700">
            Ctrl+K
          </kbd>
        </button>
      </div>

      {/* Tree View */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1 text-xs">
        {knowledgeBases.length === 0 ? (
          <div className="p-4 text-center text-zinc-500 text-xs italic">
            Nenhuma Knowledge Base encontrada.
          </div>
        ) : (
          knowledgeBases.map((kb) => {
            const isExpanded = !!expandedKbs[kb.id];
            const docs = kbDocumentsMap[kb.id] || [];

            return (
              <div key={kb.id} className="space-y-0.5">
                {/* KB Node */}
                <button
                  onClick={() => toggleKb(kb.id)}
                  className={`w-full flex items-center justify-between px-2 py-1.5 rounded-md transition-colors text-left group ${
                    selectedKbId === kb.id && !selectedDocId
                      ? 'bg-indigo-950/60 text-indigo-200 font-medium'
                      : 'text-zinc-300 hover:bg-zinc-800/60 hover:text-zinc-100'
                  }`}
                >
                  <span className="flex items-center gap-1.5 min-w-0 truncate">
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                    )}
                    {isExpanded ? (
                      <FolderOpen className="w-4 h-4 text-indigo-400 shrink-0" />
                    ) : (
                      <Folder className="w-4 h-4 text-zinc-400 shrink-0 group-hover:text-zinc-300" />
                    )}
                    <span className="truncate font-semibold">{kb.name}</span>
                  </span>
                  <span className="text-[10px] text-zinc-500 px-1 py-0.5 rounded font-mono">
                    {docs.length}
                  </span>
                </button>

                {/* Documents inside KB */}
                {isExpanded && (
                  <div className="ml-4 pl-2 border-l border-zinc-800 space-y-0.5">
                    {docs.length === 0 ? (
                      <div className="py-1 px-2 text-[11px] text-zinc-500 italic">
                        Sem documentos
                      </div>
                    ) : (
                      docs.map((doc) => {
                        const isSelected =
                          selectedKbId === kb.id && selectedDocId === doc.id;
                        return (
                          <button
                            key={doc.id}
                            onClick={() => onSelectDocument(kb.id, doc.id)}
                            className={`w-full flex items-center gap-2 px-2 py-1 rounded-md transition-colors text-left group ${
                              isSelected
                                ? 'bg-indigo-900/40 text-indigo-200 border border-indigo-700/50 font-medium shadow-sm'
                                : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                            }`}
                            title={doc.file_name}
                          >
                            {getSourceIcon(doc.file_name)}
                            <span className="truncate">{doc.file_name}</span>
                          </button>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
