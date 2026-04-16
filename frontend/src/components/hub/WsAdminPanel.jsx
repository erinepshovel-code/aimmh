// "lines of code":"162","lines of commented":"1"
import React from 'react';
import { BarChart3, Database, Loader2, Save, TerminalSquare, Waypoints } from 'lucide-react';
import { toast } from 'sonner';
import { hubApi } from '../../lib/hubApi';
import { CollapsibleSection } from './CollapsibleSection';

/** WS-Admin workspace: billing/pricing editor, endpoints, analytics, CLI. */
export function WsAdminPanel() {
  const [loading, setLoading] = React.useState(true);
  const [tierMap, setTierMap] = React.useState({});
  const [selectedTier, setSelectedTier] = React.useState('free');
  const [tierJson, setTierJson] = React.useState('{}');

  const [packages, setPackages] = React.useState([]);
  const [selectedPackageId, setSelectedPackageId] = React.useState('');
  const [packageJson, setPackageJson] = React.useState('{}');

  const [endpoints, setEndpoints] = React.useState([]);
  const [analytics, setAnalytics] = React.useState({});
  const [cliOutput, setCliOutput] = React.useState('');
  const [busyKey, setBusyKey] = React.useState('');

  const loadAll = React.useCallback(async () => {
    setLoading(true);
    try {
      const [tiersResp, pkgResp, endpointResp, analyticsResp] = await Promise.all([
        hubApi.getWsBillingTiers(),
        hubApi.getWsPricingPackages(),
        hubApi.getWsEndpoints(),
        hubApi.getWsAnalytics(),
      ]);
      const tiers = tiersResp?.tiers || {};
      setTierMap(tiers);
      const tierKeys = Object.keys(tiers);
      if (!tierKeys.includes(selectedTier) && tierKeys[0]) {
        setSelectedTier(tierKeys[0]);
      }
      setPackages(pkgResp?.packages || []);
      if (!selectedPackageId && (pkgResp?.packages || [])[0]?.package_id) {
        setSelectedPackageId(pkgResp.packages[0].package_id);
      }
      setEndpoints(endpointResp?.endpoints || []);
      setAnalytics(analyticsResp || {});
    } catch (err) {
      toast.error(err.message || 'Failed loading WS-Admin data');
    } finally {
      setLoading(false);
    }
  }, [selectedPackageId, selectedTier]);

  React.useEffect(() => {
    loadAll();
  }, [loadAll]);

  React.useEffect(() => {
    const row = tierMap[selectedTier] || {};
    setTierJson(JSON.stringify(row, null, 2));
  }, [selectedTier, tierMap]);

  React.useEffect(() => {
    const row = packages.find((item) => item.package_id === selectedPackageId) || {};
    setPackageJson(JSON.stringify(row, null, 2));
  }, [packages, selectedPackageId]);

  const saveTier = async () => {
    try {
      setBusyKey('save-tier');
      const parsed = JSON.parse(tierJson || '{}');
      await hubApi.updateWsBillingTier(selectedTier, parsed);
      toast.success('Billing tier updated');
      await loadAll();
    } catch (err) {
      toast.error(err.message || 'Tier update failed');
    } finally {
      setBusyKey('');
    }
  };

  const savePackage = async () => {
    try {
      setBusyKey('save-package');
      const parsed = JSON.parse(packageJson || '{}');
      const payload = {
        name: parsed.name,
        amount: Number(parsed.amount),
        currency: parsed.currency,
        billing_type: parsed.billing_type,
        category: parsed.category,
        description: parsed.description,
        grants_tier: parsed.grants_tier,
        stripe_price_id: parsed.stripe_price_id,
        stripe_product_id: parsed.stripe_product_id,
        features: Array.isArray(parsed.features) ? parsed.features : [],
      };
      await hubApi.updateWsPricingPackage(selectedPackageId, payload);
      toast.success('Pricing package updated');
      await loadAll();
    } catch (err) {
      toast.error(err.message || 'Package update failed');
    } finally {
      setBusyKey('');
    }
  };

  const runCli = async (command) => {
    try {
      setBusyKey(`cli-${command}`);
      const result = await hubApi.executeWsCli(command);
      setCliOutput(JSON.stringify(result, null, 2));
    } catch (err) {
      toast.error(err.message || 'CLI command failed');
    } finally {
      setBusyKey('');
    }
  };

  if (loading) {
    return <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4 text-sm text-zinc-400" data-testid="ws-admin-loading"><span className="inline-flex items-center gap-2"><Loader2 size={14} className="animate-spin" /> Loading WS-Admin...</span></div>;
  }

  return (
    <div className="space-y-4" data-testid="ws-admin-panel">
      <CollapsibleSection title="Billing tiers + pricing editor" subtitle="Live edit tier limits and pricing package metadata." icon={Database} defaultOpen={false} testId="ws-admin-billing-pricing-section">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
            <div className="text-xs text-zinc-400">Billing tier</div>
            <select value={selectedTier} onChange={(e) => setSelectedTier(e.target.value)} className="mt-2 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100" data-testid="ws-admin-tier-select">
              {Object.keys(tierMap).map((tier) => <option key={tier} value={tier}>{tier}</option>)}
            </select>
            <textarea value={tierJson} onChange={(e) => setTierJson(e.target.value)} rows={13} className="mt-2 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-100" data-testid="ws-admin-tier-json" />
            <button type="button" onClick={saveTier} disabled={busyKey === 'save-tier'} className="mt-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white" data-testid="ws-admin-save-tier-button"><span className="inline-flex items-center gap-2">{busyKey === 'save-tier' ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Save tier</span></button>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
            <div className="text-xs text-zinc-400">Pricing package</div>
            <select value={selectedPackageId} onChange={(e) => setSelectedPackageId(e.target.value)} className="mt-2 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-100" data-testid="ws-admin-package-select">
              {packages.map((pkg) => <option key={pkg.package_id} value={pkg.package_id}>{pkg.package_id}</option>)}
            </select>
            <textarea value={packageJson} onChange={(e) => setPackageJson(e.target.value)} rows={13} className="mt-2 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-100" data-testid="ws-admin-package-json" />
            <button type="button" onClick={savePackage} disabled={busyKey === 'save-package' || !selectedPackageId} className="mt-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white" data-testid="ws-admin-save-package-button"><span className="inline-flex items-center gap-2">{busyKey === 'save-package' ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />} Save package</span></button>
          </div>
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="API and REST endpoints" subtitle="Live endpoint inventory from backend router map." icon={Waypoints} defaultOpen={false} testId="ws-admin-endpoints-section">
        <div className="max-h-96 overflow-auto rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3" data-testid="ws-admin-endpoints-list">
          {endpoints.map((row) => (
            <div key={`${row.path}-${row.methods?.join(',')}`} className="mb-2 rounded-xl border border-zinc-800 bg-zinc-900/70 px-3 py-2 text-xs text-zinc-300" data-testid={`ws-admin-endpoint-${row.path.replace(/[^a-zA-Z0-9]/g, '-')}`}>
              <div className="text-zinc-100">{row.path}</div>
              <div className="text-zinc-500">{(row.methods || []).join(', ')} · {row.name}</div>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="App analytics" subtitle="Collection-level app counters." icon={BarChart3} defaultOpen={false} testId="ws-admin-analytics-section">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4" data-testid="ws-admin-analytics-grid">
          {Object.entries(analytics).map(([key, value]) => (
            <div key={key} className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2" data-testid={`ws-admin-analytics-${key}`}>
              <div className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">{key}</div>
              <div className="mt-1 text-sm text-zinc-100">{String(value)}</div>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      <CollapsibleSection title="CLI interface" subtitle="Safe allowlist command runner." icon={TerminalSquare} defaultOpen={false} testId="ws-admin-cli-section">
        <div className="flex flex-wrap gap-2">
          {['health_check', 'ready_check', 'line_rules', 'tail_backend_logs', 'sync_readme_registry'].map((cmd) => (
            <button key={cmd} type="button" onClick={() => runCli(cmd)} disabled={busyKey === `cli-${cmd}`} className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:text-white disabled:opacity-60" data-testid={`ws-admin-cli-${cmd}`}>
              {busyKey === `cli-${cmd}` ? 'Running…' : cmd}
            </button>
          ))}
        </div>
        <pre className="mt-3 max-h-80 overflow-auto rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs text-zinc-200" data-testid="ws-admin-cli-output">{cliOutput || 'Run a command above to view output.'}</pre>
      </CollapsibleSection>
    </div>
  );
}

// "lines of code":"162","lines of commented":"1"
