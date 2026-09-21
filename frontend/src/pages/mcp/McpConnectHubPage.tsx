import React, { useState, useEffect } from 'react';
import { PageContainer } from '../../components/layout/PageContainer';
import { useMcpInfo } from '../../hooks/useMcpInfo';
import { McpHealthBanner } from './components/McpHealthBanner';
import { McpClientSelectorTabs } from './components/McpClientSelectorTabs';
import { McpToolsCatalog } from './components/McpToolsCatalog';
import { Network, Zap, ShieldCheck } from 'lucide-react';
import { McpToolInfo } from '../../api/mcp-api';

const DEFAULT_DEV_API_URL = 'http://localhost:8000';

const FALLBACK_TOOLS: McpToolInfo[] = [
  {
    name: 'knowledge_query',
    description:
      'Consulta o grafo de conhecimento (GraphRAG) para responder perguntas complexas com síntese fact-dense e citações de fontes documentais.',
    category: 'GraphRAG',
    parameters: [
      {
        name: 'kb_id',
        type: 'string',
        required: true,
        description: 'UUID identificador da Base de Conhecimento a consultar.',
      },
      {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Pergunta ou consulta em linguagem natural a ser respondida.',
      },
      {
        name: 'include_graph_evidence',
        type: 'boolean',
        required: false,
        description: 'Se True, anexa as triplas ontológicas e entidades relacionadas na resposta.',
      },
    ],
  },
  {
    name: 'knowledge_list_kbs',
    description:
      'Lista todas as bases de conhecimento (Knowledge Bases) registradas no Substrate, incluindo id, nome, descrição, status e total de documentos vinculados.',
    category: 'Discovery',
    parameters: [],
  },
  {
    name: 'knowledge_search_notes',
    description:
      'Busca rápida por palavras-chave, títulos e trechos em uma Base de Conhecimento (fast-path direto, sem consumo de tokens com LLM).',
    category: 'Fast-Path',
    parameters: [
      {
        name: 'kb_id',
        type: 'string',
        required: true,
        description: 'UUID identificador da Base de Conhecimento a pesquisar.',
      },
      {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Termo, palavra-chave ou título de seção procurado.',
      },
      {
        name: 'limit',
        type: 'integer',
        required: false,
        description: 'Quantidade máxima de resultados a retornar (1 a 50, padrão 10).',
      },
    ],
  },
];

export const McpConnectHubPage: React.FC = () => {
  const { data: mcpInfo, isLoading, isError } = useMcpInfo();

  const computeDefaultBaseUrl = (): string => {
    if (typeof window === 'undefined') return DEFAULT_DEV_API_URL;
    const isLocalhost =
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';
    return isLocalhost ? DEFAULT_DEV_API_URL : window.location.origin;
  };

  const [baseUrl, setBaseUrl] = useState<string>(computeDefaultBaseUrl);

  useEffect(() => {
    setBaseUrl(computeDefaultBaseUrl());
  }, []);

  const handleResetBaseUrl = () => {
    setBaseUrl(computeDefaultBaseUrl());
  };

  const serverStatus: 'online' | 'offline' | 'loading' = isLoading
    ? 'loading'
    : isError || !mcpInfo
    ? 'offline'
    : 'online';

  const toolsList = mcpInfo?.tools || FALLBACK_TOOLS;

  return (
    <PageContainer
      title="Substrate MCP Hub"
      description="Conecte Cursor, Claude, GitHub Copilot, Antigravity e outros coding agents diretamente ao grafo de conhecimento do Substrate via Model Context Protocol (HTTP/SSE)."
    >
      <div className="space-y-8 pb-12">
        {/* 1. Health Status Banner */}
        <McpHealthBanner
          status={serverStatus}
          baseUrl={baseUrl}
          onBaseUrlChange={setBaseUrl}
          onResetBaseUrl={handleResetBaseUrl}
          toolsCount={toolsList.length}
          transport={mcpInfo?.transport || 'sse'}
          version={mcpInfo?.version ? `v${mcpInfo.version}` : 'v0.8.0'}
        />

        {/* 2. Client Quickstart Tabs */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-300">
              Configuração Rápida por Agente
            </h3>
          </div>
          <McpClientSelectorTabs baseUrl={baseUrl} />
        </div>

        {/* 3. Dynamic Tools Catalog */}
        <McpToolsCatalog tools={toolsList} />

        {/* 4. Architecture & Security Notice */}
        <div className="rounded-xl border border-zinc-800/60 bg-zinc-900/20 p-5 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-400">
          <div className="flex items-start gap-3">
            <Network className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-zinc-200 text-sm">
                Execução In-Process com Zero Latência
              </h4>
              <p className="mt-1 leading-relaxed">
                As ferramentas MCP rodam no mesmo processo do Gateway com injeção de dependências no <code>AppContainer</code>, dispensando proxies HTTP intermediários ou serializações redundantes.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-zinc-200 text-sm">
                Streaming Desbufferizado no Caddy
              </h4>
              <p className="mt-1 leading-relaxed">
                Em ambientes de produção na nuvem, o proxy Caddy opera com <code>flush_interval -1</code> na rota <code>/mcp/*</code>, garantindo entrega instantânea dos quadros SSE sem congelamento de stream.
              </p>
            </div>
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
