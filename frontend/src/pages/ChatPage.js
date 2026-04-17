// "lines of code":"256","lines of commented":"3"
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Settings, LogOut, Menu, MessageSquare, Loader2, FileUp, X } from 'lucide-react';
import {
  ModelSelector,
  ContextPanel,
  ModeSelector,
  StackLayout,
  SplitLayout,
  CarouselLayout,
  SynthesisBar,
  Sidebar,
  LayoutToggle,
  LAYOUTS,
  MODES,
} from '../components/chat/ChatPageSections';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
// ---- Main ChatPage ----
export default function ChatPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { threads, currentThread, messages, loading, streaming, error, fetchThreads, loadThread, sendPrompt, newThread, submitFeedback, addOptimisticMessage } = useChat();

  const [input, setInput] = useState('');
  const [registry, setRegistry] = useState([]);
  const [selectedModels, setSelectedModels] = useState(['gpt-4o-mini']);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showModels, setShowModels] = useState(false);
  const [showContext, setShowContext] = useState(false);
  const [globalContext, setGlobalContext] = useState('');
  const [perModelCtx, setPerModelCtx] = useState({});
  const [mode, setMode] = useState(MODES.NORMAL);
  const [rounds, setRounds] = useState(1);
  const [synthModel, setSynthModel] = useState('');
  const [layout, setLayout] = useState(() => localStorage.getItem('hub_layout') || LAYOUTS.STACK);
  const [splitLocked, setSplitLocked] = useState(false);
  const [selectedResponseIds, setSelectedResponseIds] = useState(new Set());
  const [synthesizing, setSynthesizing] = useState(false);
  const [advancedLoading, setAdvancedLoading] = useState(false);
  const responseEndRef = useRef(null);
  const textareaRef = useRef(null);

  const allModelIds = registry.flatMap(d => d.models.map(m => m.model_id));

  useEffect(() => { localStorage.setItem('hub_layout', layout); }, [layout]);
  useEffect(() => {
    fetchThreads();
    axios.get(`${API}/v1/models`).then(res => setRegistry(res.data.developers || [])).catch((modelError) => {
      console.error('Failed to load model registry:', modelError);
    });
  }, [fetchThreads]);
  useEffect(() => { if (responseEndRef.current) responseEndRef.current.scrollIntoView({ behavior: 'smooth' }); }, [messages, streaming]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || selectedModels.length === 0 || loading) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    const pmc = {};
    for (const mid of selectedModels) {
      if (perModelCtx[mid] && Object.values(perModelCtx[mid]).some(v => v)) {
        pmc[mid] = perModelCtx[mid];
      }
    }

    if (mode === MODES.NORMAL) {
      sendPrompt(trimmed, selectedModels, { globalContext, perModelContext: Object.keys(pmc).length ? pmc : undefined });
    } else {
      // Advanced modes: shared room, synth room, daisy chain
      const headers = { 'Content-Type': 'application/json' };

      let endpoint, body;
      if (mode === MODES.SHARED_ALL) {
        endpoint = `${API}/v1/a0/shared-room`;
        body = { message: trimmed, models: selectedModels, rounds, mode: 'all', global_context: globalContext || undefined, per_model_context: Object.keys(pmc).length ? pmc : undefined };
      } else if (mode === MODES.SHARED_SYNTH) {
        endpoint = `${API}/v1/a0/shared-room`;
        body = { message: trimmed, models: selectedModels, rounds, mode: 'synthesized', synthesis_model: synthModel || selectedModels[0], global_context: globalContext || undefined, per_model_context: Object.keys(pmc).length ? pmc : undefined };
      } else if (mode === MODES.DAISY) {
        endpoint = `${API}/v1/a0/daisy-chain`;
        body = { message: trimmed, models: selectedModels, rounds, global_context: globalContext || undefined, per_model_context: Object.keys(pmc).length ? pmc : undefined };
      }

      // Show user message + loading state immediately
      addOptimisticMessage({
        message_id: `msg_temp_${Date.now()}`, role: 'user', content: trimmed,
        model: 'user', timestamp: new Date().toISOString(),
      });
      setAdvancedLoading(true);

      try {
        const res = await fetch(endpoint, { method: 'POST', headers, credentials: 'include', body: JSON.stringify(body) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.thread_id) {
          await loadThread(data.thread_id);
          fetchThreads();
        }
      } catch (err) {
        console.error('Advanced mode error:', err);
      } finally {
        setAdvancedLoading(false);
      }
    }
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSend(); } };
  const toggleModel = (modelId) => setSelectedModels(prev => prev.includes(modelId) ? prev.filter(m => m !== modelId) : [...prev, modelId]);
  const handleLogout = async () => { await logout(); navigate('/auth'); };

  const toggleResponseSelect = (msgId) => {
    setSelectedResponseIds(prev => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  };

  const handleSynthesize = async (targetModel, prompt) => {
    if (selectedResponseIds.size === 0 || !targetModel) return;
    setSynthesizing(true);
    try {
      const headers = { 'Content-Type': 'application/json' };
      const res = await fetch(`${API}/v1/a0/synthesize`, {
        method: 'POST', headers, credentials: 'include',
        body: JSON.stringify({
          source_message_ids: [...selectedResponseIds],
          target_models: [targetModel],
          synthesis_prompt: prompt,
          thread_id: currentThread,
        }),
      });
      const data = await res.json();
      if (data.thread_id) {
        loadThread(data.thread_id);
        setSelectedResponseIds(new Set());
      }
    } catch (err) {
      console.error('Synthesis error:', err);
    } finally {
      setSynthesizing(false);
    }
  };

  const getGroups = () => {
    const groups = []; let cur = null;
    for (const msg of messages) {
      if (msg.role === 'user') { if (cur) groups.push(cur); cur = { userMsg: msg, responses: [] }; }
      else if (msg.role === 'assistant' && cur) { cur.responses.push(msg); }
    }
    if (cur) groups.push(cur);
    return groups;
  };

  const streamEntries = Object.entries(streaming);
  const groups = getGroups();
  const showSelect = messages.some(m => m.role === 'assistant');

  const renderResponseGroup = (responses, groupStreaming = []) => {
    if (layout === LAYOUTS.SPLIT) return <SplitLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} locked={splitLocked} selectedIds={selectedResponseIds} onSelect={toggleResponseSelect} showSelect={showSelect} />;
    if (layout === LAYOUTS.CAROUSEL) return <CarouselLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} />;
    return <StackLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} selectedIds={selectedResponseIds} onSelect={toggleResponseSelect} showSelect={showSelect} />;
  };

  const handleTextareaInput = (e) => { setInput(e.target.value); e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'; };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-200" data-testid="chat-page">
      <Sidebar threads={threads} currentThread={currentThread} onSelect={loadThread}
        onNew={() => { newThread(); setSidebarOpen(false); }} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded hover:bg-zinc-800 text-zinc-400" data-testid="sidebar-toggle"><Menu size={20} /></button>
            <h1 className="text-base font-semibold tracking-tight">Multi-Model Hub</h1>
            <span className="text-xs text-zinc-600 hidden sm:inline">v1.0.2-S9</span>
          </div>
          <div className="flex items-center gap-3">
            <LayoutToggle layout={layout} setLayout={setLayout} splitLocked={splitLocked} setSplitLocked={setSplitLocked} />
            <div className="w-px h-5 bg-zinc-800" />
            <button onClick={() => navigate('/analysis')} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="analysis-btn" title="Transcript Analysis"><FileUp size={18} /></button>
            <button onClick={() => navigate('/settings')} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="settings-btn"><Settings size={18} /></button>
            <button onClick={handleLogout} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="logout-btn"><LogOut size={18} /></button>
          </div>
        </header>

        {/* Prompt + Controls */}
        <div className="px-4 py-3 border-b border-zinc-800 space-y-2 bg-zinc-950/60">
          <div className="flex gap-3">
            <div className="flex-1">
              <textarea ref={textareaRef} value={input} onChange={handleTextareaInput} onKeyDown={handleKeyDown}
                placeholder="Enter your prompt... (Ctrl+Enter to send)" rows={2}
                className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 resize-none transition-colors"
                data-testid="prompt-input" />
            </div>
            <button onClick={handleSend} disabled={!input.trim() || selectedModels.length === 0 || loading || advancedLoading}
              className="self-end px-4 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-medium text-sm transition-colors flex items-center gap-2"
              data-testid="send-btn">
              {(loading || advancedLoading) ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>

          {/* Mode + Context toggles */}
          <div className="flex flex-wrap items-center gap-3">
            <ModeSelector mode={mode} setMode={setMode} rounds={rounds} setRounds={setRounds} synthModel={synthModel} setSynthModel={setSynthModel} allModels={allModelIds} />
            <div className="flex items-center gap-1.5 ml-auto">
              <button onClick={() => setShowContext(!showContext)}
                className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${showContext ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30' : 'text-zinc-500 border border-zinc-800 hover:text-zinc-300'}`}
                data-testid="toggle-context-btn"><Sliders size={12} /> Context</button>
              <button onClick={() => setShowModels(!showModels)}
                className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${showModels ? 'bg-zinc-700 text-zinc-200' : 'text-zinc-500 border border-zinc-800 hover:text-zinc-300'}`}
                data-testid="toggle-models-btn">Models ({selectedModels.length})</button>
            </div>
          </div>

          {/* Context Panel */}
          <ContextPanel globalContext={globalContext} setGlobalContext={setGlobalContext} perModelCtx={perModelCtx}
            setPerModelCtx={setPerModelCtx} selectedModels={selectedModels} show={showContext} onToggle={() => setShowContext(!showContext)} />

          {/* Model Selector */}
          {showModels && (
            <div className="max-h-[250px] overflow-y-auto">
              <ModelSelector registry={registry} selected={selectedModels} onToggle={toggleModel} />
            </div>
          )}
        </div>

        {/* Synthesis Bar */}
        {selectedResponseIds.size > 0 && (
          <div className="px-4 py-2 border-b border-zinc-800">
            <SynthesisBar selectedIds={selectedResponseIds} allModels={allModelIds}
              onSynthesize={handleSynthesize} onClear={() => setSelectedResponseIds(new Set())} />
          </div>
        )}

        {/* Responses */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
          {groups.length === 0 && streamEntries.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600 space-y-3">
              <MessageSquare size={48} strokeWidth={1} />
              <p className="text-sm">Select models and send a prompt to begin</p>
            </div>
          )}
          {groups.map((group, gi) => (
            <div key={gi} className="space-y-3">
              <div className="flex justify-end">
                <div className="max-w-[85%] rounded-xl px-4 py-3 bg-emerald-600/20 border border-emerald-600/30 text-zinc-200 text-sm" data-testid={`user-message-${gi}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{group.userMsg.content}</ReactMarkdown>
                </div>
              </div>
              {renderResponseGroup(group.responses, gi === groups.length - 1 ? streamEntries : [])}
            </div>
          ))}
          {groups.length === 0 && streamEntries.length > 0 && renderResponseGroup([], streamEntries)}
          {advancedLoading && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg border border-zinc-800 bg-zinc-900/40" data-testid="advanced-loading">
              <Loader2 size={18} className="animate-spin text-emerald-400" />
              <span className="text-sm text-zinc-400">
                {mode === MODES.DAISY ? 'Running daisy chain...' : mode === MODES.SHARED_SYNTH ? 'Synthesizing in shared room...' : 'Processing shared room...'}
                {rounds > 1 ? ` (${rounds} rounds)` : ''}
              </span>
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg border border-red-600/30 bg-red-950/20 text-sm text-red-400" data-testid="chat-error">
              <X size={14} /> {error}
            </div>
          )}
          <div ref={responseEndRef} />
        </div>
      </div>
    </div>
  );
}
// "lines of code":"256","lines of commented":"3"
