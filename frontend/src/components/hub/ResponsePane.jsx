import React from 'react';
import { CheckCircle2, Copy, Share2, ThumbsDown, ThumbsUp } from 'lucide-react';
import { ResponseMarkdown } from './ResponseMarkdown';

export function ResponsePane({
  item,
  selected,
  fontScale,
  feedback,
  onToggleSelected,
  onFeedback,
  onCopy,
  onShare,
}) {
  return (
    <article className={`flex h-full flex-col rounded-3xl border p-4 transition ${selected ? 'border-emerald-500/40 bg-emerald-500/5 shadow-[0_10px_40px_rgba(16,185,129,0.12)]' : 'border-zinc-800 bg-zinc-950/70'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-100">{item.instance_name || item.model}</h3>
            <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-400">{item.model}</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-500">
            <span>round {item.round_num + 1}</span>
            <span>step {item.step_num}</span>
            <span>{item.role}</span>
            {item.thread_id && <span>{item.thread_id}</span>}
          </div>
        </div>
        <button onClick={onToggleSelected} className={`rounded-full border px-3 py-1 text-[11px] ${selected ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-zinc-100'}`}>
          <span className="flex items-center gap-1"><CheckCircle2 size={11} /> {selected ? 'Selected' : 'Select'}</span>
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button onClick={() => onFeedback('up')} className={`rounded-xl border px-3 py-2 text-xs ${feedback === 'up' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-zinc-800 text-zinc-300 hover:text-white'}`}>
          <span className="flex items-center gap-2"><ThumbsUp size={13} /> Up</span>
        </button>
        <button onClick={() => onFeedback('down')} className={`rounded-xl border px-3 py-2 text-xs ${feedback === 'down' ? 'border-red-500/30 bg-red-500/10 text-red-300' : 'border-zinc-800 text-zinc-300 hover:text-white'}`}>
          <span className="flex items-center gap-2"><ThumbsDown size={13} /> Down</span>
        </button>
        <button onClick={onCopy} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white">
          <span className="flex items-center gap-2"><Copy size={13} /> Copy</span>
        </button>
        <button onClick={onShare} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white">
          <span className="flex items-center gap-2"><Share2 size={13} /> Share</span>
        </button>
      </div>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <ResponseMarkdown content={item.content} fontScale={fontScale} />
      </div>
    </article>
  );
}
