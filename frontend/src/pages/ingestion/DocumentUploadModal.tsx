import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, X } from 'lucide-react';
import { useUploadDocument } from '../../hooks/useKnowledgeBases';
import { Modal } from '../../components/ui/Modal';
import { Button } from '../../components/ui/Button';
import { Progress } from '../../components/ui/Progress';
import { ErrorBanner } from '../../components/feedback/ErrorBanner';

export interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  kbId: string;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  kbId,
}) => {
  const uploadMutation = useUploadDocument(kbId);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
      setErrorMsg('');
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
      setErrorMsg('');
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== index));
  };

  const handleUploadAll = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setErrorMsg('');
    setUploadProgress(10);

    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        await uploadMutation.mutateAsync(selectedFiles[i]);
        setUploadProgress(Math.round(((i + 1) / selectedFiles.length) * 100));
      }
      setSelectedFiles([]);
      onClose();
    } catch (err: unknown) {
      setErrorMsg((err as Error)?.message || 'Erro durante o envio dos arquivos.');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Upload de Documentos"
      description="Envie arquivos (PDF, TXT, MD, DOCX) para processamento assíncrono pelo pipeline GraphRAG."
    >
      <div className="space-y-5">
        {errorMsg && <ErrorBanner message={errorMsg} />}

        {/* Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-zinc-700 hover:border-indigo-500 bg-zinc-950/60 p-8 text-center cursor-pointer transition-colors"
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.md,.markdown,.docx,.json"
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="rounded-2xl bg-zinc-800/80 p-3 text-indigo-400">
            <UploadCloud className="w-8 h-8" />
          </div>
          <p className="mt-3 text-sm font-semibold text-zinc-200">
            Clique ou arraste arquivos aqui
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            PDF, TXT, Markdown, DOCX ou JSON (máx. 50MB por arquivo)
          </p>
        </div>

        {/* Selected files list */}
        {selectedFiles.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Arquivos selecionados ({selectedFiles.length}):
            </span>
            {selectedFiles.map((file, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg bg-zinc-950 px-3 py-2 border border-zinc-800 text-xs"
              >
                <div className="flex items-center gap-2 truncate">
                  <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                  <span className="text-zinc-200 truncate">{file.name}</span>
                  <span className="text-zinc-500 shrink-0">
                    ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
                {!uploading && (
                  <button
                    onClick={() => handleRemoveFile(i)}
                    className="text-zinc-500 hover:text-rose-400 p-1"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Upload progress */}
        {uploading && (
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-zinc-400">
              <span>Enviando e enfileirando arquivos...</span>
              <span>{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} variant="primary" />
          </div>
        )}

        {/* Modal actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={uploading}>
            Cancelar
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleUploadAll}
            disabled={selectedFiles.length === 0}
            isLoading={uploading}
            leftIcon={<UploadCloud className="w-4 h-4" />}
          >
            Iniciar Envio ({selectedFiles.length})
          </Button>
        </div>
      </div>
    </Modal>
  );
};
