import React from 'react';
import { Download, Settings, LogOut, Network, Wallet } from 'lucide-react';

export function HubHeader({ onLogout, onOpenSettings, onExportInventory, onOpenPricing }) {
  return (
    <header className="sticky top-0 z-20 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1800px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div>
          <div className="flex items-center gap-2 text-emerald-400">
            <Network size={16} />
            <span className="text-xs font-semibold uppercase tracking-[0.24em]">AIMMH Hub</span>
          </div>
          <h1 className="mt-1 text-lg font-semibold text-zinc-100 sm:text-2xl">Multi-model orchestration workspace</h1>
          <p className="mt-1 text-xs text-zinc-500 sm:text-sm">Persistent isolated instances, nested groups, stage pipelines, and FastAPI-native controls.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onExportInventory} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 transition hover:border-zinc-700 hover:text-white">
            <span className="flex items-center gap-2"><Download size={14} /> Export inventory</span>
          </button>
          <button onClick={onOpenPricing} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 transition hover:border-zinc-700 hover:text-white">
            <span className="flex items-center gap-2"><Wallet size={14} /> Pricing</span>
          </button>
          <button onClick={onOpenSettings} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 transition hover:border-zinc-700 hover:text-white">
            <span className="flex items-center gap-2"><Settings size={14} /> Settings</span>
          </button>
          <button onClick={onLogout} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-300 transition hover:border-red-500/40 hover:text-red-300">
            <span className="flex items-center gap-2"><LogOut size={14} /> Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
