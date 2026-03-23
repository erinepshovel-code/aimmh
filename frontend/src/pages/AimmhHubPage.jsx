import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../contexts/AuthContext';
import { HubGroupsPanel } from '../components/hub/HubGroupsPanel';
import { HubHeader } from '../components/hub/HubHeader';
import { HubInstancesPanel } from '../components/hub/HubInstancesPanel';
import { HubMultiChatPanel } from '../components/hub/HubMultiChatPanel';
import { HubReadmeSplash } from '../components/hub/HubReadmeSplash';
import { HubResponsesPanel } from '../components/hub/HubResponsesPanel';
import { HubRunsWorkspace } from '../components/hub/HubRunsWorkspace';
import { HubTabsNav } from '../components/hub/HubTabsNav';
import { useHubWorkspace } from '../hooks/useHubWorkspace';
import { hubApi } from '../lib/hubApi';
import { KeyManager } from '../components/settings/KeyManager';
import { RegistryManager } from '../components/settings/RegistryManager';

const TABS = [
  { id: 'registry', label: 'Registry' },
  { id: 'instantiation', label: 'Model & Group Instantiation' },
  { id: 'runs', label: 'Rooms, Runs, Orders & Prompts' },
  { id: 'responses', label: 'Responses' },
  { id: 'chat', label: 'Chat & Synthesis' },
];

export default function AimmhHubPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const workspace = useHubWorkspace();
  const [activeTab, setActiveTab] = React.useState('registry');
  const [chatPrompts, setChatPrompts] = React.useState([]);
  const [selectedChatPromptId, setSelectedChatPromptId] = React.useState('');
  const [chatBusyKey, setChatBusyKey] = React.useState('');

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

  React.useEffect(() => {
    refreshChatPrompts();
  }, [refreshChatPrompts]);

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

  const instanceOptions = workspace.instances
    .filter((item) => !item.archived)
    .map((item) => ({ value: item.instance_id, label: `${item.name} · ${item.model_id}` }));

  const renderTab = () => {
    switch (activeTab) {
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
          />
        );
    }
  };

  if (workspace.loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <HubHeader onLogout={logout} onOpenSettings={() => navigate('/settings')} onExportInventory={workspace.exportInventory} />
        <div className="flex min-h-[70vh] items-center justify-center px-4">
          <div className="flex items-center gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/60 px-5 py-4 text-sm text-zinc-400">
            <Loader2 size={16} className="animate-spin text-emerald-400" /> Loading AIMMH…
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <HubHeader onLogout={logout} onOpenSettings={() => navigate('/settings')} onExportInventory={workspace.exportInventory} />
      <main className="mx-auto max-w-[1100px] px-4 py-4 sm:px-6 sm:py-6">
        <div className="space-y-4">
          <HubReadmeSplash />
          <HubTabsNav tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />
          {renderTab()}
        </div>
      </main>
    </div>
  );
}
