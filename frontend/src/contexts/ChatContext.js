import React, { createContext, useContext, useState } from 'react';

const ChatContext = createContext(null);

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error('useChat must be used within ChatProvider');
  return context;
};

export const ChatProvider = ({ children }) => {
  const [selectedModels, setSelectedModels] = useState(['gpt-5.2', 'claude-sonnet-4-5-20250929', 'gemini-3-flash-preview']);
  const [visibleModelIndex, setVisibleModelIndex] = useState(0);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [selectedMessages, setSelectedMessages] = useState([]);
  const [pausedModels, setPausedModels] = useState({});
  const [promptHistory, setPromptHistory] = useState([]);
  const [messageIndexMap, setMessageIndexMap] = useState({});
  const [nextIndex, setNextIndex] = useState(1);
  const [globalContext, setGlobalContext] = useState('');
  const [autoExport, setAutoExport] = useState(false);
  const [modelRoles, setModelRoles] = useState({});

  const resetChat = () => {
    setMessages([]);
    setConversationId(null);
    setPromptHistory([]);
    setSelectedMessages([]);
    setMessageIndexMap({});
    setNextIndex(1);
  };

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
