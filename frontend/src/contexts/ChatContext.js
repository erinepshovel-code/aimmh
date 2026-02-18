import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const ChatContext = createContext(null);
const STORAGE_KEY = 'multi_ai_hub_chat';

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error('useChat must be used within ChatProvider');
  return context;
};

function loadFromStorage() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const ChatProvider = ({ children }) => {
  const saved = loadFromStorage();

  const [selectedModels, setSelectedModels] = useState(saved?.selectedModels || ['gpt-5.2', 'claude-sonnet-4-5-20250929', 'gemini-3-flash-preview']);
  const [visibleModelIndex, setVisibleModelIndex] = useState(saved?.visibleModelIndex || 0);
  const [input, setInput] = useState(saved?.input || '');
  const [messages, setMessages] = useState(saved?.messages || []);
  const [conversationId, setConversationId] = useState(saved?.conversationId || null);
  const [streaming, setStreaming] = useState(false);
  const [selectedMessages, setSelectedMessages] = useState(saved?.selectedMessages || []);
  const [pausedModels, setPausedModels] = useState(saved?.pausedModels || {});
  const [promptHistory, setPromptHistory] = useState(saved?.promptHistory || []);
  const [messageIndexMap, setMessageIndexMap] = useState(saved?.messageIndexMap || {});
  const [nextIndex, setNextIndex] = useState(saved?.nextIndex || 1);
  const [globalContext, setGlobalContext] = useState(saved?.globalContext || '');
  const [autoExport, setAutoExport] = useState(saved?.autoExport || false);
  const [modelRoles, setModelRoles] = useState(saved?.modelRoles || {});

  // Persist to sessionStorage on state changes
  useEffect(() => {
    const data = {
      selectedModels, visibleModelIndex, input, messages,
      conversationId, selectedMessages, pausedModels,
      promptHistory, messageIndexMap, nextIndex,
      globalContext, autoExport, modelRoles,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [selectedModels, visibleModelIndex, input, messages, conversationId,
      selectedMessages, pausedModels, promptHistory, messageIndexMap,
      nextIndex, globalContext, autoExport, modelRoles]);

  const resetChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setPromptHistory([]);
    setSelectedMessages([]);
    setMessageIndexMap({});
    setNextIndex(1);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <ChatContext.Provider value={{
      selectedModels, setSelectedModels,
      visibleModelIndex, setVisibleModelIndex,
      input, setInput,
      messages, setMessages,
      conversationId, setConversationId,
      streaming, setStreaming,
      selectedMessages, setSelectedMessages,
      pausedModels, setPausedModels,
      promptHistory, setPromptHistory,
      messageIndexMap, setMessageIndexMap,
      nextIndex, setNextIndex,
      globalContext, setGlobalContext,
      autoExport, setAutoExport,
      modelRoles, setModelRoles,
      resetChat,
    }}>
      {children}
    </ChatContext.Provider>
  );
};
