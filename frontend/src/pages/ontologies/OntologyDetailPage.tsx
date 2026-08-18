import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, GitFork, CircleDot, Copy, Check, Code, Layers } from 'lucide-react';
import { useOntologyDetail } from '../../hooks/useOntologies';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export const OntologyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: ontology, isLoading, isError, error, refetch } = useOntologyDetail(id);

  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'visual' | 'json'>('visual');

  const handleCopyJson = () => {
    if (!ontology) return;
    navigator.clipboard.writeText(JSON.stringify(ontology, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <PageContainer
      title={ontology ? ontology.name : 'Detalhes da Ontologia'}
      description={ontology?.description || 'Visualização do esquema ontológico'}
      actions={
        <>
          <Button
            variant="outline"
            onClick={() => navigate('/ontologies')}
            leftIcon={<ArrowLeft className="w-4 h-4" />}
          >
            Voltar
          </Button>
          <Button
            variant="secondary"
            onClick={handleCopyJson}
            leftIcon={copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          >
            {copied ? 'Copiado!' : 'Copiar JSON'}
          </Button>
        </>
      }
    >
      {isLoading && <LoadingSpinner message="Carregando detalhes da ontologia..." />}

      {isError && (
        <ErrorBanner
          message={(error as Error)?.message || 'Erro ao carregar detalhes da ontologia.'}
          onRetry={() => refetch()}
        />
      )}

      {ontology && (
        <div className="space-y-6">
          {/* Header Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-indigo-950/80 border border-indigo-800 text-indigo-400">
                <GitFork className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Versão do Schema</p>
                <p className="text-base font-bold text-zinc-100">v{ontology.version}</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-emerald-950/80 border border-emerald-800 text-emerald-400">
                <CircleDot className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Tipos de Nós</p>
                <p className="text-base font-bold text-zinc-100">{ontology.node_types.length} Entidades</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-purple-950/80 border border-purple-800 text-purple-400">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">Tipos de Relações</p>
                <p className="text-base font-bold text-zinc-100">{ontology.relationship_types.length} Relações</p>
              </div>
            </Card>

            <Card className="flex items-center gap-3.5">
              <div className="p-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-zinc-300">
                <Code className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-zinc-400">ID Único</p>
                <p className="text-xs font-mono font-medium text-zinc-300 truncate max-w-[120px]">{ontology.id}</p>
              </div>
            </Card>
          </div>

          {/* Tabs Selector */}
          <div className="flex border-b border-zinc-800 gap-6">
            <button
              onClick={() => setActiveTab('visual')}
              className={`pb-3 text-sm font-semibold transition-all border-b-2 ${
                activeTab === 'visual'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Estrutura Visual
            </button>
            <button
              onClick={() => setActiveTab('json')}
              className={`pb-3 text-sm font-semibold transition-all border-b-2 ${
                activeTab === 'json'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Schema JSON
            </button>
          </div>

          {/* Visual Tab */}
          {activeTab === 'visual' && (
            <div className="space-y-6">
              {/* Nodes Section */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <CircleDot className="w-4 h-4 text-indigo-400" />
                  Tipos de Entidades ({ontology.node_types.length})
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {ontology.node_types.map((node, i) => (
                    <Card key={i} className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-zinc-100 text-base">{node.name}</span>
                        <Badge variant="purple">{node.properties.length} atributos</Badge>
                      </div>

                      {node.description && (
                        <p className="text-xs text-zinc-400 leading-relaxed">{node.description}</p>
                      )}

                      {node.properties.length > 0 && (
                        <div className="pt-3 border-t border-zinc-800/80 space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                            Propriedades:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {node.properties.map((p, pIdx) => (
                              <span
                                key={pIdx}
                                className="inline-flex items-center gap-1 rounded bg-zinc-950 px-2 py-1 text-[11px] font-mono border border-zinc-800 text-zinc-300"
                              >
                                <span>{p.name}</span>
                                <span className="text-zinc-500">({p.type})</span>
                                {p.required && (
                                  <span className="text-[9px] text-amber-400 font-sans font-bold">*</span>
                                )}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              </div>

              {/* Relationships Section */}
              <div className="space-y-4 pt-4 border-t border-zinc-800/60">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-emerald-400" />
                  Relacionamentos Ontológicos ({ontology.relationship_types.length})
                </h3>

                {ontology.relationship_types.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic">
                    Nenhum relacionamento explícito definido para esta ontologia.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {ontology.relationship_types.map((rel, i) => (
                      <Card key={i} className="space-y-2.5">
                        <div className="flex items-center gap-2 text-xs font-mono">
                          <span className="px-2 py-1 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                            {rel.source_node_type}
                          </span>
                          <span className="text-zinc-500 font-bold">───[{rel.name}]───➔</span>
                          <span className="px-2 py-1 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                            {rel.target_node_type}
                          </span>
                        </div>

                        {rel.description && (
                          <p className="text-xs text-zinc-400 pt-2 border-t border-zinc-800/60">
                            {rel.description}
                          </p>
                        )}
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* JSON Tab */}
          {activeTab === 'json' && (
            <Card className="bg-zinc-950 border-zinc-800 p-0 overflow-hidden">
              <pre className="p-5 text-xs text-emerald-400 font-mono overflow-x-auto max-h-[600px] leading-relaxed">
                {JSON.stringify(ontology, null, 2)}
              </pre>
            </Card>
          )}
        </div>
      )}
    </PageContainer>
  );
};
