import React from 'react';
import { HubGroupsPanel } from './HubGroupsPanel';
import { HubInstancesPanel } from './HubInstancesPanel';
import { HubMultiChatPanel } from './HubMultiChatPanel';
import { HubSynthesisPanel } from './HubSynthesisPanel';
import { HubRunsWorkspace } from './HubRunsWorkspace';
import { ClaudeWelcomePanel } from './ClaudeWelcomePanel';
import { RegistryManager } from '../settings/RegistryManager';

export function AimmhHubTabContent({
  activeTab,
  workspace,
  instanceOptions,
  chatPrompts,
  selectedChatPromptId,
  setSelectedChatPromptId,
  chatBusyKey,
  sendChatPrompt,
  synthesisBasket,
  addSynthesisBlock,
  removeSynthesisBlock,
  runSynthesis,
  synthesisBusy,
  synthesisHistory,
  isAuthenticated,
  includeSavedSynthesisHistory,
  setIncludeSavedSynthesisHistory,
  welcomeInstance,
}) {
  switch (activeTab) {
    case 'claude':
      return <ClaudeWelcomePanel welcomeInstance={welcomeInstance} prompts={chatPrompts} onSendPrompt={sendChatPrompt} busyKey={chatBusyKey} />;
    case 'registry':
      return <RegistryManager onInventoryChanged={workspace.refreshCore} />;
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
    case 'batch-runs':
      return (
        <HubRunsWorkspace
          runMode="batch"
          sourceOptions={workspace.sourceOptions}
          instanceOptions={instanceOptions}
          onRun={workspace.createRun}
          busyKey={workspace.busyKey}
          runs={workspace.runs.filter((run) => run.run_mode ? run.run_mode === 'batch' : !(run.stage_summaries || []).some((item) => item.pattern === 'roleplay'))}
          selectedRunId={workspace.selectedRunId}
          setSelectedRunId={workspace.setSelectedRunId}
          includeArchivedRuns={workspace.includeArchivedRuns}
          setIncludeArchivedRuns={workspace.setIncludeArchivedRuns}
          onToggleRunArchive={workspace.toggleRunArchive}
          onDeleteArchivedRun={workspace.deleteArchivedRun}
        />
      );
    case 'roleplay-runs':
      return (
        <HubRunsWorkspace
          runMode="roleplay"
          sourceOptions={workspace.sourceOptions}
          instanceOptions={instanceOptions}
          onRun={workspace.createRun}
          busyKey={workspace.busyKey}
          runs={workspace.runs.filter((run) => run.run_mode ? run.run_mode === 'roleplay' : (run.stage_summaries || []).some((item) => item.pattern === 'roleplay'))}
          selectedRunId={workspace.selectedRunId}
          setSelectedRunId={workspace.setSelectedRunId}
          includeArchivedRuns={workspace.includeArchivedRuns}
          setIncludeArchivedRuns={workspace.setIncludeArchivedRuns}
          onToggleRunArchive={workspace.toggleRunArchive}
          onDeleteArchivedRun={workspace.deleteArchivedRun}
        />
      );
    case 'synthesis':
      return (
        <HubSynthesisPanel
          instances={workspace.instances}
          synthesisBasket={synthesisBasket}
          onRemoveFromSynthesis={removeSynthesisBlock}
          onRunSynthesis={runSynthesis}
          synthesisBusy={synthesisBusy}
          synthesisHistory={synthesisHistory}
          isAuthenticated={isAuthenticated}
          includeSavedSynthesisHistory={includeSavedSynthesisHistory}
          setIncludeSavedSynthesisHistory={setIncludeSavedSynthesisHistory}
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
          onAddSynthesisBlock={addSynthesisBlock}
        />
      );
  }
}
