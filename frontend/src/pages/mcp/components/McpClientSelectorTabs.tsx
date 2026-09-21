import React, { useState } from 'react';
import {
  Bot,
  Terminal,
  FileCode,
  Laptop,
  Sparkles,
  Code2,
  Cpu,
  Boxes,
  Info,
  ExternalLink,
} from 'lucide-react';
import { McpCodeSnippet } from './McpCodeSnippet';

export interface McpClientSelectorTabsProps {
  baseUrl: string;
}

interface ClientTab {
  id: string;
  name: string;
  icon: React.ElementType;
  badge?: string;
  badgeColor?: string;
}

export const McpClientSelectorTabs: React.FC<McpClientSelectorTabsProps> = ({
  baseUrl,
}) => {
  const [activeTab, setActiveTab] = useState<string>('cursor');

  const sseUrl = `${baseUrl.replace(/\/+$/, '')}/mcp/sse`;

  const tabs: ClientTab[] = [
    { id: 'cursor', name: 'Cursor', icon: Laptop, badge: 'Popular', badgeColor: 'bg-indigo-950/80 text-indigo-300 border-indigo-800/60' },
    { id: 'claude-desktop', name: 'Claude Desktop', icon: Bot, badge: 'GUI', badgeColor: 'bg-amber-950/80 text-amber-300 border-amber-800/60' },
    { id: 'claude-code', name: 'Claude Code', icon: Terminal, badge: 'CLI', badgeColor: 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60' },
    { id: 'copilot', name: 'GitHub Copilot', icon: FileCode, badge: 'VS Code', badgeColor: 'bg-sky-950/80 text-sky-300 border-sky-800/60' },
    { id: 'antigravity', name: 'Antigravity (AGY)', icon: Cpu, badge: 'DeepMind', badgeColor: 'bg-purple-950/80 text-purple-300 border-purple-800/60' },
    { id: 'gemini-cli', name: 'Gemini CLI', icon: Sparkles, badge: 'Google', badgeColor: 'bg-blue-950/80 text-blue-300 border-blue-800/60' },
    { id: 'opencode', name: 'OpenCode', icon: Boxes, badge: 'Agent', badgeColor: 'bg-zinc-800 text-zinc-300 border-zinc-700/60' },
    { id: 'chatgpt', name: 'ChatGPT / Codex', icon: Bot, badge: 'Custom', badgeColor: 'bg-teal-950/80 text-teal-300 border-teal-800/60' },
    { id: 'python-sdk', name: 'Python SDK', icon: Code2, badge: 'mcp' },
    { id: 'node-sdk', name: 'Node.js SDK', icon: Code2, badge: 'TypeScript' },
  ];

  const cursorJson = JSON.stringify(
    {
      mcpServers: {
        'agentic-substrate': {
          url: sseUrl,
        },
      },
    },
    null,
    2
  );

  const claudeDesktopJson = JSON.stringify(
    {
      mcpServers: {
        'agentic-substrate': {
          type: 'sse',
          url: sseUrl,
        },
      },
    },
    null,
    2
  );

  const claudeCodeJson = JSON.stringify(
    {
      mcpServers: {
        'agentic-substrate': {
          type: 'sse',
          url: sseUrl,
        },
      },
    },
    null,
    2
  );

  const copilotJson = JSON.stringify(
    {
      servers: {
        'agentic-substrate': {
          type: 'sse',
          url: sseUrl,
        },
      },
    },
    null,
    2
  );

  const antigravityJson = JSON.stringify(
    {
      mcpServers: {
        'agentic-substrate': {
          serverUrl: sseUrl,
        },
      },
    },
    null,
    2
  );

  const geminiCliJson = JSON.stringify(
    {
      mcpServers: {
        'agentic-substrate': {
          url: sseUrl,
        },
      },
    },
    null,
    2
  );

  const opencodeJson = JSON.stringify(
    {
      $schema: 'https://opencode.ai/config.json',
      mcp: {
        servers: {
          'agentic-substrate': {
            type: 'remote',
            url: sseUrl,
            enabled: true,
          },
        },
      },
    },
    null,
    2
  );

  const pythonSnippet = `import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("${sseUrl}") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("Sessão MCP inicializada com sucesso!")
            
            # 1. Listar bases de conhecimento
            kbs = await session.call_tool("knowledge_list_kbs", arguments={})
            print(kbs.content[0].text)
            
            # 2. Consultar o Grafo de Conhecimento (GraphRAG)
            query_res = await session.call_tool(
                "knowledge_query",
                arguments={
                    "kb_id": "<uuid-da-kb>",
                    "query": "Quais são as principais regras?",
                    "include_graph_evidence": True
                }
            )
            print(query_res.content[0].text)

asyncio.run(main())`;

  const nodeSnippet = `import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
  const transport = new SSEClientTransport(
    new URL("${sseUrl}")
  );

  const client = new Client(
    { name: "substrate-client", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);
  console.log("Conectado ao Substrate MCP via SSE!");

  // Listar ferramentas
  const { tools } = await client.listTools();
  console.log("Ferramentas:", tools.map((t) => t.name));

  // Executar busca rápida
  const res = await client.callTool({
    name: "knowledge_search_notes",
    arguments: { kb_id: "<uuid-da-kb>", query: "conceito" },
  });
  console.log(res.content);
}

main().catch(console.error);`;

  return (
    <div className="space-y-4">
      {/* Scrollable Tabs header */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-zinc-800/80 scrollbar-thin scrollbar-thumb-zinc-800">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-zinc-800 text-white shadow-sm border border-zinc-700/60'
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent'
              }`}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-400' : 'text-zinc-500'}`} />
              <span>{tab.name}</span>
              {tab.badge && (
                <span
                  className={`rounded px-1.5 py-0.2 text-[10px] font-medium border ${
                    tab.badgeColor || 'bg-zinc-800 text-zinc-400 border-zinc-700/40'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Contents */}
      <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/30 p-5 backdrop-blur-sm">
        {activeTab === 'cursor' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Configuração no Cursor</span>
                <span className="text-xs font-normal text-zinc-400 font-mono">
                  (Global ou por Workspace)
                </span>
              </h4>
              <p className="mt-1 text-xs text-zinc-400">
                Cole o JSON abaixo no arquivo <code className="text-indigo-300 font-mono">.cursor/mcp.json</code> no seu projeto, ou em <code className="text-indigo-300 font-mono">~/.cursor/mcp.json</code> para habilitar em todos os projetos.
              </p>
            </div>

            <McpCodeSnippet
              title=".cursor/mcp.json"
              code={cursorJson}
              language="json"
              badge="Recomendado"
            />

            <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/40 p-3.5 flex items-start gap-3 text-xs text-zinc-400">
              <Info className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-zinc-200">Alternativa Visual:</strong> Abra as preferências do Cursor em <code className="text-zinc-300">Cursor Settings &gt; Features &gt; MCP &gt; Add New MCP Server</code>. Selecione transporte <strong className="text-zinc-200">SSE</strong> e informe a URL <code className="text-indigo-300">{sseUrl}</code>.
              </div>
            </div>
          </div>
        )}

        {activeTab === 'claude-desktop' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">Configuração no Claude Desktop</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Abra as configurações do Claude Desktop em <strong className="text-zinc-200">Settings &gt; Developer &gt; Edit Config</strong> e adicione o bloco abaixo em <code className="text-indigo-300 font-mono">claude_desktop_config.json</code>:
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs font-mono text-zinc-400">
              <div className="rounded-lg bg-zinc-950/60 p-2 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase font-bold">macOS:</span>
                ~/Library/Application Support/Claude/claude_desktop_config.json
              </div>
              <div className="rounded-lg bg-zinc-950/60 p-2 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase font-bold">Windows:</span>
                %APPDATA%\Claude\claude_desktop_config.json
              </div>
            </div>

            <McpCodeSnippet
              title="claude_desktop_config.json"
              code={claudeDesktopJson}
              language="json"
            />
          </div>
        )}

        {activeTab === 'claude-code' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">Configuração no Claude Code (CLI)</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Você pode registrar o Substrate com um único comando no seu terminal, ou configurando o <code className="text-indigo-300 font-mono">.mcp.json</code> no seu repositório.
              </p>
            </div>

            <div>
              <span className="text-xs font-semibold text-zinc-300 block mb-1.5">
                Opção 1: Comando CLI direto (mais rápido)
              </span>
              <McpCodeSnippet
                title="Terminal"
                code={`claude mcp add --transport sse agentic-substrate ${sseUrl}`}
                language="bash"
                isCommand={true}
              />
            </div>

            <div>
              <span className="text-xs font-semibold text-zinc-300 block mb-1.5">
                Opção 2: Arquivo .mcp.json no projeto
              </span>
              <McpCodeSnippet
                title=".mcp.json"
                code={claudeCodeJson}
                language="json"
              />
            </div>

            <p className="text-xs text-zinc-400 flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-indigo-400" />
              <span>Valide os servidores ativos executando o comando <code className="text-indigo-300">/mcp</code> dentro da sessão do Claude Code.</span>
            </p>
          </div>
        )}

        {activeTab === 'copilot' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>GitHub Copilot (VS Code Agent Mode)</span>
                <span className="rounded bg-sky-950/80 text-sky-300 border border-sky-800/60 px-2 py-0.5 text-[10px] font-semibold">
                  Atenção ao Schema
                </span>
              </h4>
              <p className="mt-1 text-xs text-zinc-400">
                A extensão oficial do GitHub Copilot no VS Code utiliza a chave raiz <code className="text-amber-300 font-mono font-bold">"servers"</code> (e não "mcpServers") no arquivo <code className="text-indigo-300 font-mono">.vscode/mcp.json</code>.
              </p>
            </div>

            <McpCodeSnippet
              title=".vscode/mcp.json"
              code={copilotJson}
              language="json"
              badge="VS Code Workspace"
            />

            <div className="rounded-xl border border-sky-900/40 bg-sky-950/20 p-3 text-xs text-sky-200 flex items-start gap-2.5">
              <Info className="h-4 w-4 text-sky-400 shrink-0 mt-0.5" />
              <div>
                <strong>Como Ativar no Chat:</strong> Abra o painel do Copilot Chat no VS Code, alterne o dropdown para <strong>Agent Mode</strong> e clique no ícone de ferramentas para confirmar a conexão com o Substrate.
              </div>
            </div>
          </div>
        )}

        {activeTab === 'antigravity' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>Antigravity / Antigravity CLI (Google DeepMind)</span>
                <span className="rounded bg-purple-950/80 text-purple-300 border border-purple-800/60 px-2 py-0.5 text-[10px] font-semibold">
                  serverUrl Schema
                </span>
              </h4>
              <p className="mt-1 text-xs text-zinc-400">
                No Antigravity, conexões remotas via SSE utilizam o campo <code className="text-purple-300 font-mono font-bold">"serverUrl"</code> no arquivo global <code className="text-indigo-300 font-mono">~/.gemini/config/mcp_config.json</code>.
              </p>
            </div>

            <McpCodeSnippet
              title="~/.gemini/config/mcp_config.json"
              code={antigravityJson}
              language="json"
              badge="Global Config"
            />

            <p className="text-xs text-zinc-400 flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-purple-400" />
              <span>Inspecione servidores ativos no menu <strong>Additional Options (...) &gt; MCP Servers</strong> da interface do Antigravity.</span>
            </p>
          </div>
        )}

        {activeTab === 'gemini-cli' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">Google Gemini CLI</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Adicione o Substrate com o comando CLI do Gemini ou no arquivo de configurações <code className="text-indigo-300 font-mono">~/.gemini/settings.json</code>.
              </p>
            </div>

            <McpCodeSnippet
              title="Terminal (CLI)"
              code={`gemini mcp add agentic-substrate --url ${sseUrl}`}
              language="bash"
              isCommand={true}
            />

            <McpCodeSnippet
              title="~/.gemini/settings.json"
              code={geminiCliJson}
              language="json"
            />
          </div>
        )}

        {activeTab === 'opencode' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <span>OpenCode</span>
                <span className="rounded bg-zinc-800 text-zinc-300 border border-zinc-700/60 px-2 py-0.5 text-[10px] font-semibold">
                  type: remote
                </span>
              </h4>
              <p className="mt-1 text-xs text-zinc-400">
                O OpenCode aceita registro via CLI ou pelo arquivo <code className="text-indigo-300 font-mono">opencode.json</code> com <code className="text-zinc-300 font-mono">"type": "remote"</code>.
              </p>
            </div>

            <McpCodeSnippet
              title="Terminal (CLI)"
              code={`opencode mcp add agentic-substrate --url ${sseUrl}`}
              language="bash"
              isCommand={true}
            />

            <McpCodeSnippet
              title="opencode.json"
              code={opencodeJson}
              language="json"
            />
          </div>
        )}

        {activeTab === 'chatgpt' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">ChatGPT &amp; OpenAI Custom Connectors</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Para conectar o ChatGPT ou agentes baseados em OpenAI aos tools do Substrate, utilize a interface de Custom Connectors no Developer Mode.
              </p>
            </div>

            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 space-y-3 text-xs text-zinc-300">
              <div className="flex items-center gap-2 font-semibold text-white">
                <ExternalLink className="h-4 w-4 text-indigo-400" />
                Passo a Passo de Configuração:
              </div>
              <ol className="list-decimal list-inside space-y-1.5 text-zinc-400 leading-relaxed">
                <li>Acesse <strong>Settings &gt; Connected Apps / Developer Mode</strong> no ChatGPT.</li>
                <li>Selecione <strong>Add MCP Server</strong>.</li>
                <li>Informe o nome: <code className="text-zinc-200">agentic-substrate</code>.</li>
                <li>Cole a URL HTTPS do seu endpoint SSE:</li>
              </ol>

              <McpCodeSnippet
                title="URL de Conexão MCP (HTTPS)"
                code={sseUrl}
                language="text"
                badge="SSE Endpoint"
              />

              <p className="text-[11px] text-zinc-500 pt-2 border-t border-zinc-800/80">
                <strong>Nota:</strong> O ChatGPT exige uma URL pública HTTPS com certificado válido. Se estiver em ambiente local de desenvolvimento, utilize um túnel como <code className="text-zinc-300">ngrok http 8000</code> ou <code className="text-zinc-300">cloudflared</code>.
              </p>
            </div>
          </div>
        )}

        {activeTab === 'python-sdk' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">Integração Programática em Python (SDK Oficial)</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Ideal para agentes construídos com LangGraph, CrewAI, AutoGen ou scripts autônomos. Requer o pacote <code className="text-indigo-300 font-mono">mcp</code> instalado (<code className="text-zinc-300 font-mono">pip install mcp</code>).
              </p>
            </div>

            <McpCodeSnippet
              title="agent_client.py"
              code={pythonSnippet}
              language="python"
            />
          </div>
        )}

        {activeTab === 'node-sdk' && (
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-bold text-white">Integração em Node.js &amp; TypeScript</h4>
              <p className="mt-1 text-xs text-zinc-400">
                Utilize o SDK oficial da Anthropic (<code className="text-indigo-300 font-mono">npm install @modelcontextprotocol/sdk</code>) para conectar microserviços em Node.js ou bots Discord/Slack.
              </p>
            </div>

            <McpCodeSnippet
              title="agentClient.ts"
              code={nodeSnippet}
              language="typescript"
            />
          </div>
        )}
      </div>
    </div>
  );
};
