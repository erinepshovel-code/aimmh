import React from 'react';

export function HubTabsNav({ tabs, activeTab, onChange }) {
  return (
    <nav className="sticky top-[73px] z-10 overflow-x-auto rounded-2xl border border-zinc-800 bg-zinc-950/85 p-2 backdrop-blur-xl">
      <div className="flex min-w-max gap-2">
        {tabs.map((tab) => {
          const active = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              onClick={() => onChange(tab.id)}
              className={`rounded-xl px-4 py-2 text-sm transition ${active ? 'bg-emerald-600 text-white shadow-[0_8px_30px_rgba(16,185,129,0.25)]' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100'}`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
