import React from 'react';
import { Layers3, MessageSquareText } from 'lucide-react';
import { HubRunBuilder } from './HubRunBuilder';

export function HubRunsWorkspace({ sourceOptions, instanceOptions, onRun, busyKey, runs, selectedRunId, setSelectedRunId }) {
  return (
    <div className="space-y-4">
      <HubRunBuilder sourceOptions={sourceOptions} instanceOptions={instanceOptions} onRun={onRun} busyKey={busyKey} />
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex items-center gap-2 text-zinc-100"><Layers3 size={16} /> <h2 className="text-base font-semibold">Run inventory</h2></div>
        <p className="mt-1 text-xs text-zinc-500">Rooms, run orders, prompt chains, and saved results stay visible here for quick mobile switching.</p>
        <div className="mt-4 space-y-3">
          {runs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No runs yet. Build a room, define prompt order, then execute a pipeline.</div>
          ) : runs.map((run) => (
            <button
              key={run.run_id}
              onClick={() => setSelectedRunId(run.run_id)}
              className={`w-full rounded-2xl border p-4 text-left transition ${selectedRunId === run.run_id ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-950/60 hover:border-zinc-700'}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-medium text-zinc-100">{run.label || run.run_id}</div>
                  <div className="mt-1 text-xs text-zinc-500">{run.stage_summaries?.length || 0} stages · {run.status}</div>
                </div>
                <div className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-400">
                  {run.updated_at?.slice(0, 16).replace('T', ' ')}
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400"><MessageSquareText size={12} /> {run.prompt}</div>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
