// "lines of code":"175","lines of commented":"0"
import React from 'react';
import { Activity, FileCode2, RefreshCw, Search, Shapes } from 'lucide-react';
import { hubApi } from '../../lib/hubApi';

function ratioWidth(codeLines, maxCodeLines) {
  if (!maxCodeLines) return '12%';
  const pct = Math.max(12, Math.min(100, Math.round((codeLines / maxCodeLines) * 100)));
  return `${pct}%`;
}

export function DocsModuleMapPanel() {
  const [registry, setRegistry] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const [selectedRoot, setSelectedRoot] = React.useState('all');
  const [selectedPath, setSelectedPath] = React.useState('');

  const loadRegistry = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await hubApi.getReadmeRegistry();
      const modules = Array.isArray(data?.modules) ? data.modules : [];
      setRegistry(data);
      if (modules.length > 0 && !selectedPath) setSelectedPath(modules[0].path);
    } finally {
      setLoading(false);
    }
  }, [selectedPath]);

  React.useEffect(() => {
    loadRegistry();
  }, [loadRegistry]);

  const modules = React.useMemo(() => (Array.isArray(registry?.modules) ? registry.modules : []), [registry]);
  const roots = React.useMemo(() => {
    const set = new Set(modules.map((mod) => (mod.path || '').split('/')[0] || 'other'));
    return ['all', ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, [modules]);

  const filteredModules = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return modules
      .filter((mod) => (selectedRoot === 'all' ? true : (mod.path || '').startsWith(`${selectedRoot}/`)))
      .filter((mod) => (q ? (mod.path || '').toLowerCase().includes(q) : true));
  }, [modules, search, selectedRoot]);

  const grouped = React.useMemo(() => {
    const bucket = {};
    filteredModules.forEach((mod) => {
      const root = (mod.path || '').split('/')[0] || 'other';
      if (!bucket[root]) bucket[root] = [];
      bucket[root].push(mod);
    });
    Object.keys(bucket).forEach((key) => {
      bucket[key].sort((a, b) => (b.lines_of_code || 0) - (a.lines_of_code || 0));
    });
    return bucket;
  }, [filteredModules]);

  const maxCodeLines = React.useMemo(
    () => filteredModules.reduce((max, mod) => Math.max(max, mod.lines_of_code || 0), 0),
    [filteredModules],
  );

  const selectedModule = React.useMemo(
    () => filteredModules.find((mod) => mod.path === selectedPath) || filteredModules[0] || null,
    [filteredModules, selectedPath],
  );

  const violations = Array.isArray(registry?.violations) ? registry.violations.length : 0;

  return (
    <section className="space-y-4" data-testid="docs-module-map-panel">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="docs-module-map-header">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2 text-zinc-100"><Shapes size={16} /><h2 className="text-base font-semibold">Module Map GUI</h2></div>
            <p className="mt-1 text-sm text-zinc-400">Dynamic document graph for backend, frontend, plugins, and orchestration library modules.</p>
          </div>
          <button
            type="button"
            onClick={loadRegistry}
            disabled={loading}
            className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-200 disabled:opacity-60"
            data-testid="docs-module-map-refresh-button"
          >
            <span className="inline-flex items-center gap-2">{loading ? <RefreshCw size={12} className="animate-spin" /> : <RefreshCw size={12} />} Refresh</span>
          </button>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-3" data-testid="docs-module-map-stats-grid">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-xs text-zinc-300" data-testid="docs-module-map-total-modules">Modules: {registry?.module_count || modules.length}</div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-xs text-zinc-300" data-testid="docs-module-map-filtered-modules">Filtered: {filteredModules.length}</div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-xs text-zinc-300" data-testid="docs-module-map-violations">Violations: {violations}</div>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_180px]" data-testid="docs-module-map-controls">
          <label className="relative" data-testid="docs-module-map-search-label">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search module path"
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-9 py-2 text-xs text-zinc-200 outline-none focus:border-emerald-500/50"
              data-testid="docs-module-map-search-input"
            />
          </label>
          <select
            value={selectedRoot}
            onChange={(event) => setSelectedRoot(event.target.value)}
            className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-200"
            data-testid="docs-module-map-root-select"
          >
            {roots.map((root) => (
              <option key={root} value={root}>{root === 'all' ? 'All roots' : root}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]" data-testid="docs-module-map-layout">
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="docs-module-map-graph-zone">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><Activity size={14} /> Graphical module representation</div>
          <div className="max-h-[58vh] space-y-3 overflow-auto pr-1" data-testid="docs-module-map-groups-scroll">
            {Object.keys(grouped).length === 0 ? (
              <div className="rounded-xl border border-dashed border-zinc-800 p-4 text-xs text-zinc-500">No matching modules.</div>
            ) : Object.entries(grouped).map(([root, mods]) => (
              <div key={root} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3" data-testid={`docs-module-map-group-${root}`}>
                <div className="mb-2 text-xs uppercase tracking-[0.16em] text-zinc-500">{root}</div>
                <div className="space-y-2">
                  {mods.slice(0, 24).map((mod) => (
                    <button
                      key={mod.path}
                      type="button"
                      onClick={() => setSelectedPath(mod.path)}
                      className={`w-full rounded-lg border px-2 py-2 text-left text-xs transition ${selectedModule?.path === mod.path ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-zinc-800 bg-zinc-900/50 text-zinc-300 hover:border-zinc-700'}`}
                      data-testid={`docs-module-map-node-${mod.path.replace(/[^a-zA-Z0-9]/g, '-')}`}
                    >
                      <div className="truncate">{mod.path}</div>
                      <div className="mt-1 h-1.5 rounded-full bg-zinc-800">
                        <div className="h-1.5 rounded-full bg-emerald-500/80" style={{ width: ratioWidth(mod.lines_of_code || 0, maxCodeLines) }} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="docs-module-map-detail-zone">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-zinc-100"><FileCode2 size={14} /> Module document detail</div>
          {!selectedModule ? (
            <div className="rounded-xl border border-dashed border-zinc-800 p-4 text-xs text-zinc-500" data-testid="docs-module-map-empty-detail">Select a module node to inspect docs and metrics.</div>
          ) : (
            <div className="space-y-3" data-testid="docs-module-map-module-detail">
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3">
                <div className="text-xs text-zinc-400">Path</div>
                <div className="mt-1 break-all text-sm text-zinc-100" data-testid="docs-module-map-detail-path">{selectedModule.path}</div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300" data-testid="docs-module-map-detail-code-lines">Code lines: {selectedModule.lines_of_code || 0}</div>
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300" data-testid="docs-module-map-detail-comment-lines">Commented lines: {selectedModule.lines_of_commented || 0}</div>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-300" data-testid="docs-module-map-detail-doc">
                {selectedModule.module_doc || 'No module doc available.'}
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3" data-testid="docs-module-map-detail-functions">
                <div className="mb-2 text-xs text-zinc-400">Functions</div>
                <div className="max-h-56 space-y-2 overflow-auto">
                  {(selectedModule.functions || []).slice(0, 16).map((fn) => (
                    <div key={`${selectedModule.path}-${fn.name}`} className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-2 text-xs" data-testid={`docs-module-map-function-${fn.name.replace(/[^a-zA-Z0-9]/g, '-')}`}>
                      <div className="font-medium text-zinc-200">{fn.name}</div>
                      <div className="mt-1 text-zinc-400">{fn.doc || 'No function doc.'}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

// "lines of code":"175","lines of commented":"0"
