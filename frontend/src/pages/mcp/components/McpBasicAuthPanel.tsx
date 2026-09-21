import React, { useState } from 'react';
import {
  Lock,
  Unlock,
  KeyRound,
  Eye,
  EyeOff,
  Copy,
  Check,
  ShieldAlert,
  Info,
} from 'lucide-react';
import { buildBasicAuthHeader } from '../../../utils/mcpAuth';

export interface McpBasicAuthPanelProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  username: string;
  onUsernameChange: (username: string) => void;
  password: string;
  onPasswordChange: (password: string) => void;
}

export const McpBasicAuthPanel: React.FC<McpBasicAuthPanelProps> = ({
  enabled,
  onToggle,
  username,
  onUsernameChange,
  password,
  onPasswordChange,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [copiedHeader, setCopiedHeader] = useState(false);

  const authHeader = buildBasicAuthHeader(username, password);

  const handleCopyHeader = async () => {
    if (!authHeader) return;
    try {
      await navigator.clipboard.writeText(authHeader);
      setCopiedHeader(true);
      setTimeout(() => setCopiedHeader(false), 2000);
    } catch (err) {
      console.error('Erro ao copiar header', err);
    }
  };

  return (
    <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/40 p-4 sm:p-5 backdrop-blur-sm transition-all">
      {/* Header bar with toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
              enabled
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : 'bg-zinc-800/80 border-zinc-700/50 text-zinc-400'
            }`}
          >
            {enabled ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <span>Autenticação Caddy (HTTP Basic Auth)</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold border ${
                  enabled
                    ? 'bg-amber-950/80 text-amber-300 border-amber-800/60'
                    : 'bg-zinc-800 text-zinc-400 border-zinc-700/50'
                }`}
              >
                {enabled ? 'Ativado' : 'Opcional / Desativado'}
              </span>
            </h3>
            <p className="text-xs text-zinc-400">
              Necessário quando o Caddy protege o ambiente via{' '}
              <code className="text-zinc-300 font-mono">deploy/vm/rules/auth.caddy</code>.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onToggle(!enabled)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
            enabled
              ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border-amber-500/40 shadow-sm'
              : 'bg-zinc-800 hover:bg-zinc-700/80 text-zinc-300 border-zinc-700/60'
          }`}
        >
          <span>{enabled ? 'Desativar Autenticação' : 'Configurar Credenciais'}</span>
        </button>
      </div>

      {/* Expanded form when enabled */}
      {enabled && (
        <div className="mt-4 space-y-4 animate-fadeIn">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1.5">
                Usuário (Username)
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => onUsernameChange(e.target.value)}
                placeholder="Ex: admin"
                className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-xs text-zinc-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-zinc-400 uppercase tracking-wider mb-1.5">
                Senha (Password)
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => onPasswordChange(e.target.value)}
                  placeholder="Sua senha da regra Caddy"
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950/80 pl-3 pr-9 py-2 text-xs text-zinc-200 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-3.5 w-3.5" />
                  ) : (
                    <Eye className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Generated Header Display */}
          {authHeader && (
            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/60 p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
              <div className="flex items-center gap-2 overflow-hidden">
                <KeyRound className="h-4 w-4 text-amber-400 shrink-0" />
                <div className="text-xs truncate">
                  <span className="text-zinc-500 font-mono text-[11px] mr-2">
                    Header Gerado:
                  </span>
                  <code className="text-amber-300 font-mono text-xs">{authHeader}</code>
                </div>
              </div>

              <button
                type="button"
                onClick={handleCopyHeader}
                className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700/90 text-zinc-200 px-2.5 py-1 text-xs font-medium border border-zinc-700/60 shrink-0 transition-colors"
              >
                {copiedHeader ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-300">Copiado</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 text-zinc-400" />
                    <span>Copiar Header</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Security Architecture Note */}
          <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/40 p-3.5 space-y-2 text-xs text-zinc-400">
            <div className="flex items-center gap-2 text-zinc-200 font-semibold">
              <ShieldAlert className="h-4 w-4 text-amber-400" />
              <span>Por que usamos Headers HTTP em vez de credenciais na URL?</span>
            </div>
            <p className="leading-relaxed text-[11px] text-zinc-400">
              A RFC 3986 (seção 3.2.1) e as diretrizes do OWASP <strong>depreciam formalmente</strong> o uso de senhas expostas diretamente na URL (<code className="text-zinc-300 font-mono">https://user:pass@host</code>), pois credenciais embutidas na URI vazam em logs de proxy, históricos de terminal e cabeçalhos Referer. Além disso, muitos runtimes de agentes (como extensões VS Code e browsers modernos) descartam ou bloqueiam a submissão de credenciais via URI em conexões SSE/POST.
            </p>
            <p className="leading-relaxed text-[11px] text-zinc-400 flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
              <span>
                As configurações abaixo utilizam o padrão seguro <strong>RFC 7617</strong> via chave <code className="text-indigo-300 font-mono">headers</code>, garantindo autenticação íntegra tanto no stream SSE quanto nas chamadas POST de ferramentas.
              </span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
