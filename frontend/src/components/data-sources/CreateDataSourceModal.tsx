import React, { useState } from 'react';
import { FolderGit2, Link2, Info } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { ErrorBanner } from '../feedback/ErrorBanner';
import { useCreateDataSource } from '../../hooks/useDataSources';
import { CreateDataSourceDTO } from '../../api/types';
import { MimeTypeSelector } from './MimeTypeSelector';

interface CreateDataSourceModalProps {
  isOpen: boolean;
  onClose: () => void;
  kbId: string;
}

export const CreateDataSourceModal: React.FC<CreateDataSourceModalProps> = ({
  isOpen,
  onClose,
  kbId,
}) => {
  const createMutation = useCreateDataSource(kbId);
  const [name, setName] = useState('');
  const [folderInput, setFolderInput] = useState('');
  const [syncInterval, setSyncInterval] = useState(15);
  const [baselineDays, setBaselineDays] = useState(30);
  const [recursive, setRecursive] = useState(true);
  const [selectedMimes, setSelectedMimes] = useState<string[]>([
    'application/pdf',
    'application/vnd.google-apps.document',
    'application/vnd.google-apps.spreadsheet',
    'text/markdown',
    'text/plain',
    'audio/mpeg',
  ]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cleanFolderId = (raw: string): string => {
    const trimmed = raw.trim();
    const urlMatch = trimmed.match(/\/(?:folders|shared-drives)\/([a-zA-Z0-9_-]+)/);
    if (urlMatch) return urlMatch[1];
    return trimmed;
  };

  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const extracted = cleanFolderId(e.target.value);
    setFolderInput(extracted);
  };

  const toggleMime = (mime: string) => {
    setSelectedMimes((prev) =>
      prev.includes(mime) ? prev.filter((m) => m !== mime) : [...prev, mime]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const folderId = cleanFolderId(folderInput);
    if (!name.trim()) {
      setErrorMessage('Por favor, informe um nome para o conector.');
      return;
    }
    if (!folderId || !/^(root|[a-zA-Z0-9_-]+)$/.test(folderId)) {
      setErrorMessage(
        'Folder ID inválido. Deve conter apenas letras, números, hífens ou ser "root".'
      );
      return;
    }

    const payload: CreateDataSourceDTO = {
      name: name.trim(),
      data_source_type: 'google_drive_folder',
      sync_interval_minutes: Number(syncInterval) || 15,
      config: {
        folder_id: folderId,
        recursive,
        baseline_days: Number(baselineDays) || 30,
        include_mime_types: selectedMimes,
      },
    };

    try {
      await createMutation.mutateAsync(payload);
      setName('');
      setFolderInput('');
      onClose();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: { message?: string } } } })
          ?.response?.data?.detail?.message ||
        (err as Error)?.message ||
        'Falha ao conectar pasta do Google Drive.';
      setErrorMessage(msg);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Conectar Pasta do Google Drive"
      description="Sincronize arquivos automaticamente com ingestão delta e blue/green swap."
      maxWidth="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && <ErrorBanner message={errorMessage} />}

        <div className="flex items-start gap-2.5 p-3 rounded-xl bg-sky-950/30 border border-sky-900/50 text-xs text-sky-200">
          <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Acesso via Service Account:</strong> Compartilhe a pasta no Google Drive com o e-mail da conta de serviço do sistema como <em>Leitor (Viewer)</em>. As credenciais mestras são gerenciadas no backend via <code className="font-mono bg-sky-950 px-1 rounded text-[11px]">GOOGLE_APPLICATION_CREDENTIALS</code>.
          </p>
        </div>

        <Input
          label="Nome do Conector"
          placeholder="Ex: Drive Jurídico - Contratos"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <div>
          <Input
            label="ID da Pasta ou Link do Google Drive"
            placeholder="Ex: 1aBcDeFgHiJkLmNoP ou cole o link drive.google.com/..."
            value={folderInput}
            onChange={handleFolderChange}
            helperText="Cole o link completo da pasta no Google Drive ou apenas o ID alfanumérico."
            required
          />
          {folderInput && folderInput.length >= 10 && (
            <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
              <Link2 className="w-3 h-3" /> ID extraído: <code className="font-mono bg-zinc-800 px-1 rounded">{cleanFolderId(folderInput)}</code>
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Intervalo de Sync (minutos)"
            type="number"
            min={1}
            max={1440}
            value={syncInterval}
            onChange={(e) => setSyncInterval(Math.max(1, parseInt(e.target.value) || 1))}
            helperText="Frequência do agendador automático"
          />
          <Input
            label="Janela Inicial (dias)"
            type="number"
            min={0}
            max={365}
            value={baselineDays}
            onChange={(e) => setBaselineDays(Math.max(0, parseInt(e.target.value) || 0))}
            helperText="Ingerir modificados nos últimos X dias"
          />
        </div>

        <div className="flex items-center gap-2 pt-1">
          <input
            id="recursive-subfolders"
            type="checkbox"
            checked={recursive}
            onChange={(e) => setRecursive(e.target.checked)}
            className="w-4 h-4 rounded border-zinc-700 text-indigo-600 focus:ring-indigo-500 bg-zinc-800"
          />
          <label htmlFor="recursive-subfolders" className="text-xs text-zinc-300 select-none cursor-pointer">
            Percorrer subpastas recursivamente
          </label>
        </div>

        <MimeTypeSelector
          selectedMimes={selectedMimes}
          onToggleMime={toggleMime}
        />

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={createMutation.isPending}>
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={createMutation.isPending}
            leftIcon={<FolderGit2 className="w-4 h-4" />}
          >
            Conectar Fonte de Dados
          </Button>
        </div>
      </form>
    </Modal>
  );
};
