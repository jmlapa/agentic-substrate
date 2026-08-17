import React, { HTMLAttributes } from 'react';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  hoverable = false,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`rounded-xl border border-zinc-800/80 bg-zinc-900/60 p-5 shadow-sm backdrop-blur-sm transition-all ${
        hoverable ? 'hover:border-zinc-700 hover:bg-zinc-900/90 hover:shadow-md' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
