import React from 'react';

export function HubTabsNav({ tabs, activeTab, onChange }) {
  return (
    <nav
      className="sticky top-[73px] z-10 rounded-2xl border border-zinc-800 bg-zinc-950/85 p-2 backdrop-blur-xl"
      data-testid="hub-tabs-nav"
      aria-label="AIMMH workspace tabs"
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
        {tabs.map((tab) => {
          const active = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={`min-h-[3.25rem] rounded-xl px-4 py-3 text-left text-sm leading-snug transition ${active ? 'bg-emerald-600 text-white shadow-[0_8px_30px_rgba(16,185,129,0.25)]' : 'bg-zinc-950/40 text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100'}`}
              data-testid={`hub-tab-${tab.id}`}
              aria-pressed={active}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
