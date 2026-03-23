import React from 'react';
import { Loader2, MessageSquareShare, Send } from 'lucide-react';

export function HubMultiChatPanel({
  instances,
  prompts,
  selectedPromptId,
  setSelectedPromptId,
  onSendPrompt,
  busyKey,
}) {
  const [prompt, setPrompt] = React.useState('');
  const [selectedInstanceIds, setSelectedInstanceIds] = React.useState([]);

  const activeInstances = instances.filter((item) => !item.archived);
  const selectedPrompt = prompts.find((item) => item.prompt_id === selectedPromptId) || prompts[0] || null;

  React.useEffect(() => {
    if (!selectedPromptId && prompts[0]?.prompt_id) {
      setSelectedPromptId(prompts[0].prompt_id);
    }
  }, [prompts, selectedPromptId, setSelectedPromptId]);

  const toggleInstance = (instanceId) => {
    setSelectedInstanceIds((prev) => prev.includes(instanceId) ? prev.filter((id) => id !== instanceId) : [...prev, instanceId]);
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!prompt.trim() || selectedInstanceIds.length === 0) return;
    const detail = await onSendPrompt({ prompt, instance_ids: selectedInstanceIds });
    setPrompt('');
    setSelectedPromptId(detail.prompt_id);
  };

  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="flex items-center gap-2 text-zinc-100"><MessageSquareShare size={16} /> <h2 className="text-base font-semibold">Direct multi-instance chat</h2></div>
        <p className="mt-1 text-xs text-zinc-500">Send the exact same prompt to one or more selected instances at once. Each reply appends to that instance’s private thread history.</p>
        <form onSubmit={submit} className="mt-4 space-y-4">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
            <div className="mb-2 text-xs font-medium text-zinc-300">Recipients</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {activeInstances.length === 0 ? <div className="text-xs text-zinc-500">Create instances first in the instantiation tab.</div> : activeInstances.map((instance) => (
                <label key={instance.instance_id} className="flex items-start gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-300">
                  <input type="checkbox" checked={selectedInstanceIds.includes(instance.instance_id)} onChange={() => toggleInstance(instance.instance_id)} className="mt-0.5" />
                  <span>{instance.name} · {instance.model_id}</span>
                </label>
              ))}
            </div>
          </div>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={4} placeholder="Broadcast prompt to selected instances"
            className="w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-emerald-500/50" />
          <button type="submit" disabled={!prompt.trim() || selectedInstanceIds.length === 0 || busyKey === 'send-chat-prompt'} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-60">
            <span className="flex items-center gap-2">{busyKey === 'send-chat-prompt' ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send to all selected</span>
          </button>
        </form>
      </section>

      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
        <div className="text-base font-semibold text-zinc-100">Prompt-indexed responses</div>
        <p className="mt-1 text-xs text-zinc-500">Every response is grouped by prompt batch and instance.</p>
        <div className="mt-4 space-y-3">
          {prompts.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No direct chat prompts yet.</div>
          ) : prompts.map((promptItem) => (
            <button key={promptItem.prompt_id} onClick={() => setSelectedPromptId(promptItem.prompt_id)} className={`w-full rounded-2xl border p-4 text-left transition ${selectedPromptId === promptItem.prompt_id ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-zinc-800 bg-zinc-950/60 hover:border-zinc-700'}`}>
              <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">Prompt batch</div>
              <div className="mt-2 text-sm text-zinc-100">{promptItem.prompt}</div>
              <div className="mt-3 text-xs text-zinc-500">{promptItem.responses?.length || 0} responses · {promptItem.instance_names?.join(', ')}</div>
            </button>
          ))}
        </div>
      </section>

      {selectedPrompt && (
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="text-sm font-semibold text-zinc-100">Selected prompt</div>
          <div className="mt-2 whitespace-pre-wrap text-sm text-zinc-300">{selectedPrompt.prompt}</div>
          <div className="mt-4 space-y-3">
            {(selectedPrompt.responses || []).map((response) => (
              <article key={response.message_id || `${response.prompt_id}-${response.instance_id}`} className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-sm font-medium text-zinc-100">{response.instance_name}</div>
                  <span className="rounded-full border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-400">{response.model}</span>
                </div>
                <div className="mt-2 whitespace-pre-wrap text-sm text-zinc-300">{response.content}</div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
