import React, { HTMLAttributes } from 'react';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'purple';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'sm',
  className = '',
  ...props
}) => {
  const sizeStyles = {
    sm: 'px-2 py-0.5 text-[11px] font-medium tracking-wide',
    md: 'px-2.5 py-1 text-xs font-medium',
  };

  const variantStyles = {
    default: 'bg-zinc-800 text-zinc-300 border border-zinc-700/60',
    success: 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60',
    warning: 'bg-amber-950/60 text-amber-300 border border-amber-800/60',
    error: 'bg-rose-950/60 text-rose-300 border border-rose-800/60',
    info: 'bg-sky-950/60 text-sky-300 border border-sky-800/60',
    purple: 'bg-indigo-950/60 text-indigo-300 border border-indigo-800/60',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
};
