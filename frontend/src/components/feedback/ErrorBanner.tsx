import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';

export interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Ocorreu um erro',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`flex items-start gap-3.5 rounded-xl border border-rose-900/60 bg-rose-950/30 p-4 text-rose-200 ${className}`}
    >
      <div className="rounded-lg bg-rose-900/50 p-2 text-rose-300">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-rose-100">{title}</h4>
        <p className="mt-1 text-xs text-rose-300/90 leading-relaxed">{message}</p>
        {onRetry && (
          <div className="mt-3">
            <Button
              onClick={onRetry}
              variant="outline"
              size="sm"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              className="border-rose-800 text-rose-200 hover:bg-rose-900/40 hover:text-white"
            >
              Tentar Novamente
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
