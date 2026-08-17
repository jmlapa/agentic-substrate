import React from 'react';
import { LucideIcon } from 'lucide-react';
import { Button } from '../ui/Button';

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 p-12 text-center ${className}`}
    >
      <div className="rounded-2xl bg-zinc-800/80 p-4 text-zinc-400 ring-1 ring-zinc-700/50">
        <Icon className="h-8 w-8 text-zinc-300" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-100">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-zinc-400">{description}</p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button onClick={onAction} variant="primary" size="sm">
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
