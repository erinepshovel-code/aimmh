import React from 'react';
import { CheckCheck, ChevronLeft, ChevronRight, Loader2, Lock, MessageSquareShare, Send, Sparkles, Unlock } from 'lucide-react';
import { ResponseMarkdown } from './ResponseMarkdown';
import { CollapsibleSection } from './CollapsibleSection';
import { hubApi } from '../../lib/hubApi';
const CHAT_FONT_SCALE_KEY = 'aimmh-chat-font-scale';
export function HubMultiChatPanel({
  instances,
  prompts,
  selectedPromptId,
  setSelectedPromptId,
  onSendPrompt,
  busyKey,
  onAddSynthesisBlock,
  onSwipeTab,
}) {
  const [prompt, setPrompt] = React.useState('');
  const [selectedInstanceIds, setSelectedInstanceIds] = React.useState([]);
  const [draftLoaded, setDraftLoaded] = React.useState(false);
  const [promptIndex, setPromptIndex] = React.useState(0);
  const [lockedByPrompt, setLockedByPrompt] = React.useState({});
  const [cursorByPrompt, setCursorByPrompt] = React.useState({});
  const [fontScale, setFontScale] = React.useState(1);
  const [gestureFontMode, setGestureFontMode] = React.useState(false);
  const gestureSurfaceRef = React.useRef(null);
  const activeInstances = instances.filter((item) => !item.archived);
  const chatDraftKey = React.useMemo(() => `chat-draft:${selectedPromptId || 'new'}`, [selectedPromptId]);
  React.useEffect(() => {
    if (!selectedPromptId && prompts[0]?.prompt_id) {
      setSelectedPromptId(prompts[0].prompt_id);
    }
  }, [prompts, selectedPromptId, setSelectedPromptId]);
  React.useEffect(() => {
    let active = true;
    setDraftLoaded(false);
    const loadDraft = async () => {
      try {
        const state = await hubApi.getState(chatDraftKey);
        if (!active) return;
        setPrompt(state?.payload?.prompt || '');
        setSelectedInstanceIds(Array.isArray(state?.payload?.selectedInstanceIds) ? state.payload.selectedInstanceIds : []);
      } catch {
        if (!active) return;
        setPrompt('');
      } finally {
        if (active) setDraftLoaded(true);
      }
    };
    loadDraft();
    return () => {
      active = false;
    };
  }, [chatDraftKey]);
  React.useEffect(() => {
    if (!draftLoaded) return;
    const timer = window.setTimeout(() => {
      hubApi.setState(chatDraftKey, {
        prompt,
        selectedInstanceIds,
      }).catch(() => {});
    }, 350);
    return () => window.clearTimeout(timer);
  }, [chatDraftKey, draftLoaded, prompt, selectedInstanceIds]);
  React.useEffect(() => {
    if (activeInstances.length === 0) return;
    setSelectedInstanceIds((prev) => {
      if (prev.length > 0) return prev.filter((id) => activeInstances.some((item) => item.instance_id === id));
      return activeInstances.map((item) => item.instance_id);
    });
  }, [activeInstances]);
  React.useEffect(() => {
    try {
      const stored = Number(window.localStorage.getItem(CHAT_FONT_SCALE_KEY) || '1');
      if (!Number.isNaN(stored)) setFontScale(Math.max(0.8, Math.min(1.8, stored)));
    } catch {
      setFontScale(1);
    }
  }, []);
  React.useEffect(() => {
    try {
      window.localStorage.setItem(CHAT_FONT_SCALE_KEY, String(fontScale));
    } catch {
      // noop
    }
  }, [fontScale]);
  React.useEffect(() => {
    if (prompts.length === 0) {
      setPromptIndex(0);
      return;
    }
    const foundIndex = prompts.findIndex((item) => item.prompt_id === selectedPromptId);
    if (foundIndex >= 0) {
      setPromptIndex(foundIndex);
      return;
    }
    const safeIndex = Math.min(promptIndex, prompts.length - 1);
    setPromptIndex(safeIndex);
    setSelectedPromptId(prompts[safeIndex].prompt_id);
  }, [promptIndex, prompts, selectedPromptId, setSelectedPromptId]);
  const toggleInstance = (instanceId) => {
    setSelectedInstanceIds((prev) => prev.includes(instanceId) ? prev.filter((id) => id !== instanceId) : [...prev, instanceId]);
  };
  const allRecipientsSelected = activeInstances.length > 0 && selectedInstanceIds.length === activeInstances.length;
  const toggleSelectAllRecipients = () => {
    setSelectedInstanceIds(allRecipientsSelected ? [] : activeInstances.map((instance) => instance.instance_id));
  };
  const submit = async (event) => {
    event.preventDefault();
    if (!prompt.trim() || selectedInstanceIds.length === 0) return;
    const detail = await onSendPrompt({ prompt, instance_ids: selectedInstanceIds });
    setPrompt('');
    hubApi.deleteState(chatDraftKey).catch(() => {});
    setSelectedPromptId(detail.prompt_id);
  };
  const selectedPrompt = prompts[promptIndex] || null;
  const responses = selectedPrompt?.responses || [];
  const lockedIds = selectedPrompt ? (lockedByPrompt[selectedPrompt.prompt_id] || []) : [];
  const unlockedResponses = responses.filter((item) => {
    const responseId = item.message_id || `${selectedPrompt.prompt_id}-${item.instance_id}`;
    return !lockedIds.includes(responseId);
  });
  const activeCursor = selectedPrompt ? (cursorByPrompt[selectedPrompt.prompt_id] || 0) : 0;
  const activeResponse = unlockedResponses.length > 0 ? unlockedResponses[Math.min(activeCursor, unlockedResponses.length - 1)] : null;
  const toBlock = React.useCallback((promptItem, responseItem) => ({
    source_type: 'chat_prompt_response',
    source_id: responseItem.message_id || `${promptItem.prompt_id}-${responseItem.instance_id}`,
    source_label: `Prompt ${promptItem.prompt_id} · ${responseItem.instance_name || responseItem.model}`,
    instance_id: responseItem.instance_id,
    instance_name: responseItem.instance_name,
    model: responseItem.model,
    content: responseItem.content,
  }), []);
  const lockCurrentAndAdvance = () => {
    if (!selectedPrompt || !activeResponse) return;
    const promptId = selectedPrompt.prompt_id;
    const responseId = activeResponse.message_id || `${promptId}-${activeResponse.instance_id}`;
    setLockedByPrompt((prev) => {
      const existing = prev[promptId] || [];
      const withoutDupes = [...existing.filter((id) => id !== responseId), responseId];
      const capped = withoutDupes.length > 3 ? withoutDupes.slice(withoutDupes.length - 3) : withoutDupes;
      return { ...prev, [promptId]: capped };
    });
    setCursorByPrompt((prev) => ({ ...prev, [promptId]: 0 }));
  };
  const unlockResponse = (promptId, responseId) => {
    setLockedByPrompt((prev) => ({ ...prev, [promptId]: (prev[promptId] || []).filter((id) => id !== responseId) }));
  };
  const nextPrompt = () => {
    if (prompts.length === 0) return;
    const nextIndex = (promptIndex + 1) % prompts.length;
    setPromptIndex(nextIndex);
    setSelectedPromptId(prompts[nextIndex].prompt_id);
  };
  const prevPrompt = () => {
    if (prompts.length === 0) return;
    const prevIndex = (promptIndex - 1 + prompts.length) % prompts.length;
    setPromptIndex(prevIndex);
    setSelectedPromptId(prompts[prevIndex].prompt_id);
  };
  const nextResponse = () => {
    if (!selectedPrompt || unlockedResponses.length === 0) return;
    const promptId = selectedPrompt.prompt_id;
    const nextCursor = (activeCursor + 1) % unlockedResponses.length;
    setCursorByPrompt((prev) => ({ ...prev, [promptId]: nextCursor }));
  };
  const prevResponse = () => {
    if (!selectedPrompt || unlockedResponses.length === 0) return;
    const promptId = selectedPrompt.prompt_id;
    const nextCursor = (activeCursor - 1 + unlockedResponses.length) % unlockedResponses.length;
    setCursorByPrompt((prev) => ({ ...prev, [promptId]: nextCursor }));
  };
  const lockedResponses = selectedPrompt
    ? responses.filter((item) => lockedIds.includes(item.message_id || `${selectedPrompt.prompt_id}-${item.instance_id}`))
    : [];
  React.useEffect(() => {
    const surface = gestureSurfaceRef.current;
    if (!surface) return;
    const isTouchMobile = (typeof window !== 'undefined')
      && (window.matchMedia?.('(pointer: coarse)')?.matches || 'ontouchstart' in window);
    if (!isTouchMobile) return;
    let touchCount = 0;
    let startX = 0;
    let lastX = 0;
    let lastTapOne = 0;
    let lastTapTwo = 0;
    let lastDistance = 0;
    const avgX = (touches) => {
      if (!touches || touches.length === 0) return 0;
      let total = 0;
      for (let i = 0; i < touches.length; i += 1) total += touches[i].clientX;
      return total / touches.length;
    };
    const distance = (touches) => {
      if (!touches || touches.length < 2) return 0;
      const dx = touches[0].clientX - touches[1].clientX;
      const dy = touches[0].clientY - touches[1].clientY;
      return Math.sqrt((dx * dx) + (dy * dy));
    };
    const onTouchStart = (event) => {
      touchCount = event.touches.length;
      startX = avgX(event.touches);
      lastX = startX;
      const now = Date.now();
      if (touchCount === 1) {
        if (now - lastTapOne < 280) {
          lockCurrentAndAdvance();
        }
        lastTapOne = now;
      }
      if (touchCount === 2) {
        if (now - lastTapTwo < 320) {
          setGestureFontMode((prev) => !prev);
          event.preventDefault();
        }
        lastTapTwo = now;
        lastDistance = distance(event.touches);
      }
    };
    const onTouchMove = (event) => {
      if (event.touches.length > 0) {
        lastX = avgX(event.touches);
      }
      if (gestureFontMode && event.touches.length === 2) {
        const nextDistance = distance(event.touches);
        if (lastDistance > 0) {
          const ratio = nextDistance / lastDistance;
          if (Math.abs(ratio - 1) > 0.01) {
            setFontScale((prev) => Math.max(0.8, Math.min(1.8, prev * ratio)));
          }
        }
        lastDistance = nextDistance;
        event.preventDefault();
      }
    };
    const onTouchEnd = () => {
      const deltaX = lastX - startX;
      if (Math.abs(deltaX) < 48) {
        touchCount = 0;
        return;
      }
      const swipedLeft = deltaX < 0;
      if (touchCount === 1) {
        if (swipedLeft) nextResponse();
        else prevResponse();
      } else if (touchCount === 2) {
        if (swipedLeft) nextPrompt();
        else prevPrompt();
      } else if (touchCount >= 3 && onSwipeTab) {
        onSwipeTab(swipedLeft ? 'next' : 'prev');
      }
      touchCount = 0;
    };
    surface.addEventListener('touchstart', onTouchStart, { passive: false });
    surface.addEventListener('touchmove', onTouchMove, { passive: false });
    surface.addEventListener('touchend', onTouchEnd);
    surface.addEventListener('touchcancel', onTouchEnd);
    return () => {
      surface.removeEventListener('touchstart', onTouchStart);
      surface.removeEventListener('touchmove', onTouchMove);
      surface.removeEventListener('touchend', onTouchEnd);
      surface.removeEventListener('touchcancel', onTouchEnd);
    };
  }, [gestureFontMode, lockCurrentAndAdvance, nextPrompt, nextResponse, onSwipeTab, prevPrompt, prevResponse]);
  return (
    <div className="space-y-4" data-testid="hub-multi-chat-panel">
      <CollapsibleSection
        title="Direct multi-instance chat"
        subtitle="Send one prompt to selected instances."
        icon={MessageSquareShare}
        defaultOpen={false}
        testId="hub-direct-chat-section"
      >
        <form onSubmit={submit} className="mt-4 space-y-4">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3" data-testid="chat-recipient-list">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="text-xs font-medium text-zinc-300">Recipients</div>
              <button type="button" onClick={toggleSelectAllRecipients} className="rounded-xl border border-zinc-800 px-3 py-1 text-xs text-zinc-300" data-testid="chat-select-all-instances-button">
                <span className="flex items-center gap-2"><CheckCheck size={12} /> {allRecipientsSelected ? 'Clear all' : 'Select all instances'}</span>
              </button>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {activeInstances.length === 0 ? <div className="text-xs text-zinc-500">Create instances first in the instantiation tab.</div> : activeInstances.map((instance) => (
                <label key={instance.instance_id} className="flex items-start gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-2 text-xs text-zinc-300" data-testid={`chat-recipient-option-${instance.instance_id}`}>
                  <input type="checkbox" checked={selectedInstanceIds.includes(instance.instance_id)} onChange={() => toggleInstance(instance.instance_id)} className="mt-0.5" data-testid={`chat-recipient-checkbox-${instance.instance_id}`} aria-label={`chat recipient ${instance.name}`} />
                  <span>{instance.name} · {instance.model_id}</span>
                </label>
              ))}
            </div>
          </div>
          <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={4} placeholder="Broadcast prompt to selected instances"
            data-testid="chat-prompt-textarea"
            className="w-full rounded-2xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm text-zinc-100 outline-none focus:border-emerald-500/50" />
          <button type="submit" disabled={!prompt.trim() || selectedInstanceIds.length === 0 || busyKey === 'send-chat-prompt'} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-60" data-testid="chat-send-button">
            <span className="flex items-center gap-2">{busyKey === 'send-chat-prompt' ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send to all selected</span>
          </button>
        </form>
      </CollapsibleSection>
      <CollapsibleSection
        title="Prompt carousel"
        subtitle="Gesture controls: 1-finger swipe=response, 2-finger swipe=prompt, 3-finger swipe=tab, 1-finger double tap=lock, 2-finger double tap toggles pinch font mode."
        icon={Sparkles}
        defaultOpen={false}
        testId="chat-prompt-carousel-section"
        headerRight={<div className="text-[11px] text-zinc-400" data-testid="chat-font-scale-indicator">Font {fontScale.toFixed(2)}x {gestureFontMode ? '(pinch mode)' : ''}</div>}
      >
        <div ref={gestureSurfaceRef} data-testid="chat-gesture-surface">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-base font-semibold text-zinc-100">Prompt carousel</div>
            <div className="text-xs text-zinc-500">One prompt visible at a time. Lock up to three responses.</div>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={prevPrompt} className="rounded-xl border border-zinc-800 px-2 py-1 text-xs text-zinc-300" data-testid="chat-prompt-carousel-prev-button"><span className="flex items-center gap-1"><ChevronLeft size={12} /> Prev</span></button>
            <div className="text-xs text-zinc-500" data-testid="chat-prompt-carousel-index">{prompts.length === 0 ? 0 : promptIndex + 1}/{prompts.length}</div>
            <button type="button" onClick={nextPrompt} className="rounded-xl border border-zinc-800 px-2 py-1 text-xs text-zinc-300" data-testid="chat-prompt-carousel-next-button"><span className="flex items-center gap-1">Next <ChevronRight size={12} /></span></button>
          </div>
        </div>
        {!selectedPrompt ? (
          <div className="mt-4 rounded-2xl border border-dashed border-zinc-800 p-5 text-sm text-zinc-500">No direct chat prompts yet.</div>
        ) : (
          <div className="mt-4 space-y-4">
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4" data-testid={`chat-prompt-card-${selectedPrompt.prompt_id}`}>
              <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">Prompt</div>
              <div className="mt-2 whitespace-pre-wrap text-sm text-zinc-100">{selectedPrompt.prompt}</div>
              <div className="mt-2 text-xs text-zinc-500">{responses.length} responses</div>
            </article>
            <div className="space-y-3" data-testid="chat-locked-responses-stack">
              {lockedResponses.map((item, index) => {
                const responseId = item.message_id || `${selectedPrompt.prompt_id}-${item.instance_id}`;
                return (
                  <article key={responseId} className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-3" data-testid={`chat-locked-response-${responseId}`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-xs text-amber-200">Locked #{index + 1} · {item.instance_name} · {item.model}</div>
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => onAddSynthesisBlock(toBlock(selectedPrompt, item))} className="rounded-xl border border-violet-500/30 bg-violet-500/10 px-2 py-1 text-xs text-violet-200" data-testid={`chat-send-to-synthesis-locked-${responseId}`}>
                          <span className="flex items-center gap-1"><Sparkles size={11} /> Send to synthesis</span>
                        </button>
                        <button type="button" onClick={() => unlockResponse(selectedPrompt.prompt_id, responseId)} className="rounded-xl border border-zinc-700 px-2 py-1 text-xs text-zinc-300" data-testid={`chat-unlock-response-${responseId}`}>
                          <span className="flex items-center gap-1"><Unlock size={11} /> Unlock</span>
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 max-h-40 overflow-auto rounded-xl border border-zinc-800 bg-zinc-900/60 p-3"><ResponseMarkdown content={item.content} fontScale={fontScale} /></div>
                  </article>
                );
              })}
            </div>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4" data-testid="chat-active-response-card">
              {!activeResponse ? (
                <div className="text-sm text-zinc-500">All responses are locked. Unlock one to continue viewing.</div>
              ) : (
                <>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-zinc-500">Visible response</div>
                      <div className="mt-1 text-sm text-zinc-100">{activeResponse.instance_name} · {activeResponse.model}</div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => onAddSynthesisBlock(toBlock(selectedPrompt, activeResponse))} className="rounded-xl border border-violet-500/30 bg-violet-500/10 px-2 py-1 text-xs text-violet-200" data-testid="chat-send-to-synthesis-active-button">
                        <span className="flex items-center gap-1"><Sparkles size={11} /> Send to synthesis</span>
                      </button>
                      <button type="button" onClick={lockCurrentAndAdvance} className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-200" data-testid="chat-lock-and-next-button">
                        <span className="flex items-center gap-1"><Lock size={11} /> Lock + next</span>
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 max-h-[48vh] overflow-auto rounded-xl border border-zinc-800 bg-zinc-900/60 p-3"><ResponseMarkdown content={activeResponse.content} fontScale={fontScale} /></div>
                </>
              )}
              <div className="mt-3 flex items-center gap-2">
                <button type="button" onClick={prevResponse} className="rounded-xl border border-zinc-800 px-2 py-1 text-xs text-zinc-300" data-testid="chat-response-prev-button"><span className="flex items-center gap-1"><ChevronLeft size={12} /> Prev response</span></button>
                <button type="button" onClick={nextResponse} className="rounded-xl border border-zinc-800 px-2 py-1 text-xs text-zinc-300" data-testid="chat-response-next-button"><span className="flex items-center gap-1">Next response <ChevronRight size={12} /></span></button>
              </div>
            </article>
          </div>
        )}
        </div>
      </CollapsibleSection>
    </div>
  );
}
