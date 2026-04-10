import React from 'react';
import { Archive, Eye, Layers3, MessageSquareText, RotateCcw, Trash2, X } from 'lucide-react';
import { HubRunBuilder } from './HubRunBuilder';

function InlineCollapsible({ title, subtitle, icon: Icon, defaultOpen = false, testId, children }) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid={testId}>
      <button type="button" onClick={() => setOpen((prev) => !prev)} className="w-full text-left" data-testid={`${testId}-toggle`}>
        <div className="flex items-center gap-2 text-zinc-100">{Icon ? <Icon size={16} /> : null}<h2 className="text-base font-semibold">{title}</h2></div>
        {subtitle ? <p className="mt-1 text-xs text-zinc-500">{subtitle}</p> : null}
      </button>
      {open ? <div className="mt-4">{children}</div> : null}
    </section>
  );
}

export function HubRunsWorkspace({
  runMode = 'batch',
  sourceOptions,
  instanceOptions,
  onRun,
  busyKey,
  runs,
  selectedRunId,
  setSelectedRunId,
  includeArchivedRuns,
  setIncludeArchivedRuns,
  onToggleRunArchive,
  onDeleteArchivedRun,
  selectedRun,
}) {
  const runModeLabel = runMode === 'roleplay' ? 'Roleplay Runs' : 'Batch Runs';
  const runModeHint = runMode === 'roleplay'
    ? 'Roleplay runs are DM/player style orchestration with dedicated quota and history.'
    : 'Batch runs are structured multi-stage pipelines for analysis and synthesis.';
  const [showResponseDrawer, setShowResponseDrawer] = React.useState(false);

  const openResponses = (runId) => {
    setSelectedRunId(runId);
    setShowResponseDrawer(true);
  };

  return (
    <div className="space-y-4" data-testid="hub-runs-workspace">
      <InlineCollapsible
        title={`${runModeLabel} builder`}
        subtitle="Configure and execute runs."
        icon={Layers3}
        defaultOpen={false}
        testId="hub-run-builder-collapsible"
      >
        <HubRunBuilder runMode={runMode} sourceOptions={sourceOptions} instanceOptions={instanceOptions} onRun={onRun} busyKey={busyKey} />
      </InlineCollapsible>

      <InlineCollapsible
        title={`${runModeLabel} inventory`}
        subtitle={runModeHint}
        icon={Layers3}
        defaultOpen={false}
        testId="hub-run-inventory-section"
      >
        <div className="mb-3">
          <label className="flex items-center gap-2 text-xs text-zinc-400" data-testid="show-archived-runs-toggle-label">
            <input type="checkbox" checked={includeArchivedRuns} onChange={(event) => setIncludeArchivedRuns(event.target.checked)} data-testid="show-archived-runs-checkbox" /> Show archived
          </label>
        </div>
        <div className="space-y-3">
          {runs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No runs yet. Build a room, define prompt order, then execute a pipeline.</div>
          ) : runs.map((run) => (
            <article key={run.run_id} className={`w-full rounded-2xl border p-4 transition ${selectedRunId === run.run_id ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-950/60 hover:border-zinc-700'}`} data-testid={`run-card-${run.run_id}`}>
              <button type="button" onClick={() => setSelectedRunId(run.run_id)} className="w-full text-left" data-testid={`select-run-button-${run.run_id}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-sm font-medium text-zinc-100">{run.label || run.run_id}</div>
                      {run.archived && <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300">Archived</span>}
                    </div>
                    <div className="mt-1 text-xs text-zinc-500">{run.stage_summaries?.length || 0} stages · {run.status}</div>
                  </div>
                  <div className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-400">
                    {run.updated_at?.slice(0, 16).replace('T', ' ')}
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400"><MessageSquareText size={12} /> {run.prompt}</div>
              </button>
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" onClick={() => openResponses(run.run_id)} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:border-zinc-700 hover:text-white" data-testid={`view-run-responses-button-${run.run_id}`}>
                  <span className="flex items-center gap-2"><Eye size={13} /> View responses</span>
                </button>
                <button type="button" onClick={() => onToggleRunArchive(run)} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:border-zinc-700 hover:text-white" data-testid={`toggle-run-archive-button-${run.run_id}`}>
                  <span className="flex items-center gap-2">{run.archived ? <RotateCcw size={13} /> : <Archive size={13} />} {run.archived ? 'Restore' : 'Archive'}</span>
                </button>
                {run.archived && (
                  <button type="button" onClick={() => onDeleteArchivedRun(run.run_id)} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:border-red-500/30 hover:text-red-300" data-testid={`delete-archived-run-button-${run.run_id}`}>
                    <span className="flex items-center gap-2"><Trash2 size={13} /> Delete archived</span>
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      </InlineCollapsible>

      {showResponseDrawer && (
        <div className="fixed inset-0 z-[130] flex bg-black/70" data-testid="run-responses-drawer-overlay">
          <button type="button" className="flex-1" onClick={() => setShowResponseDrawer(false)} data-testid="run-responses-drawer-backdrop" />
          <aside className="h-full w-full max-w-2xl overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-4" data-testid="run-responses-drawer">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-base font-semibold text-zinc-100">Run responses</div>
                <div className="text-xs text-zinc-500">{selectedRun?.label || selectedRun?.run_id || 'No run selected'}</div>
              </div>
              <button type="button" onClick={() => setShowResponseDrawer(false)} className="rounded-xl border border-zinc-700 p-2 text-zinc-300" data-testid="run-responses-drawer-close-button"><X size={14} /></button>
            </div>

            <div className="mt-4 space-y-3">
              {selectedRun?.stage_summaries?.length ? (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3" data-testid="run-responses-drawer-stage-descriptions">
                  <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">Batch job descriptions</div>
                  <div className="mt-2 space-y-2">
                    {selectedRun.stage_summaries.map((summary) => (
                      <div key={`${selectedRun.run_id}-stage-${summary.stage_index}`} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-2 text-xs text-zinc-300" data-testid={`run-stage-description-${summary.stage_index}`}>
                        <div className="text-zinc-200">Stage {summary.stage_index + 1} · {summary.stage_name || summary.pattern}</div>
                        <div className="mt-1 text-zinc-400">{summary.prompt_used}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {!selectedRun?.results?.length ? (
                <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No run responses available yet.</div>
              ) : selectedRun.results.map((result) => (
                <article key={result.run_step_id} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3" data-testid={`run-response-item-${result.run_step_id}`}>
                  <div className="text-xs text-zinc-400">Stage {result.stage_index + 1} · {result.pattern} · {result.instance_name || result.model}</div>
                  <pre className="mt-2 whitespace-pre-wrap text-sm text-zinc-100">{result.content}</pre>
                </article>
              ))}
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
