import React from 'react';

export interface PageContainerProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  title,
  description,
  actions,
  children,
}) => {
  return (
    <div className="flex-1 overflow-y-auto p-8 max-w-7xl mx-auto w-full">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800/60 mb-8">
        <div className="min-w-0">
          <h2 className="text-2xl font-bold tracking-tight text-white truncate">{title}</h2>
          {description && (
            <p className="mt-1 text-sm text-zinc-400 leading-relaxed">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center flex-wrap gap-2.5 md:shrink-0">
            {actions}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <main>{children}</main>
    </div>
  );
};
