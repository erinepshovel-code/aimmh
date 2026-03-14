import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useChat } from '../contexts/ChatContext';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Plus, Settings, LogOut, ChevronDown, ChevronRight,
  ThumbsUp, ThumbsDown, Copy, Clock, Menu, X, LayoutGrid, List,
  MessageSquare, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ---- Model Selector with Developer Tabs ----
function ModelSelector({ registry, selected, onToggle }) {
  const [expandedDev, setExpandedDev] = useState({});

  if (!registry.length) return null;

  const toggleDev = (devId) => {
    setExpandedDev(prev => ({ ...prev, [devId]: !prev[devId] }));
  };

  return (
    <div className="space-y-1" data-testid="model-selector">
      {registry.map(dev => (
        <div key={dev.developer_id} className="rounded-md border border-zinc-800 overflow-hidden">
          <button
            onClick={() => toggleDev(dev.developer_id)}
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
                <label
                  key={m.model_id}
                  className="flex items-center gap-2 py-1 px-2 rounded cursor-pointer hover:bg-zinc-800/40 text-sm"
                  data-testid={`model-checkbox-${m.model_id}`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(m.model_id)}
                    onChange={() => onToggle(m.model_id)}
                    className="rounded border-zinc-600 bg-zinc-800 text-emerald-500 focus:ring-emerald-500/30"
                  />
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
function ResponsePanel({ model, content, messageId, responseTime, feedback, onFeedback, isStreaming }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      className="rounded-lg border border-zinc-800 bg-zinc-900/60 overflow-hidden"
      data-testid={`response-panel-${model}`}
    >
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900/80">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-emerald-400" data-testid={`response-model-${model}`}>{model}</span>
          {isStreaming && <Loader2 size={14} className="animate-spin text-emerald-400" />}
          {responseTime && !isStreaming && (
            <span className="flex items-center gap-1 text-xs text-zinc-500">
              <Clock size={10} /> {(responseTime / 1000).toFixed(1)}s
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-zinc-700/60 text-zinc-400 hover:text-zinc-200 transition-colors"
            data-testid={`copy-btn-${model}`}
            title="Copy"
          >
            <Copy size={14} />
          </button>
          {messageId && (
            <>
              <button
                onClick={() => onFeedback(messageId, 'up')}
                className={`p-1.5 rounded hover:bg-zinc-700/60 transition-colors ${feedback === 'up' ? 'text-emerald-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                data-testid={`thumbsup-btn-${model}`}
              >
                <ThumbsUp size={14} />
              </button>
              <button
                onClick={() => onFeedback(messageId, 'down')}
                className={`p-1.5 rounded hover:bg-zinc-700/60 transition-colors ${feedback === 'down' ? 'text-red-400' : 'text-zinc-400 hover:text-zinc-200'}`}
                data-testid={`thumbsdown-btn-${model}`}
              >
                <ThumbsDown size={14} />
              </button>
            </>
          )}
        </div>
      </div>
      <div className="p-4 prose prose-invert prose-sm max-w-none min-h-[120px] max-h-[600px] overflow-y-auto">
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

// ---- Sidebar ----
function Sidebar({ threads, currentThread, onSelect, onNew, open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 bg-black/50 z-30 lg:hidden" onClick={onClose} />}
      <div className={`fixed top-0 left-0 h-full w-72 bg-zinc-950 border-r border-zinc-800 z-40 transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 lg:relative lg:z-0`}>
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <span className="text-sm font-semibold text-zinc-200">Threads</span>
          <button
            onClick={onNew}
            className="p-1.5 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
            data-testid="new-thread-btn"
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="overflow-y-auto h-[calc(100%-60px)] p-2 space-y-1">
          {threads.map(t => (
            <button
              key={t.thread_id}
              onClick={() => { onSelect(t.thread_id); onClose(); }}
              className={`w-full text-left px-3 py-2 rounded-md text-sm truncate transition-colors ${
                currentThread === t.thread_id
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
              }`}
              data-testid={`thread-item-${t.thread_id}`}
            >
              <div className="flex items-center gap-2">
                <MessageSquare size={14} className="flex-shrink-0" />
                <span className="truncate">{t.title || 'Untitled'}</span>
              </div>
              <div className="text-xs text-zinc-600 mt-0.5">{t.models_used?.join(', ') || ''}</div>
            </button>
          ))}
          {threads.length === 0 && (
            <div className="text-center text-xs text-zinc-600 py-8">No threads yet</div>
          )}
        </div>
      </div>
    </>
  );
}

// ---- Main ChatPage ----
export default function ChatPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const {
    threads, currentThread, messages, loading, streaming,
    fetchThreads, loadThread, sendPrompt, newThread, submitFeedback,
  } = useChat();

  const [input, setInput] = useState('');
  const [registry, setRegistry] = useState([]);
  const [selectedModels, setSelectedModels] = useState(['gpt-4o-mini']);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showModels, setShowModels] = useState(true);
  const responseEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    fetchThreads();
    axios.get(`${API}/v1/models`).then(res => {
      setRegistry(res.data.developers || []);
    }).catch(() => {});
  }, [fetchThreads]);

  useEffect(() => {
    if (responseEndRef.current) {
      responseEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streaming]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || selectedModels.length === 0 || loading) return;
    setInput('');
    sendPrompt(trimmed, selectedModels);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleModel = (modelId) => {
    setSelectedModels(prev =>
      prev.includes(modelId) ? prev.filter(m => m !== modelId) : [...prev, modelId]
    );
  };

  const handleLogout = async () => {
    await logout();
    navigate('/auth');
  };

  // Group assistant messages by their source prompt (by clustering around user messages)
  const renderConversation = () => {
    const groups = [];
    let currentGroup = null;

    for (const msg of messages) {
      if (msg.role === 'user') {
        if (currentGroup) groups.push(currentGroup);
        currentGroup = { userMsg: msg, responses: [] };
      } else if (msg.role === 'assistant' && currentGroup) {
        currentGroup.responses.push(msg);
      }
    }
    if (currentGroup) groups.push(currentGroup);

    return groups.map((group, gi) => (
      <div key={gi} className="space-y-3">
        {/* User message */}
        <div className="flex justify-end">
          <div
            className="max-w-[85%] rounded-xl px-4 py-3 bg-emerald-600/20 border border-emerald-600/30 text-zinc-200 text-sm"
            data-testid={`user-message-${gi}`}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{group.userMsg.content}</ReactMarkdown>
          </div>
        </div>
        {/* Model responses - vertical stack */}
        <div className="space-y-3">
          {group.responses.map(resp => (
            <ResponsePanel
              key={resp.message_id}
              model={resp.model}
              content={resp.content}
              messageId={resp.message_id}
              responseTime={resp.response_time_ms}
              feedback={resp.feedback}
              onFeedback={submitFeedback}
              isStreaming={false}
            />
          ))}
        </div>
      </div>
    ));
  };

  // Streaming responses (currently being generated)
  const renderStreaming = () => {
    const streamEntries = Object.entries(streaming);
    if (streamEntries.length === 0) return null;

    return (
      <div className="space-y-3">
        {streamEntries.map(([model, data]) => (
          <ResponsePanel
            key={`streaming-${model}`}
            model={model}
            content={data.content}
            messageId={null}
            responseTime={null}
            feedback={null}
            onFeedback={() => {}}
            isStreaming={true}
          />
        ))}
      </div>
    );
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-200" data-testid="chat-page">
      {/* Sidebar */}
      <Sidebar
        threads={threads}
        currentThread={currentThread}
        onSelect={loadThread}
        onNew={() => { newThread(); setSidebarOpen(false); }}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded hover:bg-zinc-800 text-zinc-400"
              data-testid="sidebar-toggle"
            >
              <Menu size={20} />
            </button>
            <h1 className="text-base font-semibold tracking-tight">Multi-Model Hub</h1>
            <span className="text-xs text-zinc-600 hidden sm:inline">v1.0.2-S9</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/settings')}
              className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
              data-testid="settings-btn"
            >
              <Settings size={18} />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
              data-testid="logout-btn"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Prompt Input Area */}
        <div className="px-4 py-4 border-b border-zinc-800 space-y-3 bg-zinc-950/60">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Enter your prompt... (Ctrl+Enter to send)"
                rows={2}
                className="w-full rounded-lg bg-zinc-900 border border-zinc-700 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 resize-none transition-colors"
                data-testid="prompt-input"
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || selectedModels.length === 0 || loading}
              className="self-end px-4 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-medium text-sm transition-colors flex items-center gap-2"
              data-testid="send-btn"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>

          {/* Model Selection Toggle */}
          <div>
            <button
              onClick={() => setShowModels(!showModels)}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200"
              data-testid="toggle-models-btn"
            >
              {showModels ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              Models ({selectedModels.length} selected)
            </button>
            {showModels && (
              <div className="mt-2 max-h-[300px] overflow-y-auto">
                <ModelSelector
                  registry={registry}
                  selected={selectedModels}
                  onToggle={toggleModel}
                />
              </div>
            )}
          </div>
        </div>

        {/* Responses Area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
          {messages.length === 0 && Object.keys(streaming).length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-zinc-600 space-y-3">
              <MessageSquare size={48} strokeWidth={1} />
              <p className="text-sm">Select models and send a prompt to begin</p>
            </div>
          )}
          {renderConversation()}
          {renderStreaming()}
          <div ref={responseEndRef} />
        </div>
      </div>
    </div>
  );
}
