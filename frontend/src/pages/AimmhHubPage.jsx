// "lines of code":"344","lines of commented":"4"
import React from 'react';
import { Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { HubSplashScreen } from '../components/hub/HubSplashScreen';
import { HubTabsNav } from '../components/hub/HubTabsNav';
import { AimmhHubTabContent } from '../components/hub/AimmhHubTabContent';
import { resolvePatternFromRun } from '../components/hub/patternUtils';
import { useHubWorkspace } from '../hooks/useHubWorkspace';
import { HELP_MODEL_CONTEXT } from '../lib/helpModelContext';
import { hubApi } from '../lib/hubApi';
import { useAuth } from '../contexts/AuthContext';

const SYNTHESIS_QUEUE_LOCAL_KEY = 'aimmh-synthesis-queue-local';

const TABS = [
  { id: 'help', label: 'Help' },
  { id: 'visualizer', label: 'Visualizer' },
  { id: 'registry', label: 'Registry' },
  { id: 'instantiation', label: 'Instances' },
  { id: 'batch-runs', label: 'Batch Runs' },
  { id: 'roleplay-runs', label: 'Roleplay Runs' },
  { id: 'chat', label: 'Chat' },
  { id: 'synthesis', label: 'Synthesis' },
];
const FIRST_VISIT_KEY = 'aimmh-first-visit-complete-v1';

export default function AimmhHubPage() {
  const navigate = useNavigate();
  const { logout, isAuthenticated, user } = useAuth();
  const workspace = useHubWorkspace();
  const [activeTab, setActiveTab] = React.useState('registry');
  const [showSplash, setShowSplash] = React.useState(true);
  const [firstVisit, setFirstVisit] = React.useState(false);
  const [welcomeProvisioning, setWelcomeProvisioning] = React.useState(false);
  const [chatPrompts, setChatPrompts] = React.useState([]);
  const [selectedChatPromptId, setSelectedChatPromptId] = React.useState('');
  const [chatBusyKey, setChatBusyKey] = React.useState('');
  const [synthesisBasket, setSynthesisBasket] = React.useState([]);
  const [synthesisBatches, setSynthesisBatches] = React.useState([]);
  const [sessionSynthesisBatches, setSessionSynthesisBatches] = React.useState([]);
  const [includeSavedSynthesisHistory, setIncludeSavedSynthesisHistory] = React.useState(false);
  const [synthesisBusy, setSynthesisBusy] = React.useState(false);
  const [persistSynthesisQueue, setPersistSynthesisQueue] = React.useState(false);
  const [visualizerPatternId, setVisualizerPatternId] = React.useState('fan_out');
  const [visualizerRunContext, setVisualizerRunContext] = React.useState(null);

  const queuePersistenceScope = React.useMemo(() => {
    if (!isAuthenticated) return 'session';
    if (['supporter', 'pro', 'team'].includes(user?.subscription_tier || 'free')) return 'cloud';
    return 'local';
  }, [isAuthenticated, user?.subscription_tier]);
  const isWsAdmin = user?.subscription_tier === 'ws-tier';

  const tabs = React.useMemo(() => {
    const base = [...TABS];
    if (isWsAdmin) base.splice(2, 0, { id: 'ws-admin', label: 'WS-Admin' });
    return base;
  }, [isWsAdmin]);

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
    let active = true;
    const loadQueue = async () => {
      if (!persistSynthesisQueue) return;
      try {
        if (queuePersistenceScope === 'local') {
          const raw = window.localStorage.getItem(SYNTHESIS_QUEUE_LOCAL_KEY);
          const parsed = raw ? JSON.parse(raw) : [];
          if (active) setSynthesisBasket(Array.isArray(parsed) ? parsed : []);
          return;
        }
        if (queuePersistenceScope === 'cloud') {
          const state = await hubApi.getState('synthesis-queue-global');
          if (active) setSynthesisBasket(Array.isArray(state?.payload?.items) ? state.payload.items : []);
        }
      } catch {
        if (active) setSynthesisBasket([]);
      }
    };
    loadQueue();
    return () => {
      active = false;
    };
  }, [persistSynthesisQueue, queuePersistenceScope]);

  React.useEffect(() => {
    if (!persistSynthesisQueue) return;
    const timer = window.setTimeout(() => {
      if (queuePersistenceScope === 'local') {
        try {
          window.localStorage.setItem(SYNTHESIS_QUEUE_LOCAL_KEY, JSON.stringify(synthesisBasket));
        } catch {
          // noop
        }
      }
      if (queuePersistenceScope === 'cloud') {
        hubApi.setState('synthesis-queue-global', { items: synthesisBasket }).catch(() => {});
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [persistSynthesisQueue, queuePersistenceScope, synthesisBasket]);

  React.useEffect(() => {
    try {
      const seen = window.localStorage.getItem(FIRST_VISIT_KEY) === '1';
      const isFirst = !seen;
      setFirstVisit(isFirst);
      setActiveTab(isFirst ? 'help' : 'registry');
    } catch {
      setFirstVisit(true);
      setActiveTab('help');
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

  const addSynthesisBlock = React.useCallback((block) => {
    setSynthesisBasket((prev) => (prev.some((item) => item.source_id === block.source_id)
      ? prev
      : [...prev, block]));
  }, []);

  const removeSynthesisBlock = React.useCallback((sourceId) => {
    setSynthesisBasket((prev) => prev.filter((item) => item.source_id !== sourceId));
  }, []);

  const runSynthesis = React.useCallback(async (payload) => {
    try {
      setSynthesisBusy(true);
      const detail = await hubApi.createSynthesis(payload);
      toast.success('Synthesis complete');
      if (payload.save_history && isAuthenticated) {
        const nextBatches = await refreshSyntheses();
        if (!nextBatches.find((item) => item.synthesis_batch_id === detail.synthesis_batch_id)) {
          setSynthesisBatches((prev) => [detail, ...prev]);
        }
      } else {
        setSessionSynthesisBatches((prev) => [detail, ...prev]);
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
  }, [isAuthenticated, refreshSyntheses, workspace]);

  const openRunInVisualizer = React.useCallback((run) => {
    if (!run?.run_id) return;
    setVisualizerPatternId(resolvePatternFromRun(run));
    setVisualizerRunContext({
      run_id: run.run_id,
      run_label: run.label || run.run_id,
      run_mode: run.run_mode || 'batch',
      stage_count: Array.isArray(run.stage_summaries) ? run.stage_summaries.length : 0,
    });
    setActiveTab('visualizer');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const synthesisHistory = (isAuthenticated && includeSavedSynthesisHistory)
    ? [...sessionSynthesisBatches, ...synthesisBatches]
    : sessionSynthesisBatches;

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
          instance_prompt: HELP_MODEL_CONTEXT,
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
  }, [curatedWelcomeModelIds, welcomeInstance, welcomeModelValid, welcomeProvisioning, workspace.refreshCore, workspace.updateInstance]);

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
          instance_prompt: HELP_MODEL_CONTEXT,
          history_window_messages: 24,
          metadata: { welcome_model: true, welcome_seed: 'help-model' },
        });
        await workspace.refreshCore();
      } catch {
        // silent fail: user can still create instances manually
      } finally {
        setWelcomeProvisioning(false);
      }
    };
    seedWelcomeModel();
  }, [curatedWelcomeModelIds, firstVisit, welcomeInstance, welcomeProvisioning, workspace.createInstance, workspace.refreshCore]);

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
              {!isAuthenticated && (
                <button
                  type="button"
                  onClick={() => {
                    const shouldCreate = window.confirm(
                      'Guest sessions are IP-rate-limited and cross-session history is not preserved. Create an account now?',
                    );
                    if (shouldCreate) navigate('/auth');
                  }}
                  className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200 transition hover:bg-emerald-500/20"
                  data-testid="hub-create-account-button"
                >
                  Create account
                </button>
              )}
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
            </div>
            <HubTabsNav tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
          </div>
          <div data-testid={`hub-tab-panel-${activeTab}`}>
            <AimmhHubTabContent
              activeTab={activeTab}
              workspace={workspace}
              instanceOptions={instanceOptions}
              chatPrompts={chatPrompts}
              selectedChatPromptId={selectedChatPromptId}
              setSelectedChatPromptId={setSelectedChatPromptId}
              chatBusyKey={chatBusyKey}
              sendChatPrompt={sendChatPrompt}
              synthesisBasket={synthesisBasket}
              addSynthesisBlock={addSynthesisBlock}
              removeSynthesisBlock={removeSynthesisBlock}
              runSynthesis={runSynthesis}
              synthesisBusy={synthesisBusy}
              synthesisHistory={synthesisHistory}
              isAuthenticated={isAuthenticated}
              includeSavedSynthesisHistory={includeSavedSynthesisHistory}
              setIncludeSavedSynthesisHistory={setIncludeSavedSynthesisHistory}
              persistSynthesisQueue={persistSynthesisQueue}
              setPersistSynthesisQueue={setPersistSynthesisQueue}
              queuePersistenceScope={queuePersistenceScope}
              welcomeInstance={welcomeInstance}
              isWsAdmin={isWsAdmin}
              onRunVisualize={openRunInVisualizer}
              visualizerPatternId={visualizerPatternId}
              setVisualizerPatternId={setVisualizerPatternId}
              visualizerRunContext={visualizerRunContext}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
// "lines of code":"363","lines of commented":"4"
