import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Layers,
  Database,
  Sparkles,
  GitFork,
  Cpu,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    {
      to: '/knowledge-bases',
      label: 'Knowledge Bases',
      icon: Database,
      badge: 'Core',
    },
    {
      to: '/ontologies',
      label: 'Ontologias',
      icon: GitFork,
    },
    {
      to: '/playground',
      label: 'RAG Playground',
      icon: Sparkles,
      badge: 'Gemini',
    },
  ];

  return (
    <aside className="w-64 border-r border-zinc-800/80 bg-zinc-950/90 flex flex-col justify-between p-4 shrink-0 min-h-screen">
      <div>
        {/* Logo / Header */}
        <div className="flex items-center gap-3 px-3 py-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-white shadow-lg shadow-indigo-500/20">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              Substrate <span className="text-[10px] uppercase font-semibold bg-indigo-950 text-indigo-400 border border-indigo-800/60 rounded px-1.5 py-0.2">v0.2.1</span>
            </h1>
            <p className="text-[11px] text-zinc-500 font-mono">GraphRAG Platform</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="mt-6 space-y-1.5">
          <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">
            Módulos Principais
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-zinc-800/90 text-white font-semibold shadow-sm border border-zinc-700/50'
                      : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-zinc-400 group-hover:text-zinc-200" />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700/40 rounded-md px-1.5 py-0.5">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* System Status Footer */}
      <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-medium text-zinc-300">Engine Online</span>
          </div>
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
        </div>
        <p className="mt-1.5 text-[11px] text-zinc-500 font-mono">
          FalkorDB + Gemini Flash
        </p>
      </div>
    </aside>
  );
};
