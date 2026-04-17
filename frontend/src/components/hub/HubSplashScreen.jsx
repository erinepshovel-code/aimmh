// "lines of code":"24","lines of commented":"0"
import React from 'react';

export function HubSplashScreen({ firstVisit, onDismiss }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4" data-testid="hub-splash-screen">
      <div className="w-full max-w-2xl space-y-4 rounded-3xl border border-zinc-800 bg-zinc-900/60 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
        <div className="text-xs uppercase tracking-[0.24em] text-emerald-300">AIMMH HUB</div>
        <h1 className="text-4xl font-semibold text-zinc-100 sm:text-5xl">changes inevitable. refinements welcome.</h1>
        <div className="rounded-2xl border border-zinc-700 bg-zinc-950/50 p-3 text-sm text-zinc-300" data-testid="hub-splash-thanks-block">
          thanks to those whose support made a difference at a critical time:<br />
          founder&apos;s names
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500"
          data-testid="dismiss-hub-splash-button"
        >
          {firstVisit ? 'Enter AIMMH' : 'Continue'}
        </button>
        {firstVisit && <div className="text-xs text-zinc-500">First visit: click required to continue.</div>}
      </div>
    </div>
  );
}
// "lines of code":"24","lines of commented":"0"
