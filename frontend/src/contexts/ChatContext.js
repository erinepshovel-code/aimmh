import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

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

function buildDefaultCascadeConfig(selectedModels, savedConfig) {
  const defaults = {
    rounds: 3,
    defaultTurnsPerModelPerRound: 1,
    randomOrderPerRound: false,
    // Global prompt toggles (cascade-only)
    globalContextEnabled: false,
    globalContextText: '',
    roleplayEnabled: false,
    roleplayText: '',
    // Seed
    seedMode: 'last_user', // last_user | custom
    seedCustomText: '',
    // Turn order per round
    order: selectedModels,
    // Per-model settings
    modelSettings: {},
  };

  const config = { ...defaults, ...(savedConfig || {}) };

  // Ensure order is valid
  const baseOrder = Array.isArray(config.order) ? config.order : [];
  const order = [
    ...baseOrder.filter(m => selectedModels.includes(m)),
    ...selectedModels.filter(m => !baseOrder.includes(m)),
  ];

  const modelSettings = { ...(config.modelSettings || {}) };
  for (const model of selectedModels) {
    modelSettings[model] = {
      included: modelSettings[model]?.included ?? true,
      turnsPerRound: modelSettings[model]?.turnsPerRound ?? null,
      promptModifier: modelSettings[model]?.promptModifier ?? '',
      role: modelSettings[model]?.role ?? 'none',
      customRoleText: modelSettings[model]?.customRoleText ?? '',
      verbosity: modelSettings[model]?.verbosity ?? 5,
      alignment: modelSettings[model]?.alignment ?? 'true_neutral',
      secretMission: modelSettings[model]?.secretMission ?? '',
      miscConstraint: modelSettings[model]?.miscConstraint ?? '',
    };
  }

  return { ...config, order, modelSettings };
}

export const ChatProvider = ({ children }) => {
  const saved = loadFromStorage();

  const [activeTopTab, setActiveTopTab] = useState(saved?.activeTopTab || 'chat');

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


  const [contextMode, setContextMode] = useState(saved?.contextMode || 'compartmented');

  const [cascadeConfig, setCascadeConfig] = useState(
    buildDefaultCascadeConfig(saved?.selectedModels || ['gpt-5.2', 'claude-sonnet-4-5-20250929', 'gemini-3-flash-preview'], saved?.cascadeConfig)
  );
  const [cascadeRunning, setCascadeRunning] = useState(saved?.cascadeRunning || false);
  const [cascadeProgress, setCascadeProgress] = useState(saved?.cascadeProgress || { round: 0, model: '', turn: 0, totalTurns: 0 });

  // Keep cascade config in sync when selected models change
  useEffect(() => {
    setCascadeConfig(prev => buildDefaultCascadeConfig(selectedModels, prev));
  }, [selectedModels]);

  // Stable prompt index allocator (needed for async loops like cascade)
  const nextIndexRef = useRef(nextIndex);
  useEffect(() => {
    nextIndexRef.current = nextIndex;
  }, [nextIndex]);

  const allocPromptIndex = useCallback(() => {
    const idx = nextIndexRef.current;
    const next = idx + 1;
    nextIndexRef.current = next;
    setNextIndex(next);
    return idx;
  }, []);

  // Persist to sessionStorage on state changes
  useEffect(() => {
    const data = {
      activeTopTab,
      selectedModels, visibleModelIndex, input, messages,
      conversationId, selectedMessages, pausedModels,
      promptHistory, messageIndexMap, nextIndex,
      globalContext, autoExport, modelRoles,
      contextMode,
      cascadeConfig, cascadeRunning, cascadeProgress,
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [activeTopTab, selectedModels, visibleModelIndex, input, messages, conversationId,
      selectedMessages, pausedModels, promptHistory, messageIndexMap,
      nextIndex, globalContext, autoExport, modelRoles,
      contextMode,
      cascadeConfig, cascadeRunning, cascadeProgress]);

  const resetChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setPromptHistory([]);
    setSelectedMessages([]);
    setMessageIndexMap({});
    setNextIndex(1);
    setCascadeRunning(false);
    setCascadeProgress({ round: 0, model: '', turn: 0, totalTurns: 0 });
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <ChatContext.Provider value={{
      activeTopTab, setActiveTopTab,
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
      allocPromptIndex,
      globalContext, setGlobalContext,
      autoExport, setAutoExport,
      modelRoles, setModelRoles,
      contextMode, setContextMode,
      cascadeConfig, setCascadeConfig,
      cascadeRunning, setCascadeRunning,
      cascadeProgress, setCascadeProgress,
      resetChat,
    }}>
      {children}
    </ChatContext.Provider>
  );
};
