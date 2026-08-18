import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Sparkles, Sliders, Database } from 'lucide-react';
import { useKnowledgeBases } from '../../hooks/useKnowledgeBases';
import { useRagQuery } from '../../hooks/useRagQuery';
import { QueryKnowledgeResponse } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { Card } from '../../components/ui/Card';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';
import { AnswerView } from './AnswerView';
import { EvidenceInspector } from './EvidenceInspector';

export const QueryPlaygroundView: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlKbId = searchParams.get('kbId') || '';

  const { data: kbsData, isLoading: loadingKbs } = useKnowledgeBases();
  const ragMutation = useRagQuery();

  const [selectedKbId, setSelectedKbId] = useState(urlKbId);
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(3);
  const [mode, setMode] = useState<'synthesis' | 'retrieve'>('synthesis');
  const [queryResponse, setQueryResponse] = useState<QueryKnowledgeResponse | null>(null);
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState('');

  const kbs = kbsData?.knowledge_bases || [];

  useEffect(() => {
    if (urlKbId) {
      setSelectedKbId(urlKbId);
    } else if (kbs.length > 0 && !selectedKbId) {
      setSelectedKbId(kbs[0].id);
    }
  }, [urlKbId, kbs, selectedKbId]);

  const handleKbChange = (newKbId: string) => {
    setSelectedKbId(newKbId);
    setSearchParams({ kbId: newKbId });
    setQueryResponse(null);
  };

  const handleExecuteQuery = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!selectedKbId || !query.trim() || ragMutation.isPending) return;

    setLastSubmittedQuery(query);
    try {
      const res = await ragMutation.mutateAsync({
        kbId: selectedKbId,
        payload: {
          query,
          top_k: Number(topK) || 3,
          mode,
        },
      });
      setQueryResponse(res);
    } catch {
      // Error handled by mutation state
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleExecuteQuery();
    }
  };

  const kbOptions = kbs.map((k) => ({
    value: k.id,
    label: `${k.name} (${k.documents_count} documentos)`,
  }));

  return (
    <PageContainer
      title="RAG Query Playground"
      description="Faça perguntas em linguagem natural e receba respostas sintetizadas com evidências recuperadas do FalkorDB GraphRAG."
    >
      <div className="space-y-8 max-w-5xl">
        {/* Controls Card */}
        <Card className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex-1 w-full sm:w-auto">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                Knowledge Base Alvo
              </label>
              {loadingKbs ? (
                <LoadingSpinner size="sm" />
              ) : (
                <Select
                  options={kbOptions}
                  value={selectedKbId}
                  onChange={(e) => handleKbChange(e.target.value)}
                  placeholder="Selecione uma Knowledge Base..."
                />
              )}
            </div>

            <div className="w-full sm:w-56">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Modo de Execução
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as 'synthesis' | 'retrieve')}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="synthesis">Síntese Fact-Dense (Gemma 4 / OpenRouter)</option>
                <option value="retrieve">Apenas Recuperação (Raw Fast-Path)</option>
              </select>
            </div>

            <div className="w-full sm:w-40">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                Top-K Evidências
              </label>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value={1}>Top 1 chunk/nó</option>
                <option value={3}>Top 3 chunks/nós</option>
                <option value={5}>Top 5 chunks/nós</option>
                <option value={10}>Top 10 chunks/nós</option>
              </select>
            </div>
          </div>

          {/* Prompt / Query Textarea */}
          <form onSubmit={handleExecuteQuery} className="space-y-3 pt-2">
            <Textarea
              label="Sua Pergunta / Consulta"
              placeholder="Digite sua dúvida sobre os documentos da Knowledge Base... (Pressione Enter para enviar)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              required
            />

            <div className="flex items-center justify-between">
              <span className="text-[11px] text-zinc-500">
                Pressione <kbd className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">Enter</kbd> para consultar ou <kbd className="bg-zinc-800 px-1.5 py-0.5 rounded text-zinc-400">Shift + Enter</kbd> para quebrar linha.
              </span>
              <Button
                type="submit"
                variant="primary"
                disabled={!selectedKbId || !query.trim() || ragMutation.isPending}
                isLoading={ragMutation.isPending}
                leftIcon={<Sparkles className="w-4 h-4" />}
              >
                {mode === 'retrieve' ? 'Recuperar Evidências' : 'Consultar RAG'}
              </Button>
            </div>
          </form>
        </Card>

        {/* Query Loading */}
        {ragMutation.isPending && (
          <LoadingSpinner
            message={
              mode === 'retrieve'
                ? 'Recuperando subgrafos e chunks estruturados no FalkorDB...'
                : 'Buscando no FalkorDB e sintetizando resposta factual com Gemma 4 (OpenRouter)...'
            }
          />
        )}

        {/* Error Banner */}
        {ragMutation.isError && (
          <ErrorBanner
            title="Erro na Consulta"
            message={ragMutation.error?.message || 'Falha ao executar consulta RAG.'}
            onRetry={() => handleExecuteQuery()}
          />
        )}

        {/* Results View */}
        {queryResponse && !ragMutation.isPending && (
          <div className="space-y-6">
            {/* LLM Synthesized Answer */}
            <AnswerView
              answer={queryResponse.answer}
              query={lastSubmittedQuery}
            />

            {/* Evidence Inspector */}
            <EvidenceInspector results={queryResponse.results} />
          </div>
        )}
      </div>
    </PageContainer>
  );
};
