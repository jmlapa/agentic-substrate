import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  BookOpen,
  Copy,
  Check,
  Search,
  FileText,
  Calendar,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { knowledgeApi } from '../../api/knowledge-api';
import {
  KnowledgeBaseSummary,
  DocumentSummary,
  DocumentContentResponse,
} from '../../api/types';
import { NotesSidebarTree } from '../../components/notes/NotesSidebarTree';
import { TableOfContents } from '../../components/notes/TableOfContents';
import { CommandPaletteModal } from '../../components/notes/CommandPaletteModal';
import { DocumentChatDrawer } from '../../components/notes/DocumentChatDrawer';
import { MarkdownRenderer } from '../../components/ui/MarkdownRenderer';

export const NotesPortalPage: React.FC = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBaseSummary[]>([]);
  const [kbDocumentsMap, setKbDocumentsMap] = useState<Record<string, DocumentSummary[]>>({});
  const [selectedKbId, setSelectedKbId] = useState<string>('');
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [documentContent, setDocumentContent] = useState<DocumentContentResponse | null>(null);

  const [isLoadingBases, setIsLoadingBases] = useState(true);
  const [isLoadingDoc, setIsLoadingDoc] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isChatDrawerOpen, setIsChatDrawerOpen] = useState(false);

  // Load KBs and their docs
  const loadInitialData = useCallback(async () => {
    setIsLoadingBases(true);
    try {
      const kbRes = await knowledgeApi.listBases();
      setKnowledgeBases(kbRes.knowledge_bases);

      if (kbRes.knowledge_bases.length > 0) {
        const firstKb = kbRes.knowledge_bases[0];
        setSelectedKbId(firstKb.id);

        // Fetch docs for all KBs
        const docsMap: Record<string, DocumentSummary[]> = {};
        for (const kb of kbRes.knowledge_bases) {
          try {
            const detail = await knowledgeApi.getBaseById(kb.id);
            docsMap[kb.id] = detail.documents;
          } catch (e) {
            console.error(`Falha ao buscar detalhes da KB ${kb.id}`, e);
          }
        }
        setKbDocumentsMap(docsMap);

        // Select first doc if available
        if (docsMap[firstKb.id] && docsMap[firstKb.id].length > 0) {
          const firstDoc = docsMap[firstKb.id][0];
          setSelectedDocId(firstDoc.id);
        }
      }
    } catch (err) {
      console.error('Falha ao carregar Knowledge Bases', err);
    } finally {
      setIsLoadingBases(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load document content whenever selectedDocId changes
  useEffect(() => {
    if (!selectedKbId || !selectedDocId) {
      setDocumentContent(null);
      return;
    }

    let isMounted = true;
    setIsLoadingDoc(true);
    knowledgeApi
      .getDocumentContent(selectedKbId, selectedDocId)
      .then((data) => {
        if (isMounted) {
          setDocumentContent(data);
        }
      })
      .catch((err) => {
        console.error('Falha ao carregar conteúdo do documento', err);
        if (isMounted) setDocumentContent(null);
      })
      .finally(() => {
        if (isMounted) setIsLoadingDoc(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedKbId, selectedDocId]);

  // Global shortcut for Command Palette (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSelectDocument = (kbId: string, docId: string) => {
    setSelectedKbId(kbId);
    setSelectedDocId(docId);
  };

  const handleCommandPaletteSelect = (docId: string, anchor?: string) => {
    setSelectedDocId(docId);
    if (anchor) {
      setTimeout(() => {
        const el = document.getElementById(anchor);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 300);
    }
  };

  const handleCopyMarkdown = () => {
    if (!documentContent?.markdown_content) return;
    navigator.clipboard.writeText(documentContent.markdown_content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const currentKb = knowledgeBases.find((kb) => kb.id === selectedKbId);
  const currentDoc = (kbDocumentsMap[selectedKbId] || []).find((d) => d.id === selectedDocId);

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* 1. Left Sidebar Tree */}
      <NotesSidebarTree
        knowledgeBases={knowledgeBases}
        selectedKbId={selectedKbId}
        selectedDocId={selectedDocId}
        kbDocumentsMap={kbDocumentsMap}
        onSelectDocument={handleSelectDocument}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* 2. Main Reader Content Area */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-zinc-950 overflow-hidden">
        {/* Document Header & Action Toolbar */}
        <header className="h-14 border-b border-zinc-800/80 px-6 flex items-center justify-between bg-zinc-900/40 shrink-0">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-xs text-zinc-400 min-w-0 truncate">
            <span className="font-semibold text-zinc-200 truncate flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              {currentKb?.name || 'Knowledge Base'}
            </span>
            {currentDoc && (
              <>
                <ChevronRight className="w-3 h-3 text-zinc-600 shrink-0" />
                <span className="text-zinc-300 font-medium truncate flex items-center gap-1">
                  <FileText className="w-3 h-3 text-zinc-500 shrink-0" />
                  {currentDoc.file_name}
                </span>
              </>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Command Palette Trigger */}
            <button
              onClick={() => setIsCommandPaletteOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:border-zinc-700 hover:text-zinc-100 transition-colors shadow-sm"
              title="Buscar (Ctrl+K)"
            >
              <Search className="w-3.5 h-3.5 text-zinc-400" />
              <span className="hidden sm:inline">Buscar</span>
              <kbd className="text-[10px] font-mono px-1 py-0.5 rounded bg-zinc-800 text-zinc-500">
                Ctrl+K
              </kbd>
            </button>

            {/* Copy Markdown */}
            {documentContent && (
              <button
                onClick={handleCopyMarkdown}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:border-zinc-700 hover:text-zinc-100 transition-colors shadow-sm"
                title="Copiar Markdown"
              >
                {isCopied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copiado!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-zinc-400" />
                    <span className="hidden sm:inline">Copiar MD</span>
                  </>
                )}
              </button>
            )}

            {/* Open AI Assistant Toggle */}
            <button
              onClick={() => setIsChatDrawerOpen((prev) => !prev)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors shadow-sm ${
                isChatDrawerOpen
                  ? 'bg-indigo-600 text-white'
                  : 'bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 hover:bg-indigo-900/60'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Assistente</span>
            </button>
          </div>
        </header>

        {/* Scrollable Reader with ToC on Right */}
        <div className="flex-1 flex overflow-y-auto">
          {isLoadingBases || isLoadingDoc ? (
            <div className="flex-1 flex items-center justify-center p-12 text-xs text-zinc-500">
              <span className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mr-2" />
              Carregando nota...
            </div>
          ) : !documentContent ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-zinc-500 space-y-3">
              <BookOpen className="w-12 h-12 text-zinc-700 stroke-1" />
              <h3 className="text-base font-semibold text-zinc-300">
                Selecione um documento para leitura
              </h3>
              <p className="text-xs text-zinc-500 max-w-sm">
                Navegue pela árvore de arquivos à esquerda ou use <kbd className="px-1.5 py-0.5 bg-zinc-800 rounded font-mono text-[10px]">Ctrl+K</kbd> para buscar rapidamente seções e notas.
              </p>
            </div>
          ) : (
            <div className="flex-1 flex max-w-7xl mx-auto w-full">
              {/* Document Markdown View */}
              <div className="flex-1 px-8 py-6 min-w-0 max-w-4xl">
                {/* Meta Header */}
                <div className="mb-6 pb-4 border-b border-zinc-800/80 space-y-2">
                  <h1 className="text-2xl font-bold text-zinc-100">
                    {documentContent.file_name}
                  </h1>
                  <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-1">
                      <Layers className="w-3.5 h-3.5 text-indigo-400" />
                      {documentContent.total_parents} seções • {documentContent.total_children} chunks
                    </span>
                    {documentContent.ingested_at && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5 text-zinc-500" />
                        {new Date(documentContent.ingested_at * 1000).toLocaleDateString('pt-BR')}
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-400">
                      {documentContent.status}
                    </span>
                  </div>
                </div>

                {/* Markdown Canonical Content */}
                <MarkdownRenderer content={documentContent.markdown_content} />
              </div>

              {/* Table of Contents (Outliner) */}
              <TableOfContents tocTree={documentContent.toc_tree} />
            </div>
          )}
        </div>
      </main>

      {/* 3. AI Assistant Contextual Chat Drawer */}
      <DocumentChatDrawer
        isOpen={isChatDrawerOpen}
        onClose={() => setIsChatDrawerOpen(false)}
        kbId={selectedKbId}
        kbName={currentKb?.name || 'Knowledge Base'}
        documentId={selectedDocId || undefined}
        documentName={currentDoc?.file_name}
      />

      {/* 4. Global Command Palette Modal (Ctrl+K) */}
      <CommandPaletteModal
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        kbId={selectedKbId}
        onSelectResult={handleCommandPaletteSelect}
      />
    </div>
  );
};
