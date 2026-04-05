import React from 'react';
import { Crown, Sparkles } from 'lucide-react';

export function UpgradeToProModal({
  open,
  title,
  description,
  currentCount,
  maxAllowed,
  contextLabel,
  onClose,
  onUpgrade,
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/70 p-4" data-testid="upgrade-to-pro-modal-overlay">
      <div className="w-full max-w-md rounded-3xl border border-zinc-800 bg-zinc-950 p-5 shadow-[0_30px_90px_rgba(0,0,0,0.55)]" data-testid="upgrade-to-pro-modal-card">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-amber-300" data-testid="upgrade-to-pro-modal-badge">
          <Sparkles size={12} /> Free tier limit
        </div>
        <h3 className="mt-3 text-xl font-semibold text-zinc-100" data-testid="upgrade-to-pro-modal-title">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-zinc-400" data-testid="upgrade-to-pro-modal-description">{description}</p>
        {typeof maxAllowed === 'number' && (
          <div className="mt-4 rounded-2xl border border-zinc-800 bg-zinc-900/70 p-3 text-xs text-zinc-300" data-testid="upgrade-to-pro-modal-metric">
            {contextLabel || 'Usage'}: <span className="font-semibold text-zinc-100">{currentCount}</span> / {maxAllowed}
          </div>
        )}
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-zinc-700 px-4 py-2 text-sm text-zinc-300 transition hover:border-zinc-600 hover:text-zinc-100"
            data-testid="upgrade-to-pro-modal-close-button"
          >
            Continue free
          </button>
          <button
            type="button"
            onClick={onUpgrade}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
            data-testid="upgrade-to-pro-modal-upgrade-button"
          >
            <Crown size={14} /> Upgrade to Pro
          </button>
        </div>
      </div>
    </div>
  );
}
