import React from 'react';
import { Check } from 'lucide-react';

interface MimeTypeSelectorProps {
  selectedMimes: string[];
  onToggleMime: (mime: string) => void;
}

export const MIME_OPTIONS = [
  { label: 'PDF (.pdf)', mime: 'application/pdf' },
  { label: 'Google Docs', mime: 'application/vnd.google-apps.document' },
  { label: 'Google Sheets', mime: 'application/vnd.google-apps.spreadsheet' },
  { label: 'Texto e Markdown (.txt, .md)', mime: 'text/markdown' },
  { label: 'Áudios (.mp3, .wav, .m4a)', mime: 'audio/mpeg' },
];

export const MimeTypeSelector: React.FC<MimeTypeSelectorProps> = ({
  selectedMimes,
  onToggleMime,
}) => {
  return (
    <div className="space-y-2 pt-2 border-t border-zinc-800">
      <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
        Tipos de Arquivos Suportados
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {MIME_OPTIONS.map((opt) => {
          const active = selectedMimes.includes(opt.mime);
          return (
            <button
              key={opt.mime}
              type="button"
              onClick={() => onToggleMime(opt.mime)}
              className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                active
                  ? 'border-indigo-600/70 bg-indigo-950/40 text-indigo-200'
                  : 'border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700'
              }`}
            >
              <span>{opt.label}</span>
              {active && <Check className="w-3.5 h-3.5 text-indigo-400 shrink-0" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};
