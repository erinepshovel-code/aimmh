import React, { createContext, useContext, useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ChatContext = createContext(null);

export const useChat = () => {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be inside ChatProvider');
  return ctx;
};

export const ChatProvider = ({ children }) => {
  const [threads, setThreads] = useState([]);
  const [currentThread, setCurrentThread] = useState(() => sessionStorage.getItem('hub_thread') || null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState({});
  const [error, setError] = useState(null);
  const [initialized, setInitialized] = useState(false);

  const selectThread = useCallback((threadId) => {
    setCurrentThread(threadId);
    if (threadId) sessionStorage.setItem('hub_thread', threadId);
    else sessionStorage.removeItem('hub_thread');
  }, []);

  const fetchThreads = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/v1/a0/history?limit=50`);
      setThreads(res.data.threads || []);
      return res.data.threads || [];
    } catch (err) {
      console.error('Failed to fetch threads:', err);
      return [];
    }
  }, []);

  const loadThread = useCallback(async (threadId) => {
    try {
      const res = await axios.get(`${API}/v1/a0/thread/${threadId}`);
      selectThread(threadId);
      setMessages(res.data || []);
    } catch (err) {
      console.error('Failed to load thread:', err);
    }
  }, [selectThread]);

  // ---- Fallback: non-streaming collected response ----
  const sendPromptCollected = useCallback(async (message, models, options = {}) => {
    const token = localStorage.getItem('token');
    const body = {
      message,
      models,
      thread_id: currentThread || undefined,
      global_context: options.globalContext || undefined,
      per_model_context: options.perModelContext || undefined,
    };

    const res = await fetch(`${API}/v1/a0/prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }, [currentThread]);

  const sendPrompt = useCallback(async (message, models, options = {}) => {
    setLoading(true);
    setStreaming({});
    setError(null);

    // Add user message optimistically
    const userMsgId = `msg_temp_${Date.now()}`;
    setMessages(prev => [...prev, {
      message_id: userMsgId, role: 'user', content: message,
      model: 'user', timestamp: new Date().toISOString(),
    }]);

    try {
      // Try SSE streaming first
      const token = localStorage.getItem('token');
      const body = {
        message, models,
        thread_id: currentThread || undefined,
        global_context: options.globalContext || undefined,
        per_model_context: options.perModelContext || undefined,
      };

      const response = await fetch(`${API}/v1/a0/prompt/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`SSE_FAIL_${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const newResponses = {};
      let threadId = currentThread;
      let gotAnyData = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) continue;
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));
            gotAnyData = true;

            if (data.thread_id && !threadId) {
              threadId = data.thread_id;
              selectThread(threadId);
            }

            if (data.message_id && data.model) {
              if (data.content !== undefined) {
                // Chunk
                if (!newResponses[data.model]) {
                  newResponses[data.model] = { content: '', message_id: data.message_id };
                }
                newResponses[data.model].content += data.content;
                setStreaming(prev => ({
                  ...prev,
                  [data.model]: {
                    message_id: data.message_id,
                    content: newResponses[data.model].content,
                  },
                }));
              } else if (data.response_time_ms !== undefined) {
                // Complete
                const finalContent = newResponses[data.model]?.content || '';
                setMessages(prev => [...prev, {
                  message_id: data.message_id, thread_id: threadId,
                  role: 'assistant', content: finalContent, model: data.model,
                  timestamp: new Date().toISOString(), response_time_ms: data.response_time_ms,
                }]);
                setStreaming(prev => {
                  const next = { ...prev };
                  delete next[data.model];
                  return next;
                });
              }
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }

      // If SSE connected but no data arrived, fall back to collected
      if (!gotAnyData) {
        throw new Error('SSE_EMPTY');
      }

      fetchThreads();
    } catch (err) {
      console.warn('SSE failed, falling back to collected endpoint:', err.message);
      setStreaming({});

      // Show loading indicator for each model
      const tempStreaming = {};
      for (const m of models) {
        tempStreaming[m] = { message_id: null, content: '' };
      }
      setStreaming(tempStreaming);

      try {
        // Fallback to collected (non-streaming) endpoint
        const data = await sendPromptCollected(message, models, options);

        if (data.thread_id) selectThread(data.thread_id);

        // Add all responses at once
        for (const resp of (data.responses || [])) {
          setMessages(prev => [...prev, {
            message_id: resp.message_id, thread_id: data.thread_id,
            role: 'assistant', content: resp.content, model: resp.model,
            timestamp: new Date().toISOString(), response_time_ms: resp.response_time_ms,
          }]);
        }
        fetchThreads();
      } catch (fallbackErr) {
        console.error('Collected endpoint also failed:', fallbackErr);
        setError(`Failed to get responses: ${fallbackErr.message}`);
      }
    } finally {
      setLoading(false);
      setStreaming({});
    }
  }, [currentThread, fetchThreads, selectThread, sendPromptCollected]);

  const newThread = useCallback(() => {
    selectThread(null);
    setMessages([]);
    setStreaming({});
    setError(null);
  }, [selectThread]);

  const submitFeedback = useCallback(async (messageId, feedback) => {
    try {
      await axios.post(`${API}/v1/a0/feedback`, { message_id: messageId, feedback });
      setMessages(prev => prev.map(m =>
        m.message_id === messageId ? { ...m, feedback } : m
      ));
    } catch (err) {
      console.error('Feedback error:', err);
    }
  }, []);

  // Restore state on mount and on window focus
  const restoreState = useCallback(async () => {
    const savedThread = sessionStorage.getItem('hub_thread');
    if (savedThread && messages.length === 0) {
      try {
        const res = await axios.get(`${API}/v1/a0/thread/${savedThread}`);
        if (res.data && res.data.length > 0) {
          setMessages(res.data);
        }
      } catch {
        sessionStorage.removeItem('hub_thread');
        setCurrentThread(null);
      }
    }
  }, [messages.length]);

  React.useEffect(() => {
    if (!initialized) {
      setInitialized(true);
      fetchThreads();
      restoreState();
    }

    const handleFocus = () => {
      fetchThreads();
      const saved = sessionStorage.getItem('hub_thread');
      if (saved) {
        axios.get(`${API}/v1/a0/thread/${saved}`).then(res => {
          if (res.data) setMessages(res.data);
        }).catch(() => {});
      }
    };

    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [initialized, fetchThreads, restoreState]);

  return (
    <ChatContext.Provider value={{
      threads, currentThread, messages, loading, streaming, error,
      fetchThreads, loadThread, sendPrompt, newThread, submitFeedback,
      setCurrentThread: selectThread,
    }}>
      {children}
    </ChatContext.Provider>
  );
};
