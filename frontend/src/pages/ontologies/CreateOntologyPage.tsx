import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, ArrowLeft, GitFork, Save } from 'lucide-react';
import { useCreateOntology } from '../../hooks/useOntologies';
import { NodeTypeDefinition, PropertyDefinition, PropertyType, RelationshipTypeDefinition } from '../../api/types';
import { PageContainer } from '../../components/layout/PageContainer';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Textarea } from '../../components/ui/Textarea';
import { Card } from '../../components/ui/Card';
import { Select } from '../../components/ui/Select';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export const CreateOntologyPage: React.FC = () => {
  const navigate = useNavigate();
  const createMutation = useCreateOntology();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState(1);
  const [errorMsg, setErrorMsg] = useState('');

  // Node Types
  const [nodeTypes, setNodeTypes] = useState<NodeTypeDefinition[]>([
    {
      name: '',
      description: '',
      properties: [],
    },
  ]);

  // Relationship Types
  const [relationshipTypes, setRelationshipTypes] = useState<RelationshipTypeDefinition[]>([]);

  const handleAddNodeType = () => {
    setNodeTypes([...nodeTypes, { name: '', description: '', properties: [] }]);
  };

  const handleRemoveNodeType = (index: number) => {
    setNodeTypes(nodeTypes.filter((_, i) => i !== index));
  };

  const handleNodeTypeChange = (index: number, field: keyof NodeTypeDefinition, value: string) => {
    const updated = [...nodeTypes];
    updated[index] = { ...updated[index], [field]: value };
    setNodeTypes(updated);
  };

  const handleAddProperty = (nodeIndex: number) => {
    const updated = [...nodeTypes];
    const newProp: PropertyDefinition = {
      name: '',
      type: 'string',
      required: false,
    };
    updated[nodeIndex].properties.push(newProp);
    setNodeTypes(updated);
  };

  const handleRemoveProperty = (nodeIndex: number, propIndex: number) => {
    const updated = [...nodeTypes];
    updated[nodeIndex].properties = updated[nodeIndex].properties.filter((_, i) => i !== propIndex);
    setNodeTypes(updated);
  };

  const handlePropertyChange = (
    nodeIndex: number,
    propIndex: number,
    field: keyof PropertyDefinition,
    value: string | boolean
  ) => {
    const updated = [...nodeTypes];
    updated[nodeIndex].properties[propIndex] = {
      ...updated[nodeIndex].properties[propIndex],
      [field]: value,
    };
    setNodeTypes(updated);
  };

  // Relationships
  const handleAddRelationship = () => {
    setRelationshipTypes([
      ...relationshipTypes,
      {
        name: '',
        source_node_type: nodeTypes[0]?.name || '',
        target_node_type: nodeTypes[0]?.name || '',
        description: '',
        properties: [],
      },
    ]);
  };

  const handleRemoveRelationship = (index: number) => {
    setRelationshipTypes(relationshipTypes.filter((_, i) => i !== index));
  };

  const handleRelationshipChange = (
    index: number,
    field: keyof RelationshipTypeDefinition,
    value: string
  ) => {
    const updated = [...relationshipTypes];
    updated[index] = { ...updated[index], [field]: value };
    setRelationshipTypes(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!name.trim()) {
      setErrorMsg('O nome da ontologia é obrigatório.');
      return;
    }

    const validNodeTypes = nodeTypes.filter((nt) => nt.name.trim() !== '');
    if (validNodeTypes.length === 0) {
      setErrorMsg('Adicione pelo menos um Tipo de Entidade (Nó) válido.');
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        name,
        description,
        version: Number(version) || 1,
        node_types: validNodeTypes,
        relationship_types: relationshipTypes.filter((rt) => rt.name.trim() !== ''),
      });
      navigate(`/ontologies/${created.id}`);
    } catch (err: unknown) {
      setErrorMsg((err as Error)?.message || 'Erro ao criar ontologia.');
    }
  };

  const propertyTypeOptions = [
    { value: 'string', label: 'String (Texto)' },
    { value: 'integer', label: 'Integer (Número Inteiro)' },
    { value: 'float', label: 'Float (Número Decimal)' },
    { value: 'boolean', label: 'Boolean (Verdadeiro/Falso)' },
    { value: 'date', label: 'Date (Data)' },
    { value: 'list', label: 'List (Lista de Valores)' },
  ];

  return (
    <PageContainer
      title="Nova Ontologia"
      description="Modele as entidades e relacionamentos que a IA (Gemma 4 / OpenRouter) extrairá dos documentos."
      actions={
        <Button
          variant="outline"
          onClick={() => navigate('/ontologies')}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Voltar
        </Button>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
        {errorMsg && <ErrorBanner message={errorMsg} />}

        {/* Informações Básicas */}
        <Card className="space-y-4">
          <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
            <GitFork className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
              1. Dados Gerais da Ontologia
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Input
                label="Nome da Ontologia"
                placeholder="Ex: ontologia_juridica_trabalhista"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <Input
                label="Versão"
                type="number"
                min="1"
                value={version}
                onChange={(e) => setVersion(parseInt(e.target.value) || 1)}
              />
            </div>
          </div>

          <Textarea
            label="Descrição do Domínio"
            placeholder="Descreva o escopo e regras deste domínio de conhecimento..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </Card>

        {/* Tipos de Entidades (Nós) */}
        <Card className="space-y-5">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-950 text-[11px] font-bold text-indigo-400 border border-indigo-800">
                2
              </span>
              <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
                Tipos de Entidades (Nós do Grafo)
              </h3>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddNodeType}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Adicionar Entidade
            </Button>
          </div>

          <div className="space-y-4">
            {nodeTypes.map((node, nodeIdx) => (
              <div
                key={nodeIdx}
                className="rounded-xl border border-zinc-800/80 bg-zinc-950/40 p-4 space-y-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Input
                      label={`Nome da Entidade #${nodeIdx + 1}`}
                      placeholder="Ex: Tribunal, Lei, ParteProcessual"
                      value={node.name}
                      onChange={(e) => handleNodeTypeChange(nodeIdx, 'name', e.target.value)}
                      required
                    />
                    <Input
                      label="Descrição Semântica"
                      placeholder="Ex: Órgão do Poder Judiciário responsável por julgamentos"
                      value={node.description}
                      onChange={(e) => handleNodeTypeChange(nodeIdx, 'description', e.target.value)}
                    />
                  </div>
                  {nodeTypes.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveNodeType(nodeIdx)}
                      className="mt-6 p-2 text-zinc-500 hover:text-rose-400 transition-colors"
                      title="Remover entidade"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Propriedades da Entidade */}
                <div className="pl-3 border-l-2 border-zinc-800 space-y-2 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                      Atributos / Propriedades ({node.properties.length})
                    </span>
                    <button
                      type="button"
                      onClick={() => handleAddProperty(nodeIdx)}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> Adicionar Atributo
                    </button>
                  </div>

                  {node.properties.map((prop, propIdx) => (
                    <div key={propIdx} className="flex items-center gap-3">
                      <Input
                        placeholder="Nome (ex: sigla, data_publicacao)"
                        value={prop.name}
                        onChange={(e) => handlePropertyChange(nodeIdx, propIdx, 'name', e.target.value)}
                        className="text-xs py-1.5"
                      />
                      <Select
                        options={propertyTypeOptions}
                        value={prop.type}
                        onChange={(e) =>
                          handlePropertyChange(
                            nodeIdx,
                            propIdx,
                            'type',
                            e.target.value as PropertyType
                          )
                        }
                        className="text-xs py-1.5 w-48"
                      />
                      <label className="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={prop.required}
                          onChange={(e) =>
                            handlePropertyChange(nodeIdx, propIdx, 'required', e.target.checked)
                          }
                          className="rounded border-zinc-700 bg-zinc-800 text-indigo-600 focus:ring-indigo-500"
                        />
                        Obrigatório
                      </label>
                      <button
                        type="button"
                        onClick={() => handleRemoveProperty(nodeIdx, propIdx)}
                        className="text-zinc-500 hover:text-rose-400 p-1"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Tipos de Relacionamentos */}
        <Card className="space-y-5">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-950 text-[11px] font-bold text-indigo-400 border border-indigo-800">
                3
              </span>
              <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
                Relacionamentos Entre Entidades
              </h3>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddRelationship}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Adicionar Relação
            </Button>
          </div>

          {relationshipTypes.length === 0 && (
            <p className="text-xs text-zinc-500 italic">
              Nenhum relacionamento explícito definido. Clique no botão acima para conectar entidades.
            </p>
          )}

          <div className="space-y-3">
            {relationshipTypes.map((rel, relIdx) => (
              <div
                key={relIdx}
                className="flex flex-col sm:flex-row items-start sm:items-center gap-3 rounded-xl border border-zinc-800/80 bg-zinc-950/40 p-3.5"
              >
                <div className="flex-1 grid grid-cols-1 sm:grid-cols-4 gap-2.5 w-full">
                  <Input
                    placeholder="Origem (ex: Processo)"
                    value={rel.source_node_type}
                    onChange={(e) => handleRelationshipChange(relIdx, 'source_node_type', e.target.value)}
                    className="text-xs py-1.5"
                  />
                  <Input
                    placeholder="Relação (ex: JULGADO_POR)"
                    value={rel.name}
                    onChange={(e) => handleRelationshipChange(relIdx, 'name', e.target.value)}
                    className="text-xs py-1.5"
                  />
                  <Input
                    placeholder="Destino (ex: Tribunal)"
                    value={rel.target_node_type}
                    onChange={(e) => handleRelationshipChange(relIdx, 'target_node_type', e.target.value)}
                    className="text-xs py-1.5"
                  />
                  <Input
                    placeholder="Descrição da relação"
                    value={rel.description}
                    onChange={(e) => handleRelationshipChange(relIdx, 'description', e.target.value)}
                    className="text-xs py-1.5"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveRelationship(relIdx)}
                  className="text-zinc-500 hover:text-rose-400 p-1.5"
                  title="Remover relacionamento"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </Card>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate('/ontologies')}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            isLoading={createMutation.isPending}
            leftIcon={<Save className="w-4 h-4" />}
          >
            Salvar Ontologia
          </Button>
        </div>
      </form>
    </PageContainer>
  );
};
