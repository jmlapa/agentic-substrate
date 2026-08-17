import React from 'react';
import { Sparkles, Copy, Check } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';

export interface AnswerViewProps {
  answer: string;
  query?: string;
}

export const AnswerView: React.FC<AnswerViewProps> = ({ answer }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="space-y-4 border-indigo-800/60 bg-gradient-to-b from-indigo-950/20 to-zinc-900/60">
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-600/30">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              Resposta Sintetizada pelo LLM
            </h3>
            <p className="text-[11px] text-zinc-400 font-mono">Gemini 2.5 Flash-Lite • Temperatura 0.2</p>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          leftIcon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        >
          {copied ? 'Copiado' : 'Copiar'}
        </Button>
      </div>

      <div className="prose prose-invert max-w-none text-sm text-zinc-200 leading-relaxed space-y-3 whitespace-pre-wrap">
        {answer}
      </div>
    </Card>
  );
};
