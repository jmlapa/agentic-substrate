import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Database, Plus, Save, GitFork } from 'lucide-react';
import { useCreateKnowledgeBase } from '../../hooks/useKnowledgeBases';
import { useOntologies, useCreateOntology } from '../../hooks/useOntologies';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Select } from '../../components/ui/Select';
import { Card } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';
import { LoadingSpinner } from '../../components/feedback/LoadingSpinner';

export const CreateKnowledgeBasePage: React.FC = () => {
  const navigate = useNavigate();
  const createKbMutation = useCreateKnowledgeBase();
  const createOntologyMutation = useCreateOntology();
  const { data: ontologies, isLoading: loadingOntologies } = useOntologies();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedOntologyId, setSelectedOntologyId] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Modal para criação de ontologia inline
  const [isOntologyModalOpen, setIsOntologyModalOpen] = useState(false);
  const [inlineOntologyName, setInlineOntologyName] = useState('');
  const [inlineOntologyDesc, setInlineOntologyDesc] = useState('');
  const [inlineNodeName, setInlineNodeName] = useState('');
  const [inlineModalError, setInlineModalError] = useState('');

  const handleCreateInlineOntology = async () => {
    setInlineModalError('');
    if (!inlineOntologyName.trim()) {
      setInlineModalError('O nome da ontologia é obrigatório.');
      return;
    }
    if (!inlineNodeName.trim()) {
      setInlineModalError('Informe ao menos um tipo de entidade inicial.');
      return;
    }

    try {
      const created = await createOntologyMutation.mutateAsync({
        name: inlineOntologyName,
        description: inlineOntologyDesc,
        version: 1,
        node_types: [
          {
            name: inlineNodeName,
            description: 'Entidade inicial criada inline',
            properties: [],
          },
        ],
        relationship_types: [],
      });
      setSelectedOntologyId(created.id);
      setIsOntologyModalOpen(false);
      setInlineOntologyName('');
      setInlineOntologyDesc('');
      setInlineNodeName('');
    } catch (err: unknown) {
      setInlineModalError((err as Error)?.message || 'Erro ao criar ontologia inline.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!name.trim()) {
      setErrorMsg('O nome da Knowledge Base é obrigatório.');
      return;
    }

    try {
      const res = await createKbMutation.mutateAsync({
        name,
        description,
        ontology_id: selectedOntologyId || undefined,
      });
      navigate(`/knowledge-bases/${res.id}`);
    } catch (err: unknown) {
      setErrorMsg((err as Error)?.message || 'Erro ao criar Knowledge Base.');
    }
  };

  const ontologyOptions = (ontologies || []).map((ont) => ({
    value: ont.id,
    label: `${ont.name} (v${ont.version} • ${ont.node_types.length} entidades)`,
  }));

  return (
    <PageContainer
      title="Nova Knowledge Base"
      description="Configure uma nova partição isolada com ontologia vinculada para indexação híbrida no FalkorDB."
      actions={
        <Button
          variant="outline"
          onClick={() => navigate('/knowledge-bases')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Voltar
        </Button>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6 max-w-2xl">
        {errorMsg && <ErrorBanner message={errorMsg} />}

        <Card className="space-y-5">
          <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
            <Database className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
              Configuração da Base
            </h3>
          </div>

          <Input
            label="Nome da Knowledge Base"
            placeholder="Ex: base_processos_trabalhistas"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <Textarea
            label="Descrição"
            placeholder="Finalidade e tipos de documentos a serem armazenados..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />

          {/* Seletor de Ontologia */}
          <div className="space-y-1.5 pt-2 border-t border-zinc-800/80">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Ontologia Vinculada (Schema do Grafo)
              </label>
              <button
                type="button"
                onClick={() => setIsOntologyModalOpen(true)}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
              >
                <Plus className="w-3 h-3" /> Criar Nova Inline
              </button>
            </div>

            {loadingOntologies ? (
              <LoadingSpinner size="sm" message="Carregando ontologias..." />
            ) : (
              <Select
                options={ontologyOptions}
                value={selectedOntologyId}
                onChange={(e) => setSelectedOntologyId(e.target.value)}
                placeholder="Selecione uma ontologia existente..."
              />
            )}
            <p className="text-xs text-zinc-500">
              A ontologia instrui o extrator semântico a extrair as entidades e conexões certas para o grafo.
            </p>

          </div>
        </Card>

        {/* Submit Actions */}
        <div className="flex items-center justify-end gap-3 pt-4">
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate('/knowledge-bases')}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            isLoading={createKbMutation.isPending}
            leftIcon={<Save className="w-4 h-4" />}
          >
            Criar Knowledge Base
          </Button>
        </div>
      </form>

      {/* Modal para Criação de Ontologia Inline */}
      <Modal
        isOpen={isOntologyModalOpen}
        onClose={() => setIsOntologyModalOpen(false)}
        title="Criar Nova Ontologia"
        description="Cadastre uma ontologia rápida e vincule-a instantaneamente a esta Knowledge Base."
      >
        <div className="space-y-4">
          {inlineModalError && <ErrorBanner message={inlineModalError} />}

          <Input
            label="Nome da Ontologia"
            placeholder="Ex: ontologia_contratos"
            value={inlineOntologyName}
            onChange={(e) => setInlineOntologyName(e.target.value)}
            required
          />

          <Input
            label="Tipo de Entidade Principal"
            placeholder="Ex: Contrato, Clausula, Parte"
            value={inlineNodeName}
            onChange={(e) => setInlineNodeName(e.target.value)}
            required
          />

          <Textarea
            label="Descrição"
            placeholder="Descrição do domínio..."
            value={inlineOntologyDesc}
            onChange={(e) => setInlineOntologyDesc(e.target.value)}
            rows={2}
          />

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setIsOntologyModalOpen(false)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={createOntologyMutation.isPending}
              onClick={handleCreateInlineOntology}
              leftIcon={<GitFork className="w-3.5 h-3.5" />}
            >
              Criar & Vincular
            </Button>
          </div>
        </div>
      </Modal>
    </PageContainer>
  );
};
