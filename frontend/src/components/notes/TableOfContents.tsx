import React, { useEffect, useState } from 'react';
import { List, Hash } from 'lucide-react';
import { TocItem } from '../../api/types';

interface TableOfContentsProps {
  tocTree: TocItem[];
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({ tocTree }) => {
  const [activeAnchor, setActiveAnchor] = useState<string>('');

  useEffect(() => {
    if (tocTree.length === 0) return;

    const handleScroll = () => {
      const headingElements = tocTree
        .map((item) => document.getElementById(item.anchor))
        .filter((el): el is HTMLElement => el !== null);

      if (headingElements.length === 0) return;

      const scrollPosition = window.scrollY + 120;

      let currentActive = headingElements[0].id;
      for (const el of headingElements) {
        if (el.offsetTop <= scrollPosition) {
          currentActive = el.id;
        } else {
          break;
        }
      }
      setActiveAnchor(currentActive);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [tocTree]);

  if (tocTree.length === 0) {
    return null;
  }

  const handleItemClick = (anchor: string) => {
    const el = document.getElementById(anchor);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveAnchor(anchor);
    }
  };

  return (
    <nav className="w-64 shrink-0 hidden xl:block p-4 sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto select-none border-l border-zinc-800/80">
      <div className="flex items-center gap-2 mb-3 px-1 text-xs font-semibold uppercase tracking-wider text-zinc-400">
        <List className="w-3.5 h-3.5 text-indigo-400" />
        Sumário da Nota
      </div>

      <div className="space-y-1 text-xs">
        {tocTree.map((item) => {
          const isActive = activeAnchor === item.anchor;
          const indentClass =
            item.level === 1
              ? 'pl-2 font-medium'
              : item.level === 2
              ? 'pl-4 font-normal'
              : item.level === 3
              ? 'pl-6 font-normal'
              : 'pl-8 font-normal';

          return (
            <button
              key={`${item.level}-${item.anchor}`}
              onClick={() => handleItemClick(item.anchor)}
              className={`w-full flex items-center gap-1.5 py-1 pr-2 rounded-md text-left transition-colors truncate group ${indentClass} ${
                isActive
                  ? 'bg-indigo-950/60 text-indigo-300 border-l-2 border-indigo-500 font-semibold'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
              }`}
              title={item.title}
            >
              <Hash className={`w-2.5 h-2.5 shrink-0 ${isActive ? 'text-indigo-400' : 'text-zinc-600 group-hover:text-zinc-400'}`} />
              <span className="truncate">{item.title}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
