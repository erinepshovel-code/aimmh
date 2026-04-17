// "lines of code":"0","lines of commented":"0"
import React from 'react';
import { Pause, Play, RotateCcw, SkipBack, SkipForward } from 'lucide-react';

const PATTERNS = [
  {
    id: 'fan_out',
    name: 'Fan Out',
    summary: 'Prompt is broadcast to all selected instances in parallel.',
    nodes: ['Hub', 'Model A', 'Model B', 'Model C'],
    steps: ['Hub → Model A', 'Hub → Model B', 'Hub → Model C', 'Model A/B/C → Hub'],
  },
  {
    id: 'daisy_chain',
    name: 'Daisy Chain',
    summary: 'Each model receives context from the previous model in sequence.',
    nodes: ['Hub', 'Model A', 'Model B', 'Model C'],
    steps: ['Hub → Model A', 'Model A → Model B', 'Model B → Model C', 'Model C → Hub'],
  },
  {
    id: 'room_all',
    name: 'Room (All Shared)',
    summary: 'All participants can see all participant outputs per round.',
    nodes: ['Hub', 'Room', 'Model A', 'Model B', 'Model C'],
    steps: ['Hub → Room', 'Room ↔ Model A/B/C', 'Room → Hub'],
  },
  {
    id: 'room_synthesized',
    name: 'Room (Synthesized)',
    summary: 'Participants exchange then synthesis model creates unified output.',
    nodes: ['Hub', 'Room', 'Models', 'Synth Model'],
    steps: ['Hub → Room', 'Room ↔ Models', 'Models → Synth Model', 'Synth Model → Hub'],
  },
  {
    id: 'council',
    name: 'Council',
    summary: 'Structured deliberation with rounds, initiative, and optional reactions.',
    nodes: ['Hub', 'Council DM', 'Participants'],
    steps: ['Hub → Council DM', 'DM orchestrates rounds', 'Participants exchange', 'Council result → Hub'],
  },
  {
    id: 'roleplay',
    name: 'Roleplay',
    summary: 'DM/GM drives player participants through roleplay turns.',
    nodes: ['Hub', 'DM/GM', 'Player A', 'Player B'],
    steps: ['Hub → DM/GM', 'DM/GM → Players', 'Players → DM/GM', 'DM/GM → Hub'],
  },
];

const ABSENT_PATTERNS = ['debate', 'tournament', 'pipeline_revise', 'vote'];

/**
 * PatternVisualizerPanel
 * What: Visual guide for currently supported orchestration patterns.
 * How: Step-based animated sequence for each pattern with controls.
 */
export function PatternVisualizerPanel() {
  const [patternId, setPatternId] = React.useState(PATTERNS[0].id);
  const [stepIndex, setStepIndex] = React.useState(0);
  const [isPlaying, setIsPlaying] = React.useState(true);
  const [speedMs, setSpeedMs] = React.useState(1100);

  const pattern = React.useMemo(
    () => PATTERNS.find((item) => item.id === patternId) || PATTERNS[0],
    [patternId],
  );

  React.useEffect(() => {
    setStepIndex(0);
  }, [patternId]);

  React.useEffect(() => {
    if (!isPlaying) return undefined;
    const timer = window.setInterval(() => {
      setStepIndex((prev) => (prev + 1) % pattern.steps.length);
    }, speedMs);
    return () => window.clearInterval(timer);
  }, [isPlaying, pattern.steps.length, speedMs]);

  const nextStep = () => setStepIndex((prev) => (prev + 1) % pattern.steps.length);
  const prevStep = () => setStepIndex((prev) => (prev - 1 + pattern.steps.length) % pattern.steps.length);

  return (
    <section className="space-y-4" data-testid="pattern-visualizer-panel">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="pattern-visualizer-header">
        <div className="text-xs uppercase tracking-[0.2em] text-zinc-500">AIMMH Pattern Visualizer</div>
        <h2 className="mt-2 text-base font-semibold text-zinc-100">Multi-model orchestration message flow</h2>
        <p className="mt-1 text-sm text-zinc-400">Animated overview of the six implemented orchestration patterns.</p>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="pattern-selector-wrap">
        <div className="mb-2 text-xs text-zinc-400">Patterns</div>
        <div className="flex flex-wrap gap-2">
          {PATTERNS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setPatternId(item.id)}
              className={`rounded-xl border px-3 py-1.5 text-xs ${patternId === item.id ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-zinc-700 text-zinc-300'}`}
              data-testid={`pattern-select-${item.id}`}
            >
              {item.name}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="pattern-canvas">
        <div className="mb-2 text-sm font-semibold text-zinc-100" data-testid="pattern-active-name">{pattern.name}</div>
        <p className="text-xs text-zinc-400" data-testid="pattern-active-summary">{pattern.summary}</p>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4" data-testid="pattern-node-list">
          {pattern.nodes.map((node) => (
            <div key={node} className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-xs text-zinc-300" data-testid={`pattern-node-${node.replace(/[^a-zA-Z0-9]/g, '-')}`}>
              {node}
            </div>
          ))}
        </div>

        <div className="mt-4 space-y-2" data-testid="pattern-step-list">
          {pattern.steps.map((step, idx) => (
            <div
              key={step}
              className={`rounded-xl border px-3 py-2 text-sm ${idx === stepIndex ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-zinc-800 bg-zinc-950/60 text-zinc-300'}`}
              data-testid={`pattern-step-${idx}`}
            >
              {idx + 1}. {step}
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2" data-testid="pattern-controls">
          <button type="button" onClick={() => setIsPlaying((prev) => !prev)} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-200" data-testid="pattern-toggle-play-button">
            <span className="inline-flex items-center gap-2">{isPlaying ? <Pause size={12} /> : <Play size={12} />} {isPlaying ? 'Pause' : 'Play'}</span>
          </button>
          <button type="button" onClick={prevStep} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-300" data-testid="pattern-prev-step-button"><span className="inline-flex items-center gap-1"><SkipBack size={12} /> Prev</span></button>
          <button type="button" onClick={nextStep} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-300" data-testid="pattern-next-step-button"><span className="inline-flex items-center gap-1">Next <SkipForward size={12} /></span></button>
          <button type="button" onClick={() => setStepIndex(0)} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-300" data-testid="pattern-reset-step-button"><span className="inline-flex items-center gap-1"><RotateCcw size={12} /> Reset</span></button>
          <label className="ml-auto inline-flex items-center gap-2 text-xs text-zinc-400" data-testid="pattern-speed-control">
            Speed
            <select value={speedMs} onChange={(e) => setSpeedMs(Number(e.target.value))} className="rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-200" data-testid="pattern-speed-select">
              <option value={700}>Fast</option>
              <option value={1100}>Normal</option>
              <option value={1600}>Slow</option>
            </select>
          </label>
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="pattern-absent-list">
        <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">Conceptually absent</div>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-300">
          {ABSENT_PATTERNS.map((item) => (
            <span key={item} className="rounded-full border border-zinc-700 px-2 py-1" data-testid={`pattern-absent-${item}`}>{item}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

// "lines of code":"0","lines of commented":"0"