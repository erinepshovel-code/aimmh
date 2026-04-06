import React from 'react';
import { HubGroupsPanel } from './HubGroupsPanel';
import { HubInstancesPanel } from './HubInstancesPanel';
import { HubMultiChatPanel } from './HubMultiChatPanel';
import { HubResponsesPanel } from './HubResponsesPanel';
import { HubRunsWorkspace } from './HubRunsWorkspace';
import { ClaudeWelcomePanel } from './ClaudeWelcomePanel';
import { KeyManager } from '../settings/KeyManager';
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
  toggleSynthesisBlock,
  synthesisInstanceIds,
  setSynthesisInstanceIds,
  runSynthesis,
  synthesisBusy,
  synthesisBatches,
  welcomeInstance,
}) {
  switch (activeTab) {
    case 'claude':
      return <ClaudeWelcomePanel welcomeInstance={welcomeInstance} prompts={chatPrompts} onSendPrompt={sendChatPrompt} busyKey={chatBusyKey} />;
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
}
