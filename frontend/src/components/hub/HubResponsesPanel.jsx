import React from 'react';
import { Copy, LayoutPanelTop, Rows3, Share2 } from 'lucide-react';
import { toast } from 'sonner';
import { hubApi } from '../../lib/hubApi';
import { ResponseCarousel } from './ResponseCarousel';
import { ResponsePane } from './ResponsePane';

export function HubResponsesPanel({
  runs,
  selectedRun,
  selectedRunId,
  setSelectedRunId,
  prompts,
  selectedPromptId,
  setSelectedPromptId,
  synthesisBasket,
  onToggleSynthesisBlock,
}) {
  const [sourceType, setSourceType] = React.useState('runs');
  const [selectedStageIndex, setSelectedStageIndex] = React.useState(0);
  const [compareMode, setCompareMode] = React.useState('stack');
  const [selectedIds, setSelectedIds] = React.useState([]);
  const [feedbackMap, setFeedbackMap] = React.useState({});
  const [fontScale, setFontScale] = React.useState(1);
  const [activeIndex, setActiveIndex] = React.useState(0);

  React.useEffect(() => {
    setSelectedStageIndex(0);
    setSelectedIds([]);
    setActiveIndex(0);
  }, [selectedRunId, selectedPromptId, sourceType]);

  const stageSummaries = selectedRun?.stage_summaries || [];
  const stageOptions = stageSummaries.map((summary) => ({ value: summary.stage_index, label: summary.stage_name || summary.pattern }));
  const selectedPrompt = prompts.find((item) => item.prompt_id === selectedPromptId) || prompts[0] || null;
  const toSynthesisBlock = React.useCallback((item) => ({
    source_type: sourceType === 'runs' ? 'run_response' : 'prompt_response',
    source_id: item.run_step_id,
    source_label: sourceType === 'runs'
      ? `Run ${selectedRunId || 'unknown'} · ${item.instance_name || item.model}`
      : `Prompt ${selectedPromptId || 'unknown'} · ${item.instance_name || item.model}`,
    instance_id: item.instance_id,
    instance_name: item.instance_name,
    model: item.model,
    content: item.content,
  }), [selectedPromptId, selectedRunId, sourceType]);
  const stageResponses = sourceType === 'runs'
    ? (selectedRun?.results || []).filter((item) => item.stage_index === Number(selectedStageIndex))
    : (selectedPrompt?.responses || []).map((item, index) => ({
        ...item,
        run_step_id: item.message_id || `${item.prompt_id}-${item.instance_id}-${index}`,
        round_num: 0,
        step_num: index + 1,
        role: 'assistant',
        slot_idx: index,
      }));
  const synthesisIds = synthesisBasket.map((item) => item.source_id);
  const selectedResponses = stageResponses.filter((item) => selectedIds.includes(item.run_step_id));

  const toggleSelected = (item) => {
    setSelectedIds((prev) => prev.includes(item.run_step_id) ? prev.filter((id) => id !== item.run_step_id) : [...prev, item.run_step_id]);
  };

  const copyText = async (text, label = 'Response copied') => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(label);
    } catch {
      toast.error('Copy failed');
    }
  };

  const shareResponse = async (item) => {
    const payload = { title: item.instance_name || item.model, text: item.content };
    if (navigator.share) {
      try {
        await navigator.share(payload);
        return;
      } catch {
        // fall through
      }
    }
    await copyText(item.content, 'Share not available — copied instead');
  };

  const submitFeedback = async (item, value) => {
    if (!item.message_id) {
      toast.info('Feedback is available for fresh persisted responses.');
      setFeedbackMap((prev) => ({ ...prev, [item.run_step_id]: value }));
      return;
    }
    try {
      await hubApi.submitFeedback(item.message_id, value);
      setFeedbackMap((prev) => ({ ...prev, [item.message_id]: value }));
      toast.success(`Marked ${value === 'up' ? 'thumbs up' : 'thumbs down'}`);
    } catch (error) {
      toast.error(error.message || 'Feedback failed');
    }
  };

  const copySelected = async () => {
    if (selectedResponses.length === 0) return;
    const text = selectedResponses.map((item) => `# ${item.instance_name || item.model}\n\n${item.content}`).join('\n\n---\n\n');
    await copyText(text, 'Selected responses copied');
  };

  const shareSelected = async () => {
    if (selectedResponses.length === 0) return;
    const text = selectedResponses.map((item) => `# ${item.instance_name || item.model}\n\n${item.content}`).join('\n\n---\n\n');
    if (navigator.share) {
      try {
        await navigator.share({ title: 'AIMMH selected responses', text });
        return;
      } catch {
        // fall through
      }
    }
    await copyText(text, 'Share unavailable — copied selected responses');
  };

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Responses</h2>
            <p className="mt-1 text-xs text-zinc-500">Native formatting preserved. Compare vertically in stack mode or pane mode.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => setSourceType('runs')} className={`rounded-xl border px-3 py-2 text-xs ${sourceType === 'runs' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 text-zinc-300'}`}>
              Run responses
            </button>
            <button onClick={() => setSourceType('prompts')} className={`rounded-xl border px-3 py-2 text-xs ${sourceType === 'prompts' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 text-zinc-300'}`}>
              Prompt responses
            </button>
            <button onClick={() => setCompareMode('stack')} className={`rounded-xl border px-3 py-2 text-xs ${compareMode === 'stack' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 text-zinc-300'}`}>
              <span className="flex items-center gap-2"><Rows3 size={13} /> Stack</span>
            </button>
            <button onClick={() => setCompareMode('carousel')} className={`rounded-xl border px-3 py-2 text-xs ${compareMode === 'carousel' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 text-zinc-300'}`}>
              <span className="flex items-center gap-2"><LayoutPanelTop size={13} /> Pane mode</span>
            </button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          {sourceType === 'runs' ? (
            <>
              <select value={selectedRunId || ''} onChange={(event) => setSelectedRunId(event.target.value)} className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50">
                <option value="">Select a run</option>
                {runs.map((run) => <option key={run.run_id} value={run.run_id}>{run.label || run.run_id}</option>)}
              </select>
              <select value={selectedStageIndex} onChange={(event) => setSelectedStageIndex(Number(event.target.value))} className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50">
                {stageOptions.length === 0 ? <option value={0}>Stage 1</option> : stageOptions.map((stage) => <option key={stage.value} value={stage.value}>{stage.label}</option>)}
              </select>
            </>
          ) : (
            <>
              <select value={selectedPromptId || ''} onChange={(event) => setSelectedPromptId(event.target.value)} className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50 md:col-span-2">
                <option value="">Select a prompt batch</option>
                {prompts.map((prompt) => <option key={prompt.prompt_id} value={prompt.prompt_id}>{prompt.label || prompt.prompt}</option>)}
              </select>
            </>
          )}
          <div className="flex gap-2">
            <button onClick={copySelected} disabled={selectedResponses.length === 0} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 disabled:opacity-40"><span className="flex items-center gap-2"><Copy size={13} /> Copy selected</span></button>
            <button onClick={shareSelected} disabled={selectedResponses.length === 0} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 disabled:opacity-40"><span className="flex items-center gap-2"><Share2 size={13} /> Share selected</span></button>
          </div>
        </div>
      </div>

      {(sourceType === 'runs' && !selectedRun) || (sourceType === 'prompts' && !selectedPrompt) ? (
        <div className="rounded-2xl border border-dashed border-zinc-800 p-6 text-sm text-zinc-500">Select a {sourceType === 'runs' ? 'run' : 'prompt batch'} to compare responses.</div>
      ) : compareMode === 'carousel' ? (
        <ResponseCarousel
          items={stageResponses}
          activeIndex={activeIndex}
          setActiveIndex={setActiveIndex}
          fontScale={fontScale}
          setFontScale={setFontScale}
          selectedIds={selectedIds}
          feedbackMap={feedbackMap}
          onToggleSelected={toggleSelected}
          onFeedback={submitFeedback}
          onCopy={(item) => copyText(item.content)}
          onShare={shareResponse}
          synthesisIds={synthesisIds}
          onToggleSynthesis={(item) => onToggleSynthesisBlock(toSynthesisBlock(item))}
        />
      ) : (
        <div className="space-y-4">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-3 text-xs text-zinc-500">
            Pinch/spread to zoom font size. Switch to pane mode for two-finger vertical pane sliding while one-finger scrolling within each response.
          </div>
          {stageResponses.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-6 text-sm text-zinc-500">No responses yet for this selection.</div>
          ) : stageResponses.map((item) => (
            <ResponsePane
              key={item.run_step_id}
              item={item}
              selected={selectedIds.includes(item.run_step_id)}
              fontScale={fontScale}
              feedback={feedbackMap[item.message_id || item.run_step_id]}
              onToggleSelected={() => toggleSelected(item)}
              onFeedback={(value) => submitFeedback(item, value)}
              onCopy={() => copyText(item.content)}
              onShare={() => shareResponse(item)}
              synthesisSelected={synthesisIds.includes(item.run_step_id)}
              onToggleSynthesis={() => onToggleSynthesisBlock(toSynthesisBlock(item))}
            />
          ))}
        </div>
      )}
    </section>
  );
}
