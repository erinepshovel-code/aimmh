import React from 'react';
import { Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { HubGroupsPanel } from '../components/hub/HubGroupsPanel';
import { HubInstancesPanel } from '../components/hub/HubInstancesPanel';
import { HubMultiChatPanel } from '../components/hub/HubMultiChatPanel';
import { HubResponsesPanel } from '../components/hub/HubResponsesPanel';
import { HubRunsWorkspace } from '../components/hub/HubRunsWorkspace';
import { HubSplashScreen } from '../components/hub/HubSplashScreen';
import { HubTabsNav } from '../components/hub/HubTabsNav';
import { ClaudeWelcomePanel } from '../components/hub/ClaudeWelcomePanel';
import { useHubWorkspace } from '../hooks/useHubWorkspace';
import { CLAUDE_MD_CONTEXT } from '../lib/claudeContext';
import { hubApi } from '../lib/hubApi';
import { KeyManager } from '../components/settings/KeyManager';
import { RegistryManager } from '../components/settings/RegistryManager';
import { useAuth } from '../contexts/AuthContext';

const TABS = [
  { id: 'claude', label: 'Claude.md' },
  { id: 'registry', label: 'Registry' },
  { id: 'instantiation', label: 'Instances' },
  { id: 'runs', label: 'Rooms & Runs' },
  { id: 'responses', label: 'Response Synthesis' },
  { id: 'chat', label: 'Chat+Synth' },
];
const FIRST_VISIT_KEY = 'aimmh-first-visit-complete-v1';

export default function AimmhHubPage() {
  const navigate = useNavigate();
  const { logout, isAuthenticated } = useAuth();
  const workspace = useHubWorkspace();
  const [activeTab, setActiveTab] = React.useState('registry');
  const [showSplash, setShowSplash] = React.useState(true);
  const [showWelcomePanel, setShowWelcomePanel] = React.useState(false);
  const [firstVisit, setFirstVisit] = React.useState(false);
  const [welcomeProvisioning, setWelcomeProvisioning] = React.useState(false);
  const [chatPrompts, setChatPrompts] = React.useState([]);
  const [selectedChatPromptId, setSelectedChatPromptId] = React.useState('');
  const [chatBusyKey, setChatBusyKey] = React.useState('');
  const [synthesisBasket, setSynthesisBasket] = React.useState([]);
  const [queueLoaded, setQueueLoaded] = React.useState(false);
  const [synthesisInstanceIds, setSynthesisInstanceIds] = React.useState([]);
  const [synthesisBatches, setSynthesisBatches] = React.useState([]);
  const [synthesisBusy, setSynthesisBusy] = React.useState(false);

  const refreshChatPrompts = React.useCallback(async () => {
    try {
      const response = await hubApi.getChatPrompts();
      const nextPrompts = response?.prompts || [];
      setChatPrompts(nextPrompts);
      if (!selectedChatPromptId && nextPrompts[0]?.prompt_id) {
        setSelectedChatPromptId(nextPrompts[0].prompt_id);
      }
      return nextPrompts;
    } catch (error) {
      toast.error(error.message || 'Failed to load chat prompts');
      return [];
    }
  }, [selectedChatPromptId]);

  const refreshSyntheses = React.useCallback(async () => {
    try {
      const response = await hubApi.getSyntheses();
      setSynthesisBatches(response?.batches || []);
      return response?.batches || [];
    } catch (error) {
      toast.error(error.message || 'Failed to load synthesis batches');
      return [];
    }
  }, []);

  React.useEffect(() => {
    refreshChatPrompts();
    refreshSyntheses();
  }, [refreshChatPrompts, refreshSyntheses]);

  React.useEffect(() => {
    try {
      const seen = window.localStorage.getItem(FIRST_VISIT_KEY) === '1';
      const isFirst = !seen;
      setFirstVisit(isFirst);
      setShowWelcomePanel(isFirst);
      setActiveTab(isFirst ? 'claude' : 'registry');
    } catch {
      setFirstVisit(true);
      setShowWelcomePanel(true);
      setActiveTab('claude');
    }
  }, []);

  const dismissSplash = React.useCallback(() => {
    setShowSplash(false);
    if (firstVisit) {
      try {
        window.localStorage.setItem(FIRST_VISIT_KEY, '1');
      } catch {
        // ignore write issues
      }
    }
  }, [firstVisit]);

  React.useEffect(() => {
    if (firstVisit) return;
    const timer = window.setTimeout(() => dismissSplash(), 1800);
    return () => window.clearTimeout(timer);
  }, [dismissSplash, firstVisit]);

  React.useEffect(() => {
    let active = true;
    const loadQueue = async () => {
      try {
        const state = await hubApi.getState('synthesis-queue-global');
        if (!active) return;
        setSynthesisBasket(Array.isArray(state?.payload?.items) ? state.payload.items : []);
      } catch {
        if (!active) return;
        setSynthesisBasket([]);
      } finally {
        if (active) setQueueLoaded(true);
      }
    };
    loadQueue();
    return () => {
      active = false;
    };
  }, []);

  React.useEffect(() => {
    if (!queueLoaded) return;
    const timer = window.setTimeout(() => {
      hubApi.setState('synthesis-queue-global', { items: synthesisBasket }).catch(() => {});
    }, 350);
    return () => window.clearTimeout(timer);
  }, [queueLoaded, synthesisBasket]);

  const sendChatPrompt = React.useCallback(async (payload) => {
    try {
      setChatBusyKey('send-chat-prompt');
      const detail = await hubApi.sendChatPrompt(payload);
      toast.success('Prompt sent to selected instances');
      const nextPrompts = await refreshChatPrompts();
      if (!nextPrompts.find((item) => item.prompt_id === detail.prompt_id)) {
        setChatPrompts((prev) => [detail, ...prev]);
      }
      await workspace.refreshCore();
      return detail;
    } catch (error) {
      toast.error(error.message || 'Failed to send prompt');
      throw error;
    } finally {
      setChatBusyKey('');
    }
  }, [refreshChatPrompts, workspace]);

  const toggleSynthesisBlock = React.useCallback((block) => {
    setSynthesisBasket((prev) => prev.some((item) => item.source_id === block.source_id)
      ? prev.filter((item) => item.source_id !== block.source_id)
      : [...prev, block]);
  }, []);

  const runSynthesis = React.useCallback(async (payload) => {
    try {
      setSynthesisBusy(true);
      const detail = await hubApi.createSynthesis(payload);
      toast.success('Synthesis complete');
      const nextBatches = await refreshSyntheses();
      if (!nextBatches.find((item) => item.synthesis_batch_id === detail.synthesis_batch_id)) {
        setSynthesisBatches((prev) => [detail, ...prev]);
      }
      setSynthesisBasket([]);
      await workspace.refreshCore();
      return detail;
    } catch (error) {
      toast.error(error.message || 'Synthesis failed');
      throw error;
    } finally {
      setSynthesisBusy(false);
    }
  }, [refreshSyntheses, workspace]);

  const instanceOptions = workspace.instances
    .filter((item) => !item.archived)
    .map((item) => ({ value: item.instance_id, label: `${item.name} · ${item.model_id}` }));

  const curatedWelcomeModelIds = React.useMemo(() => {
    const allowedDevelopers = new Set(['openai', 'anthropic', 'google']);
    return workspace.models
      .filter((developer) => allowedDevelopers.has(developer.developer_id))
      .flatMap((developer) => developer.models.map((model) => model.model_id));
  }, [workspace.models]);

  const welcomeInstance = React.useMemo(
    () => workspace.instances.find((item) => item.metadata?.welcome_model) || null,
    [workspace.instances],
  );

  const welcomeModelValid = !welcomeInstance || curatedWelcomeModelIds.includes(welcomeInstance.model_id);

  React.useEffect(() => {
    if (!welcomeInstance || welcomeModelValid || welcomeProvisioning) return;
    if (curatedWelcomeModelIds.length === 0) return;
    const fallbackModel = curatedWelcomeModelIds[Math.floor(Math.random() * curatedWelcomeModelIds.length)];
    const repairWelcomeModel = async () => {
      try {
        setWelcomeProvisioning(true);
        await workspace.updateInstance(welcomeInstance.instance_id, {
          model_id: fallbackModel,
          instance_prompt: CLAUDE_MD_CONTEXT,
          metadata: { ...(welcomeInstance.metadata || {}), welcome_model: true, welcome_repaired: true },
        });
        await workspace.refreshCore();
      } catch {
        // silent fail, user can continue with other models
      } finally {
        setWelcomeProvisioning(false);
      }
    };
    repairWelcomeModel();
  }, [CLAUDE_MD_CONTEXT, curatedWelcomeModelIds, welcomeInstance, welcomeModelValid, welcomeProvisioning, workspace]);

  React.useEffect(() => {
    if (!firstVisit || workspace.loading || welcomeInstance || welcomeProvisioning) return;
    if (curatedWelcomeModelIds.length === 0) return;
    const modelId = curatedWelcomeModelIds[Math.floor(Math.random() * curatedWelcomeModelIds.length)];
    if (!modelId) return;

    const seedWelcomeModel = async () => {
      try {
        setWelcomeProvisioning(true);
        await workspace.createInstance({
          name: 'Welcome Guide',
          model_id: modelId,
          role_preset: 'Mentor',
          instance_prompt: CLAUDE_MD_CONTEXT,
          history_window_messages: 24,
          metadata: { welcome_model: true, welcome_seed: 'claude-md' },
        });
        await workspace.refreshCore();
      } catch {
        // silent fail: user can still create instances manually
      } finally {
        setWelcomeProvisioning(false);
      }
    };
    seedWelcomeModel();
  }, [CLAUDE_MD_CONTEXT, curatedWelcomeModelIds, firstVisit, welcomeInstance, welcomeProvisioning, workspace]);

  const renderTab = () => {
    switch (activeTab) {
      case 'claude':
        return (
          <ClaudeWelcomePanel
            welcomeInstance={welcomeInstance}
            prompts={chatPrompts}
            onSendPrompt={sendChatPrompt}
            busyKey={chatBusyKey}
          />
        );
      case 'registry':
        return (
          <div className="space-y-4">
            <KeyManager compact />
            <RegistryManager onInventoryChanged={workspace.refreshCore} />
          </div>
        );
      case 'instantiation':
        return (
          <div className="space-y-4">
            <HubInstancesPanel
              modelOptions={workspace.modelOptions}
              instances={workspace.instances}
              includeArchived={workspace.includeArchivedInstances}
              setIncludeArchived={workspace.setIncludeArchivedInstances}
              onCreate={workspace.createInstance}
              onUpdate={workspace.updateInstance}
              onToggleArchive={workspace.toggleInstanceArchive}
              onDeleteArchived={workspace.deleteArchivedInstance}
              onArchiveMany={workspace.archiveManyInstances}
              onRestoreMany={workspace.restoreManyInstances}
              onDeleteMany={workspace.deleteManyArchivedInstances}
              onFetchHistory={workspace.fetchInstanceHistory}
              busyKey={workspace.busyKey}
            />
            <HubGroupsPanel
              instances={workspace.instances}
              groups={workspace.groups}
              includeArchived={workspace.includeArchivedGroups}
              setIncludeArchived={workspace.setIncludeArchivedGroups}
              onCreate={workspace.createGroup}
              onUpdate={workspace.updateGroup}
              onToggleArchive={workspace.toggleGroupArchive}
              busyKey={workspace.busyKey}
            />
          </div>
        );
      case 'runs':
        return (
          <HubRunsWorkspace
            sourceOptions={workspace.sourceOptions}
            instanceOptions={instanceOptions}
            onRun={workspace.createRun}
            busyKey={workspace.busyKey}
            runs={workspace.runs}
            selectedRunId={workspace.selectedRunId}
            setSelectedRunId={workspace.setSelectedRunId}
            includeArchivedRuns={workspace.includeArchivedRuns}
            setIncludeArchivedRuns={workspace.setIncludeArchivedRuns}
            onToggleRunArchive={workspace.toggleRunArchive}
            onDeleteArchivedRun={workspace.deleteArchivedRun}
          />
        );
      case 'responses':
        return (
          <HubResponsesPanel
            runs={workspace.runs}
            selectedRun={workspace.selectedRun}
            selectedRunId={workspace.selectedRunId}
            setSelectedRunId={workspace.setSelectedRunId}
            prompts={chatPrompts}
            selectedPromptId={selectedChatPromptId}
            setSelectedPromptId={setSelectedChatPromptId}
            synthesisBasket={synthesisBasket}
            onToggleSynthesisBlock={toggleSynthesisBlock}
          />
        );
      case 'chat':
      default:
        return (
          <HubMultiChatPanel
            instances={workspace.instances}
            prompts={chatPrompts}
            selectedPromptId={selectedChatPromptId}
            setSelectedPromptId={setSelectedChatPromptId}
            onSendPrompt={sendChatPrompt}
            busyKey={chatBusyKey}
            synthesisBasket={synthesisBasket}
            onToggleSynthesisBlock={toggleSynthesisBlock}
            synthesisInstanceIds={synthesisInstanceIds}
            setSynthesisInstanceIds={setSynthesisInstanceIds}
            onRunSynthesis={runSynthesis}
            synthesisBusy={synthesisBusy}
            synthesisBatches={synthesisBatches}
          />
        );
    }
  };

  if (workspace.loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <div className="flex min-h-[70vh] items-center justify-center px-4">
          <div className="flex items-center gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 px-5 py-4 text-sm text-zinc-400">
            <Loader2 size={16} className="animate-spin text-emerald-400" /> Loading AIMMH…
          </div>
        </div>
      </div>
    );
  }

  if (showSplash) {
    return <HubSplashScreen firstVisit={firstVisit} onDismiss={dismissSplash} />;
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100" data-testid="aimmh-hub-page">
      <main className="mx-auto max-w-[1100px] px-4 py-4 sm:px-6 sm:py-6">
        <div className="space-y-3">
          <div className="sticky top-0 z-20 space-y-2 border-b border-zinc-800 bg-zinc-950/95 pb-3 backdrop-blur" data-testid="hub-tab-selector-shell">
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => navigate('/pricing')}
                className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 transition hover:border-zinc-700 hover:text-white"
                data-testid="hub-open-pricing-button"
              >
                Pricing
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!isAuthenticated) {
                    navigate('/auth', { replace: true });
                    return;
                  }
                  await logout();
                  navigate('/auth', { replace: true });
                }}
                className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 transition hover:border-zinc-700 hover:text-white"
                data-testid="hub-logout-button"
              >
                {isAuthenticated ? 'Logout' : 'Sign in'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowWelcomePanel((prev) => !prev);
                }}
                className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 transition hover:border-zinc-700 hover:text-white"
                data-testid="hub-toggle-ai-guide-button"
              >
                {showWelcomePanel ? 'Hide guide chat' : 'Guide chat'}
              </button>
            </div>
            <HubTabsNav tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
          </div>
          {showWelcomePanel && activeTab !== 'claude' && (
            <ClaudeWelcomePanel
              welcomeInstance={welcomeInstance}
              prompts={chatPrompts}
              onSendPrompt={sendChatPrompt}
              busyKey={chatBusyKey}
            />
          )}
          <div data-testid={`hub-tab-panel-${activeTab}`}>
            {renderTab()}
          </div>
        </div>
      </main>
    </div>
  );
}
