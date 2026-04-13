// "lines of code":"115","lines of commented":"5"
import React from 'react';
import { BookOpenText, Loader2, RefreshCw, Send, Wrench } from 'lucide-react';
import { hubApi } from '../../lib/hubApi';
import { buildReadmeMarkdown } from '../../lib/readme.ts';
import { ResponseMarkdown } from './ResponseMarkdown';

/**
 * HelpReadmePanel
 * What: Lets users ask the help model for a dynamic README built from code registry.
 * How: Pulls registry -> assembles markdown -> sends to help instance as context.
 */
export function HelpReadmePanel({ welcomeInstance, prompts, onSendPrompt, busyKey }) {
  const [question, setQuestion] = React.useState('How is this app structured and where should I extend next?');
  const [latestPromptId, setLatestPromptId] = React.useState('');
  const [registry, setRegistry] = React.useState(null);
  const [markdown, setMarkdown] = React.useState('');
  const [loadingRegistry, setLoadingRegistry] = React.useState(false);
  const [sending, setSending] = React.useState(false);

  const latestPrompt = React.useMemo(() => {
    if (latestPromptId) return prompts.find((item) => item.prompt_id === latestPromptId) || null;
    return prompts[0] || null;
  }, [latestPromptId, prompts]);

  const latestResponse = latestPrompt?.responses?.[0] || null;

  const refreshRegistry = async (syncMarkers = false) => {
    setLoadingRegistry(true);
    try {
      const payload = syncMarkers ? await hubApi.syncReadmeRegistry() : await hubApi.getReadmeRegistry();
      setRegistry(payload);
      const md = buildReadmeMarkdown(payload, question);
      setMarkdown(md);
      return { payload, md };
    } finally {
      setLoadingRegistry(false);
    }
  };

  const askHelpModel = async (event) => {
    event.preventDefault();
    if (!welcomeInstance || !question.trim() || sending || busyKey === 'chat-send-prompt') return;
    setSending(true);
    try {
      const { payload, md } = await refreshRegistry(false);
      const prompt = [
        'You are the AIMMH Help Model.',
        'Answer the user using the dynamic README context below.',
        '',
        '--- DYNAMIC README CONTEXT START ---',
        md || buildReadmeMarkdown(payload, question),
        '--- DYNAMIC README CONTEXT END ---',
        '',
        `User request: ${question}`,
      ].join('\n');
      const result = await onSendPrompt({ prompt, instance_ids: [welcomeInstance.instance_id], label: 'help-readme' });
      setLatestPromptId(result.prompt_id);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="space-y-4" data-testid="help-readme-panel">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex items-center gap-2 text-zinc-100"><BookOpenText size={15} /><h2 className="text-base font-semibold">Dynamic README Help</h2></div>
        <p className="mt-2 text-sm text-zinc-400">Ask the help model. It will assemble README context from live module registry metadata.</p>
        <div className="mt-2 text-xs text-zinc-500">Help model: {welcomeInstance ? `${welcomeInstance.name} · ${welcomeInstance.model_id}` : 'provisioning...'}</div>
      </div>

      <form onSubmit={askHelpModel} className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="help-readme-form">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={4}
          placeholder="Ask for architecture, module docs, extension points, or implementation guidance."
          className="w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-emerald-500/50"
          data-testid="help-readme-question-input"
        />

        <div className="mt-3 flex flex-wrap justify-between gap-2">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => refreshRegistry(false)}
              disabled={loadingRegistry}
              className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white disabled:opacity-60"
              data-testid="help-readme-refresh-registry-button"
            >
              <span className="flex items-center gap-2">{loadingRegistry ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} Refresh registry</span>
            </button>
            <button
              type="button"
              onClick={() => refreshRegistry(true)}
              disabled={loadingRegistry}
              className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white disabled:opacity-60"
              data-testid="help-readme-sync-markers-button"
            >
              <span className="flex items-center gap-2">{loadingRegistry ? <Loader2 size={12} className="animate-spin" /> : <Wrench size={12} />} Sync metrics markers</span>
            </button>
          </div>

          <button
            type="submit"
            disabled={!welcomeInstance || !question.trim() || sending || busyKey === 'chat-send-prompt'}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
            data-testid="help-readme-ask-button"
          >
            <span className="flex items-center gap-2">{sending || busyKey === 'chat-send-prompt' ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Ask help model</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="help-readme-preview-panel">
        <div className="text-sm font-semibold text-zinc-100">Assembled README preview</div>
        <div className="mt-2 max-h-72 overflow-auto rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300">
          {markdown ? <ResponseMarkdown content={markdown} fontScale={1} /> : <div>Click “Refresh registry” to assemble README.md context.</div>}
        </div>
      </div>

      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="help-readme-latest-response-panel">
        <div className="mb-2 text-sm font-semibold text-zinc-100">Latest help response</div>
        {!latestResponse ? (
          <div className="text-xs text-zinc-500">No response yet.</div>
        ) : (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4"><ResponseMarkdown content={latestResponse.content} fontScale={1} /></div>
        )}
      </div>
    </section>
  );
}

// "lines of code":"115","lines of commented":"5"
