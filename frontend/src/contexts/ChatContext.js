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
  const [currentThread, setCurrentThread] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState({});

  const fetchThreads = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/v1/a0/history?limit=50`);
      setThreads(res.data.threads || []);
    } catch (err) {
      console.error('Failed to fetch threads:', err);
    }
  }, []);

  const loadThread = useCallback(async (threadId) => {
    try {
      const res = await axios.get(`${API}/v1/a0/thread/${threadId}`);
      setCurrentThread(threadId);
      setMessages(res.data || []);
    } catch (err) {
      console.error('Failed to load thread:', err);
    }
  }, []);

  const sendPrompt = useCallback(async (message, models, options = {}) => {
    setLoading(true);
    setStreaming({});

    try {
      // Use SSE streaming endpoint for real-time display
      const token = localStorage.getItem('token');
      const body = {
        message,
        models,
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
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const newResponses = {};
      let threadId = currentThread;

      // Add user message optimistically
      const userMsgId = `msg_temp_${Date.now()}`;
      setMessages(prev => [...prev, {
        message_id: userMsgId,
        role: 'user',
        content: message,
        model: 'user',
        timestamp: new Date().toISOString(),
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim();
            continue;
          }
          if (!line.startsWith('data: ')) continue;

          try {
            const data = JSON.parse(line.slice(6));

            if (data.thread_id && !threadId) {
              threadId = data.thread_id;
              setCurrentThread(threadId);
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
                  message_id: data.message_id,
                  thread_id: threadId,
                  role: 'assistant',
                  content: finalContent,
                  model: data.model,
                  timestamp: new Date().toISOString(),
                  response_time_ms: data.response_time_ms,
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

      // Refresh threads list
      fetchThreads();
    } catch (err) {
      console.error('Prompt error:', err);
    } finally {
      setLoading(false);
      setStreaming({});
    }
  }, [currentThread, fetchThreads]);

  const newThread = useCallback(() => {
    setCurrentThread(null);
    setMessages([]);
    setStreaming({});
  }, []);

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

  return (
    <ChatContext.Provider value={{
      threads, currentThread, messages, loading, streaming,
      fetchThreads, loadThread, sendPrompt, newThread, submitFeedback,
      setCurrentThread,
    }}>
      {children}
    </ChatContext.Provider>
  );
};
