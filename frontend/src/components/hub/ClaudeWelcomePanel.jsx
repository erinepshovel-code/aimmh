import React from 'react';
import { MessageSquare, Send, X } from 'lucide-react';
import { ResponseMarkdown } from './ResponseMarkdown';

export function ClaudeWelcomePanel({ welcomeInstance, prompts, onSendPrompt, busyKey }) {
  const [prompt, setPrompt] = React.useState('');
  const [latestPromptId, setLatestPromptId] = React.useState('');
  const [popoutOpen, setPopoutOpen] = React.useState(false);

  const latestPrompt = React.useMemo(() => {
    if (latestPromptId) {
      return prompts.find((item) => item.prompt_id === latestPromptId) || null;
    }
    return prompts[0] || null;
  }, [latestPromptId, prompts]);

  const latestResponse = latestPrompt?.responses?.[0] || null;

  const sendPrompt = async (event) => {
    event.preventDefault();
    if (!prompt.trim() || !welcomeInstance) return;
    const result = await onSendPrompt({ prompt, instance_ids: [welcomeInstance.instance_id] });
    setLatestPromptId(result.prompt_id);
    setPrompt('');
  };

  return (
    <section className="space-y-4" data-testid="claude-md-welcome-panel">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex items-center gap-2 text-zinc-100">
          <MessageSquare size={15} />
          <h2 className="text-base font-semibold">Claude.md Guide</h2>
        </div>
        <p className="mt-2 text-sm text-zinc-400">Ask the welcome guide anything about AIMMH workflows, instances, runs, synthesis, and registry setup.</p>
        <div className="mt-2 text-xs text-zinc-500">Guide model: {welcomeInstance ? `${welcomeInstance.name} · ${welcomeInstance.model_id}` : 'provisioning...'}</div>
      </div>

      <form onSubmit={sendPrompt} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="claude-md-chat-form">
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={4}
          placeholder="Ask the welcome model..."
          className="w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-emerald-500/50"
          data-testid="claude-md-chat-input"
        />
        <div className="mt-3 flex justify-end">
          <button
            type="submit"
            disabled={!welcomeInstance || busyKey === 'chat-send-prompt' || !prompt.trim()}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
            data-testid="claude-md-chat-send-button"
          >
            <span className="flex items-center gap-2"><Send size={14} /> Ask guide</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="claude-md-latest-response">
        <div className="mb-2 text-sm font-semibold text-zinc-100">Latest guide response</div>
        {!latestResponse ? (
          <div className="text-xs text-zinc-500">No response yet. Ask your first question above.</div>
        ) : (
          <>
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
              <ResponseMarkdown content={latestResponse.content} fontScale={1} />
            </div>
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setPopoutOpen(true)}
                className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white"
                data-testid="claude-md-popout-button"
              >
                Pop out response
              </button>
            </div>
          </>
        )}
      </div>

      {popoutOpen && latestResponse && (
        <div className="fixed inset-0 z-50 bg-black/70 p-4 sm:p-8" data-testid="claude-md-popout-overlay">
          <div className="mx-auto flex h-full w-full max-w-4xl flex-col rounded-3xl border border-zinc-700 bg-zinc-950" data-testid="claude-md-popout-modal">
            <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
              <div className="text-sm font-semibold text-zinc-100">Guide response popout</div>
              <button type="button" onClick={() => setPopoutOpen(false)} className="rounded-full border border-zinc-700 p-2 text-zinc-300 hover:text-white" data-testid="claude-md-popout-close-button">
                <X size={14} />
              </button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto p-4">
              <ResponseMarkdown content={latestResponse.content} fontScale={1} />
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
