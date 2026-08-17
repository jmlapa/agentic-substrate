import React, { HTMLAttributes } from 'react';

export interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value: number; // 0 to 100
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'success' | 'warning' | 'error';
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  size = 'md',
  variant = 'primary',
  className = '',
  ...props
}) => {
  const clampedValue = Math.min(100, Math.max(0, value));

  const sizeStyles = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };

  const variantStyles = {
    primary: 'bg-indigo-500',
    success: 'bg-emerald-500',
    warning: 'bg-amber-500',
    error: 'bg-rose-500',
  };

  return (
    <div
      className={`w-full overflow-hidden rounded-full bg-zinc-800 ${sizeStyles[size]} ${className}`}
      {...props}
    >
      <div
        className={`h-full rounded-full transition-all duration-300 ease-out ${variantStyles[variant]}`}
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  );
};
