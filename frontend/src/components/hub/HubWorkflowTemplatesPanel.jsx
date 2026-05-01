// "lines of code":"140","lines of commented":"0"
import React from 'react';
import { Save, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import { hubApi } from '../../lib/hubApi';

const WORKFLOW_TEMPLATES_KEY = 'run-workflow-templates-v1';

export function HubWorkflowTemplatesPanel({ runMode, currentDraft, onApplyTemplate }) {
  const [templates, setTemplates] = React.useState([]);
  const [templateName, setTemplateName] = React.useState('');
  const [busy, setBusy] = React.useState(false);

  const runModeLabel = runMode === 'roleplay' ? 'Roleplay' : 'Batch';

  const loadTemplates = React.useCallback(async () => {
    try {
      const state = await hubApi.getState(WORKFLOW_TEMPLATES_KEY);
      const nextTemplates = Array.isArray(state?.payload?.templates) ? state.payload.templates : [];
      setTemplates(nextTemplates);
    } catch {
      setTemplates([]);
    }
  }, []);

  React.useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const persistTemplates = React.useCallback(async (nextTemplates) => {
    setBusy(true);
    try {
      setTemplates(nextTemplates);
      await hubApi.setState(WORKFLOW_TEMPLATES_KEY, { templates: nextTemplates });
    } finally {
      setBusy(false);
    }
  }, []);

  const saveTemplate = async () => {
    if (!currentDraft?.prompt?.trim() || !Array.isArray(currentDraft?.stages) || currentDraft.stages.length === 0) {
      toast.error('Add a prompt and at least one stage before saving a workflow.');
      return;
    }
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const name = templateName.trim() || `${runModeLabel} workflow ${new Date().toLocaleDateString()}`;
    const nextTemplate = {
      id,
      name,
      run_mode: runMode,
      label: currentDraft.label || '',
      prompt: currentDraft.prompt,
      stages: currentDraft.stages,
      created_at: new Date().toISOString(),
    };
    await persistTemplates([nextTemplate, ...templates]);
    setTemplateName('');
    toast.success('Workflow saved');
  };

  const deleteTemplate = async (templateId) => {
    const next = templates.filter((item) => item.id !== templateId);
    await persistTemplates(next);
    toast.success('Workflow removed');
  };

  const filtered = templates.filter((item) => item.run_mode === runMode);

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="workflow-templates-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100">Saved workflows (scaffold)</h3>
          <p className="text-xs text-zinc-500">Save and reload reusable {runModeLabel.toLowerCase()} run drafts.</p>
        </div>
        <div className="text-[11px] text-zinc-500" data-testid="workflow-template-count">{filtered.length} templates</div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          value={templateName}
          onChange={(event) => setTemplateName(event.target.value)}
          placeholder="Template name (optional)"
          className="min-w-[220px] flex-1 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-200 outline-none focus:border-emerald-500/50"
          data-testid="workflow-template-name-input"
        />
        <button
          type="button"
          onClick={saveTemplate}
          disabled={busy}
          className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200 disabled:opacity-60"
          data-testid="workflow-save-template-button"
        >
          <span className="inline-flex items-center gap-1"><Save size={12} /> Save current</span>
        </button>
      </div>

      <div className="mt-3 space-y-2" data-testid="workflow-template-list">
        {filtered.length === 0 ? (
          <div className="rounded-xl border border-dashed border-zinc-800 p-3 text-xs text-zinc-500">No saved workflows yet for this run mode.</div>
        ) : filtered.map((template) => (
          <article key={template.id} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3" data-testid={`workflow-template-item-${template.id}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-medium text-zinc-200">{template.name}</div>
                <div className="text-[11px] text-zinc-500">{template.stages?.length || 0} stages · {template.created_at?.slice(0, 10)}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => onApplyTemplate(template)}
                  className="rounded-lg border border-zinc-700 px-2 py-1 text-[11px] text-zinc-200"
                  data-testid={`workflow-apply-template-button-${template.id}`}
                >
                  <span className="inline-flex items-center gap-1"><Upload size={11} /> Apply</span>
                </button>
                <button
                  type="button"
                  onClick={() => deleteTemplate(template.id)}
                  className="rounded-lg border border-zinc-700 px-2 py-1 text-[11px] text-zinc-400 hover:border-red-500/30 hover:text-red-300"
                  data-testid={`workflow-delete-template-button-${template.id}`}
                >
                  <span className="inline-flex items-center gap-1"><Trash2 size={11} /> Delete</span>
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

// "lines of code":"140","lines of commented":"0"
