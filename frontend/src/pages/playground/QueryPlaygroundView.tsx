import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Sparkles, Sliders, Database, Cpu, ShieldCheck } from 'lucide-react';
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

interface TopKConfig {
  topK: number;
  label: string;
  budget: number;
  description: string;
}

const TOP_K_CONFIGS: TopKConfig[] = [
  {
    topK: 1,
    label: 'Top 1 chunk/nó • 2.000 tokens máx',
    budget: 2000,
    description: '1 parent chunk (~1.200 tokens) + margem de segurança',
  },
  {
    topK: 3,
    label: 'Top 3 chunks/nós • 4.500 tokens máx (Recomendado)',
    budget: 4500,
    description: 'Até 3 parent chunks com 25% de margem contra truncamento',
  },
  {
    topK: 5,
    label: 'Top 5 chunks/nós • 7.500 tokens máx',
    budget: 7500,
    description: 'Até 5 parent chunks expandidos no grafo com folga de segurança',
  },
  {
    topK: 10,
    label: 'Top 10 chunks/nós • 15.000 tokens máx',
    budget: 15000,
    description: 'Até 10 parent chunks para consultas amplas de alta abrangência',
  },
];

const getSafeTokenBudgetForTopK = (k: number): number => {
  const found = TOP_K_CONFIGS.find((c) => c.topK === k);
  if (found) return found.budget;
  return Math.min(32000, Math.max(2000, k * 1500));
};

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
  const currentBudget = getSafeTokenBudgetForTopK(topK);
  const currentConfig = TOP_K_CONFIGS.find((c) => c.topK === topK);

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
    const tokenBudget = getSafeTokenBudgetForTopK(topK);

    try {
      const res = await ragMutation.mutateAsync({
        kbId: selectedKbId,
        payload: {
          query,
          top_k: Number(topK) || 3,
          mode,
          max_tokens_budget: tokenBudget,
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

            <div className="w-full sm:w-64">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-indigo-400" />
                Top-K Evidências & Token Budget
              </label>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                {TOP_K_CONFIGS.map((cfg) => (
                  <option key={cfg.topK} value={cfg.topK}>
                    {cfg.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Token Budget Info Banner */}
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/40 px-3.5 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-zinc-300">
              <Cpu className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>
                Orçamento de Retrieval:{' '}
                <strong className="text-zinc-100 font-mono">
                  {currentBudget.toLocaleString()} tokens
                </strong>
                <span className="text-zinc-500 ml-1.5">
                  ({currentConfig?.description || `${topK} chunks com margem segura`})
                </span>
              </span>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-emerald-400/90 shrink-0 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Margem anti-truncamento ativa</span>
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
            <EvidenceInspector
              results={queryResponse.results}
              retrievalTrace={queryResponse.retrieval_trace}
              totalTokensEstimated={queryResponse.total_tokens_estimated}
            />
          </div>
        )}
      </div>
    </PageContainer>
  );
};

