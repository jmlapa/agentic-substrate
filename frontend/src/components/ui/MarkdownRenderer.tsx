import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { CodeBlock } from './CodeBlock';

export interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const getNodeText = (node: React.ReactNode): string => {
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(getNodeText).join('');
  if (React.isValidElement(node) && (node.props as { children?: React.ReactNode })?.children) {
    return getNodeText((node.props as { children?: React.ReactNode }).children);
  }
  return '';
};

const getSlug = (node: React.ReactNode): string => {
  const text = getNodeText(node);
  return (
    text
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .trim()
      .replace(/[-\s]+/g, '-') || 'section'
  );
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className = '',
}) => {
  return (
    <div
      className={`prose prose-invert max-w-none text-zinc-200 text-sm leading-relaxed ${className}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          sub: ({ children }) => (
            <sub className="text-[0.8em] font-normal leading-none text-zinc-300 align-sub">
              {children}
            </sub>
          ),
          sup: ({ children }) => (
            <sup className="text-[0.8em] font-medium leading-none text-indigo-400 align-super">
              {children}
            </sup>
          ),
          h1: ({ children }) => (
            <h1
              id={getSlug(children)}
              className="mt-5 mb-3 border-b border-zinc-800/80 pb-2 text-xl font-bold text-zinc-100 first:mt-0 scroll-mt-20"
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              id={getSlug(children)}
              className="mt-4 mb-2 text-lg font-semibold text-zinc-100 first:mt-0 scroll-mt-20"
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              id={getSlug(children)}
              className="mt-3.5 mb-1.5 text-base font-medium text-zinc-200 first:mt-0 scroll-mt-20"
            >
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4
              id={getSlug(children)}
              className="mt-3 mb-1 text-sm font-medium text-zinc-300 first:mt-0 scroll-mt-20"
            >
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="mb-3 text-sm leading-relaxed text-zinc-300 last:mb-0">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="my-2.5 ml-4 list-disc space-y-1 text-sm text-zinc-300">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2.5 ml-4 list-decimal space-y-1 text-sm text-zinc-300">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="pl-1 leading-relaxed">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-3 rounded-r-lg border-l-4 border-indigo-500 bg-indigo-950/20 px-4 py-2 text-sm italic text-zinc-300">
              {children}
            </blockquote>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-400 underline underline-offset-2 transition-colors hover:text-indigo-300"
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-zinc-800/80 bg-zinc-950/40">
              <table className="w-full text-left text-xs text-zinc-300 divide-y divide-zinc-800">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-zinc-900/80 text-[11px] font-semibold uppercase tracking-wider text-zinc-200">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-zinc-800/60">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="transition-colors hover:bg-zinc-800/30">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-semibold text-zinc-200">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2 text-zinc-300">{children}</td>
          ),
          hr: () => <hr className="my-4 border-zinc-800/80" />,
          code: ({ className: codeClassName, children, ...props }) => {
            const match = /language-(\w+)/.exec(codeClassName || '');
            const codeString = String(children).replace(/\n$/, '');
            const isMultiline = codeString.includes('\n');

            if (match || isMultiline) {
              return (
                <CodeBlock
                  language={match ? match[1] : 'text'}
                  value={codeString}
                />
              );
            }

            return (
              <code
                className="rounded border border-zinc-700/50 bg-zinc-800/90 px-1.5 py-0.5 font-mono text-xs font-medium text-indigo-300"
                {...props}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
