import React from 'react';
import { Loader2, Sparkles, Trash2 } from 'lucide-react';
import { ResponseMarkdown } from './ResponseMarkdown';
import { CollapsibleSection } from './CollapsibleSection';

export function HubSynthesisPanel({
  instances,
  synthesisBasket,
  onRemoveFromSynthesis,
  onRunSynthesis,
  synthesisBusy,
  synthesisHistory,
  isAuthenticated,
  includeSavedSynthesisHistory,
  setIncludeSavedSynthesisHistory,
}) {
  const [selectedBlockIds, setSelectedBlockIds] = React.useState([]);
  const [synthesisInstanceIds, setSynthesisInstanceIds] = React.useState([]);
  const [instruction, setInstruction] = React.useState('Synthesize and analyze selected responses into a cohesive answer.');
  const [saveHistory, setSaveHistory] = React.useState(false);

  const activeInstances = React.useMemo(
    () => instances.filter((item) => !item.archived),
    [instances],
  );

  React.useEffect(() => {
    setSelectedBlockIds((prev) => {
      const next = prev.filter((id) => synthesisBasket.some((block) => block.source_id === id));
      return next.length === prev.length && next.every((id, idx) => id === prev[idx]) ? prev : next;
    });
  }, [synthesisBasket]);

  React.useEffect(() => {
    setSynthesisInstanceIds((prev) => {
      const next = prev.filter((id) => activeInstances.some((instance) => instance.instance_id === id));
      return next.length === prev.length && next.every((id, idx) => id === prev[idx]) ? prev : next;
    });
  }, [activeInstances]);

  const toggleBlock = (sourceId) => {
    setSelectedBlockIds((prev) => (prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId]));
  };

  const toggleSynthesisInstance = (instanceId) => {
    setSynthesisInstanceIds((prev) => (prev.includes(instanceId) ? prev.filter((id) => id !== instanceId) : [...prev, instanceId]));
  };

  const submitSynthesis = async () => {
    const selectedBlocks = synthesisBasket.filter((block) => selectedBlockIds.includes(block.source_id));
    if (selectedBlocks.length === 0 || synthesisInstanceIds.length === 0) return;
    await onRunSynthesis({
      synthesis_instance_ids: synthesisInstanceIds,
      selected_blocks: selectedBlocks,
      instruction,
      label: 'Synthesis tab run',
      save_history: isAuthenticated && saveHistory,
    });
    setSelectedBlockIds([]);
  };

  return (
    <div className="space-y-4" data-testid="hub-synthesis-panel">
      <CollapsibleSection
        title="Synthesis queue"
        subtitle="Only responses sent from Chat appear here."
        icon={Sparkles}
        defaultOpen={false}
        testId="synthesis-queue-section"
      >
        <div className="max-h-[58vh] space-y-3 overflow-y-auto pr-1" data-testid="synthesis-queue-scroll-region">
          {synthesisBasket.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500" data-testid="synthesis-empty-queue">No queued responses yet.</div>
          ) : synthesisBasket.map((block) => (
            <article key={block.source_id} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-3" data-testid={`synthesis-queue-item-${block.source_id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <label className="flex min-w-0 items-start gap-2">
                  <input
                    type="checkbox"
                    checked={selectedBlockIds.includes(block.source_id)}
                    onChange={() => toggleBlock(block.source_id)}
                    className="mt-0.5"
                    data-testid={`synthesis-queue-select-${block.source_id}`}
                  />
                  <div className="min-w-0">
                    <div className="text-xs text-zinc-400">{block.source_label || block.instance_name || block.model}</div>
                    <div className="mt-1 text-xs text-zinc-500">{block.model} · {block.instance_name}</div>
                  </div>
                </label>
                <button
                  type="button"
                  onClick={() => onRemoveFromSynthesis(block.source_id)}
                  className="rounded-xl border border-zinc-800 px-2 py-1 text-xs text-zinc-300 hover:text-white"
                  data-testid={`synthesis-queue-remove-${block.source_id}`}
                >
                  <span className="flex items-center gap-1"><Trash2 size={11} /> Remove</span>
                </button>
              </div>
              <div className="mt-2 rounded-xl border border-zinc-800 bg-zinc-900/50 p-3 text-sm">
                <ResponseMarkdown content={block.content} fontScale={1} />
              </div>
            </article>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="Synthesis run controls"
        subtitle="Pick synthesis instances and instructions."
        icon={Sparkles}
        defaultOpen={false}
        testId="synthesis-run-controls"
      >
        <div className="text-xs font-medium text-zinc-300">Synthesis models ({synthesisInstanceIds.length} selected)</div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {activeInstances.length === 0 ? <div className="text-sm text-zinc-500">Create instances first.</div> : activeInstances.map((instance) => (
            <label key={instance.instance_id} className="flex items-start gap-2 rounded-xl border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-xs text-zinc-300" data-testid={`synthesis-run-instance-${instance.instance_id}`}>
              <input type="checkbox" checked={synthesisInstanceIds.includes(instance.instance_id)} onChange={() => toggleSynthesisInstance(instance.instance_id)} className="mt-0.5" />
              <span>{instance.name} · {instance.model_id}</span>
            </label>
          ))}
        </div>

        <textarea
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          rows={4}
          placeholder="Synthesis instruction"
          className="mt-3 w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-violet-500/50"
          data-testid="synthesis-run-instruction-input"
        />

        <label className="mt-3 flex items-center gap-2 text-xs text-zinc-400" data-testid="synthesis-save-history-toggle-row">
          <input
            type="checkbox"
            checked={saveHistory && isAuthenticated}
            disabled={!isAuthenticated}
            onChange={(event) => setSaveHistory(event.target.checked)}
            data-testid="synthesis-save-history-toggle"
          />
          Save synthesis history across sessions (account only)
        </label>

        {isAuthenticated && (
          <label className="mt-2 flex items-center gap-2 text-xs text-zinc-400" data-testid="synthesis-include-saved-history-row">
            <input
              type="checkbox"
              checked={includeSavedSynthesisHistory}
              onChange={(event) => setIncludeSavedSynthesisHistory(event.target.checked)}
              data-testid="synthesis-include-saved-history-toggle"
            />
            Show saved cross-session history
          </label>
        )}

        <button
          type="button"
          onClick={submitSynthesis}
          disabled={selectedBlockIds.length === 0 || synthesisInstanceIds.length === 0 || synthesisBusy}
          className="mt-3 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-60"
          data-testid="synthesis-run-submit-button"
        >
          <span className="flex items-center gap-2">{synthesisBusy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Synthesize selected</span>
        </button>
      </CollapsibleSection>

      <CollapsibleSection
        title="Synthesis history"
        subtitle="Session-first history with optional saved history visibility."
        icon={Sparkles}
        defaultOpen={false}
        testId="synthesis-history-section"
      >
        <div className="mt-3 space-y-3">
          {synthesisHistory.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No synthesis history yet for this session.</div>
          ) : synthesisHistory.map((batch) => (
            <article key={batch.synthesis_batch_id} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4" data-testid={`synthesis-history-batch-${batch.synthesis_batch_id}`}>
              <div className="text-sm text-zinc-200">{batch.label || batch.synthesis_batch_id}</div>
              <div className="mt-1 text-xs text-zinc-500">{batch.synthesis_instance_names?.join(', ')}</div>
              <div className="mt-3 space-y-3">
                {(batch.outputs || []).map((output) => (
                  <div key={output.message_id || `${batch.synthesis_batch_id}-${output.synthesis_instance_id}`} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3" data-testid={`synthesis-history-output-${output.message_id || `${batch.synthesis_batch_id}-${output.synthesis_instance_id}`}`}>
                    <div className="text-xs text-zinc-400">{output.synthesis_instance_name} · {output.model}</div>
                    <div className="mt-2"><ResponseMarkdown content={output.content} fontScale={1} /></div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
}
