import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import useEmblaCarousel from 'embla-carousel-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Plus, Settings, LogOut, ChevronDown, ChevronRight,
  ThumbsUp, ThumbsDown, Copy, Clock, Menu,
  MessageSquare, Loader2, Columns2, Layers, GalleryHorizontal,
  Lock, ChevronLeft, FileUp
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LAYOUTS = { STACK: 'stack', SPLIT: 'split', CAROUSEL: 'carousel' };

// ---- Model Selector with Developer Tabs ----
function ModelSelector({ registry, selected, onToggle }) {
  const [expandedDev, setExpandedDev] = useState({});
  if (!registry.length) return null;

  return (
    <div className="space-y-1" data-testid="model-selector">
      {registry.map(dev => (
        <div key={dev.developer_id} className="rounded-md border border-zinc-800 overflow-hidden">
          <button
            onClick={() => setExpandedDev(p => ({ ...p, [dev.developer_id]: !p[dev.developer_id] }))}
            className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800/60 transition-colors"
            data-testid={`dev-tab-${dev.developer_id}`}
          >
            <span>{dev.name}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">
                {dev.models.filter(m => selected.includes(m.model_id)).length}/{dev.models.length}
              </span>
              {expandedDev[dev.developer_id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
          </button>
          {expandedDev[dev.developer_id] && (
            <div className="px-3 pb-2 space-y-1 bg-zinc-900/40">
              {dev.models.map(m => (
                <label key={m.model_id} className="flex items-center gap-2 py-1 px-2 rounded cursor-pointer hover:bg-zinc-800/40 text-sm" data-testid={`model-checkbox-${m.model_id}`}>
                  <input type="checkbox" checked={selected.includes(m.model_id)} onChange={() => onToggle(m.model_id)}
                    className="rounded border-zinc-600 bg-zinc-800 text-emerald-500 focus:ring-emerald-500/30" />
                  <span className="text-zinc-300">{m.display_name || m.model_id}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---- Response Panel ----
function ResponsePanel({ model, content, messageId, responseTime, feedback, onFeedback, isStreaming, compact }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => { navigator.clipboard.writeText(content); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  return (
    <div className={`rounded-lg border border-zinc-800 bg-zinc-900/60 overflow-hidden flex flex-col ${compact ? 'h-full' : ''}`} data-testid={`response-panel-${model}`}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900/80 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-emerald-400" data-testid={`response-model-${model}`}>{model}</span>
          {isStreaming && <Loader2 size={14} className="animate-spin text-emerald-400" />}
          {responseTime && !isStreaming && (
            <span className="flex items-center gap-1 text-xs text-zinc-500"><Clock size={10} /> {(responseTime / 1000).toFixed(1)}s</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleCopy} className="p-1.5 rounded hover:bg-zinc-700/60 text-zinc-400 hover:text-zinc-200 transition-colors" data-testid={`copy-btn-${model}`} title={copied ? 'Copied!' : 'Copy'}>
            <Copy size={14} />
          </button>
          {messageId && (
            <>
              <button onClick={() => onFeedback(messageId, 'up')} className={`p-1.5 rounded hover:bg-zinc-700/60 transition-colors ${feedback === 'up' ? 'text-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`} data-testid={`thumbsup-btn-${model}`}>
                <ThumbsUp size={14} />
              </button>
              <button onClick={() => onFeedback(messageId, 'down')} className={`p-1.5 rounded hover:bg-zinc-700/60 transition-colors ${feedback === 'down' ? 'text-red-400' : 'text-zinc-400 hover:text-zinc-200'}`} data-testid={`thumbsdown-btn-${model}`}>
                <ThumbsDown size={14} />
              </button>
            </>
          )}
        </div>
      </div>
      <div className={`p-4 prose prose-invert prose-sm max-w-none overflow-y-auto flex-1 ${compact ? '' : 'min-h-[120px] max-h-[600px]'}`}>
        {content ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        ) : isStreaming ? (
          <span className="text-zinc-500 animate-pulse">Thinking...</span>
        ) : (
          <span className="text-zinc-600">No response</span>
        )}
      </div>
    </div>
  );
}

// ---- Response Layouts ----

function StackLayout({ responses, onFeedback, streamEntries }) {
  return (
    <div className="space-y-3">
      {responses.map(r => (
        <ResponsePanel key={r.message_id} model={r.model} content={r.content} messageId={r.message_id}
          responseTime={r.response_time_ms} feedback={r.feedback} onFeedback={onFeedback} isStreaming={false} />
      ))}
      {streamEntries.map(([model, data]) => (
        <ResponsePanel key={`s-${model}`} model={model} content={data.content} messageId={null}
          responseTime={null} feedback={null} onFeedback={() => {}} isStreaming={true} />
      ))}
    </div>
  );
}

function SplitLayout({ responses, onFeedback, streamEntries, locked }) {
  const all = [
    ...responses.map(r => ({ ...r, isStreaming: false })),
    ...streamEntries.map(([model, data]) => ({ model, content: data.content, message_id: null, response_time_ms: null, feedback: null, isStreaming: true })),
  ];
  if (all.length === 0) return null;
  if (all.length === 1) {
    const r = all[0];
    return <ResponsePanel model={r.model} content={r.content} messageId={r.message_id} responseTime={r.response_time_ms} feedback={r.feedback} onFeedback={onFeedback} isStreaming={r.isStreaming} />;
  }

  return (
    <div className="h-[500px]">
      <PanelGroup direction="horizontal" data-testid="split-panel-group">
        {all.map((r, i) => (
          <React.Fragment key={r.message_id || `s-${r.model}`}>
            {i > 0 && (
              <PanelResizeHandle className="w-2 bg-zinc-800 hover:bg-emerald-600/40 transition-colors rounded mx-0.5 cursor-col-resize" data-testid="panel-resize-handle" />
            )}
            <Panel defaultSize={locked ? (100 / all.length) : undefined} minSize={15}>
              <ResponsePanel model={r.model} content={r.content} messageId={r.message_id}
                responseTime={r.response_time_ms} feedback={r.feedback} onFeedback={onFeedback}
                isStreaming={r.isStreaming} compact={true} />
            </Panel>
          </React.Fragment>
        ))}
      </PanelGroup>
    </div>
  );
}

function CarouselLayout({ responses, onFeedback, streamEntries }) {
  const all = [
    ...responses.map(r => ({ ...r, isStreaming: false })),
    ...streamEntries.map(([model, data]) => ({ model, content: data.content, message_id: null, response_time_ms: null, feedback: null, isStreaming: true })),
  ];
  const [emblaRef, emblaApi] = useEmblaCarousel({ loop: true, align: 'center' });
  const [selectedIdx, setSelectedIdx] = useState(0);

  const onSelect = useCallback(() => {
    if (!emblaApi) return;
    setSelectedIdx(emblaApi.selectedScrollSnap());
  }, [emblaApi]);

  useEffect(() => {
    if (!emblaApi) return;
    emblaApi.on('select', onSelect);
    onSelect();
    return () => { emblaApi.off('select', onSelect); };
  }, [emblaApi, onSelect]);

  if (all.length === 0) return null;
  if (all.length === 1) {
    const r = all[0];
    return <ResponsePanel model={r.model} content={r.content} messageId={r.message_id} responseTime={r.response_time_ms} feedback={r.feedback} onFeedback={onFeedback} isStreaming={r.isStreaming} />;
  }

  return (
    <div data-testid="carousel-layout">
      {/* Dot indicators + nav */}
      <div className="flex items-center justify-between mb-2">
        <button onClick={() => emblaApi?.scrollPrev()} className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="carousel-prev">
          <ChevronLeft size={16} />
        </button>
        <div className="flex gap-1.5">
          {all.map((r, i) => (
            <button key={i} onClick={() => emblaApi?.scrollTo(i)}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${i === selectedIdx ? 'bg-emerald-600/30 text-emerald-400 border border-emerald-600/40' : 'text-zinc-500 hover:text-zinc-300 border border-zinc-800'}`}
              data-testid={`carousel-dot-${i}`}
            >
              {r.model}
            </button>
          ))}
        </div>
        <button onClick={() => emblaApi?.scrollNext()} className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="carousel-next">
          <ChevronRight size={16} />
        </button>
      </div>
      {/* Carousel viewport */}
      <div className="overflow-hidden rounded-lg" ref={emblaRef}>
        <div className="flex">
          {all.map((r, i) => (
            <div key={r.message_id || `s-${r.model}`} className="flex-[0_0_100%] min-w-0 px-1">
              <ResponsePanel model={r.model} content={r.content} messageId={r.message_id}
                responseTime={r.response_time_ms} feedback={r.feedback} onFeedback={onFeedback}
                isStreaming={r.isStreaming} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---- Sidebar ----
function Sidebar({ threads, currentThread, onSelect, onNew, open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={onClose} />}
      <div className={`fixed top-0 left-0 h-full w-72 bg-zinc-950 border-r border-zinc-800 z-40 transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:relative lg:z-0`}>
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <span className="text-sm font-semibold text-zinc-200">Threads</span>
          <button onClick={onNew} className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="new-thread-btn">
            <Plus size={16} />
          </button>
        </div>
        <div className="overflow-y-auto h-[calc(100%-60px)] p-2 space-y-1">
          {threads.map(t => (
            <button key={t.thread_id} onClick={() => { onSelect(t.thread_id); onClose(); }}
              className={`w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors ${currentThread === t.thread_id ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'}`}
              data-testid={`thread-item-${t.thread_id}`}>
              <div className="flex items-center gap-2">
                <MessageSquare size={14} className="flex-shrink-0" />
                <span className="truncate">{t.title || 'Untitled'}</span>
              </div>
              <div className="text-xs text-zinc-600 mt-0.5">{t.models_used?.join(', ') || ''}</div>
            </button>
          ))}
          {threads.length === 0 && <div className="text-center text-xs text-zinc-600 py-8">No threads yet</div>}
        </div>
      </div>
    </>
  );
}

// ---- Layout Toggle ----
function LayoutToggle({ layout, setLayout, splitLocked, setSplitLocked }) {
  return (
    <div className="flex items-center gap-1" data-testid="layout-toggle">
      <button onClick={() => setLayout(LAYOUTS.STACK)} title="Vertical Stack"
        className={`p-1.5 rounded transition-colors ${layout === LAYOUTS.STACK ? 'bg-zinc-700 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}
        data-testid="layout-stack-btn">
        <Layers size={16} />
      </button>
      <button onClick={() => setLayout(LAYOUTS.SPLIT)} title="Side-by-Side Split"
        className={`p-1.5 rounded transition-colors ${layout === LAYOUTS.SPLIT ? 'bg-zinc-700 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}
        data-testid="layout-split-btn">
        <Columns2 size={16} />
      </button>
      <button onClick={() => setLayout(LAYOUTS.CAROUSEL)} title="Carousel"
        className={`p-1.5 rounded transition-colors ${layout === LAYOUTS.CAROUSEL ? 'bg-zinc-700 text-emerald-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}
        data-testid="layout-carousel-btn">
        <GalleryHorizontal size={16} />
      </button>
      {layout === LAYOUTS.SPLIT && (
        <button onClick={() => setSplitLocked(l => !l)} title={splitLocked ? 'Unlock panels' : 'Lock 50/50'}
          className={`p-1.5 rounded transition-colors ${splitLocked ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/30' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'}`}
          data-testid="split-lock-btn">
          <Lock size={14} />
        </button>
      )}
    </div>
  );
}

// ---- Main ChatPage ----
export default function ChatPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { threads, currentThread, messages, loading, streaming, fetchThreads, loadThread, sendPrompt, newThread, submitFeedback } = useChat();

  const [input, setInput] = useState('');
  const [registry, setRegistry] = useState([]);
  const [selectedModels, setSelectedModels] = useState(['gpt-4o-mini']);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showModels, setShowModels] = useState(true);
  const [layout, setLayout] = useState(() => localStorage.getItem('hub_layout') || LAYOUTS.STACK);
  const [splitLocked, setSplitLocked] = useState(false);
  const responseEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Persist layout preference
  useEffect(() => { localStorage.setItem('hub_layout', layout); }, [layout]);

  useEffect(() => {
    fetchThreads();
    axios.get(`${API}/v1/models`).then(res => setRegistry(res.data.developers || [])).catch(() => {});
  }, [fetchThreads]);

  useEffect(() => {
    if (responseEndRef.current) responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streaming]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || selectedModels.length === 0 || loading) return;
    setInput('');
    sendPrompt(trimmed, selectedModels);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleSend(); }
  };

  const toggleModel = (modelId) => {
    setSelectedModels(prev => prev.includes(modelId) ? prev.filter(m => m !== modelId) : [...prev, modelId]);
  };

  const handleLogout = async () => { await logout(); navigate('/auth'); };

  // Group messages into prompt→response groups
  const getGroups = () => {
    const groups = [];
    let cur = null;
    for (const msg of messages) {
      if (msg.role === 'user') {
        if (cur) groups.push(cur);
        cur = { userMsg: msg, responses: [] };
      } else if (msg.role === 'assistant' && cur) {
        cur.responses.push(msg);
      }
    }
    if (cur) groups.push(cur);
    return groups;
  };

  const streamEntries = Object.entries(streaming);
  const groups = getGroups();

  const renderResponseGroup = (responses, groupStreaming = []) => {
    if (layout === LAYOUTS.SPLIT) return <SplitLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} locked={splitLocked} />;
    if (layout === LAYOUTS.CAROUSEL) return <CarouselLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} />;
    return <StackLayout responses={responses} onFeedback={submitFeedback} streamEntries={groupStreaming} />;
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-200" data-testid="chat-page">
      <Sidebar threads={threads} currentThread={currentThread} onSelect={loadThread}
        onNew={() => { newThread(); setSidebarOpen(false); }} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded hover:bg-zinc-800 text-zinc-400" data-testid="sidebar-toggle">
              <Menu size={20} />
            </button>
            <h1 className="text-base font-semibold tracking-tight">Multi-Model Hub</h1>
            <span className="text-xs text-zinc-600 hidden sm:inline">v1.0.2-S9</span>
          </div>
          <div className="flex items-center gap-3">
            <LayoutToggle layout={layout} setLayout={setLayout} splitLocked={splitLocked} setSplitLocked={setSplitLocked} />
            <div className="w-px h-5 bg-zinc-800" />
            <button onClick={() => navigate('/analysis')} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="analysis-btn" title="Transcript Analysis">
              <FileUp size={18} />
            </button>
            <button onClick={() => navigate('/settings')} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="settings-btn">
              <Settings size={18} />
            </button>
            <button onClick={handleLogout} className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200" data-testid="logout-btn">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Prompt Input */}
        <div className="px-4 py-4 border-b border-zinc-800 space-y-3 bg-zinc-950/60">
          <div className="flex gap-3">
            <div className="flex-1">
              <textarea ref={textareaRef} value={input} onChange={handleTextareaInput} onKeyDown={handleKeyDown}
                placeholder="Enter your prompt... (Ctrl+Enter to send)" rows={2}
                className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 resize-none transition-colors"
                data-testid="prompt-input" />
            </div>
            <button onClick={handleSend} disabled={!input.trim() || selectedModels.length === 0 || loading}
              className="self-end px-4 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-medium text-sm transition-colors flex items-center gap-2"
              data-testid="send-btn">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
          <div>
            <button onClick={() => setShowModels(!showModels)} className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200" data-testid="toggle-models-btn">
              {showModels ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              Models ({selectedModels.length} selected)
            </button>
            {showModels && (
              <div className="mt-2 max-h-[300px] overflow-y-auto">
                <ModelSelector registry={registry} selected={selectedModels} onToggle={toggleModel} />
              </div>
            )}
          </div>
        </div>

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
          <div ref={responseEndRef} />
        </div>
      </div>
    </div>
  );
}
