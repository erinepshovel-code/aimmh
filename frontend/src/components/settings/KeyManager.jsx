// "lines of code":"153","lines of commented":"0"
import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Key, Shield, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { registryApi } from '../../lib/registryApi';
import { paymentsApi } from '../../lib/paymentsApi';
import { UpgradeToProModal } from '../ui/UpgradeToProModal';

function statusMeta(status) {
  if (status === 'configured') return { label: 'Configured', className: 'text-emerald-400', icon: CheckCircle };
  if (status === 'universal') return { label: 'Universal Key', className: 'text-blue-400', icon: Shield };
  return { label: 'Missing', className: 'text-amber-400', icon: AlertCircle };
}

export function KeyManager({ compact = false }) {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editDev, setEditDev] = useState('');
  const [editKey, setEditKey] = useState('');
  const [billingSummary, setBillingSummary] = useState(null);
  const [showKeyLimitModal, setShowKeyLimitModal] = useState(false);

  const configuredKeyCount = keys.filter((item) => item.status === 'configured').length;
  const maxConnectedKeys = typeof billingSummary?.max_connected_keys === 'number' ? billingSummary.max_connected_keys : null;

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const [data, summary] = await Promise.all([
        registryApi.getKeys(),
        paymentsApi.getSummary(),
      ]);
      setKeys(data || []);
      setBillingSummary(summary || null);
    } catch (error) {
      toast.error(error.message || 'Failed to load key statuses');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const saveKey = async (developerId) => {
    if (!editKey.trim()) return;

    if (maxConnectedKeys !== null) {
      const target = keys.find((item) => item.developer_id === developerId);
      const isNewConnection = target?.status !== 'configured';
      if (isNewConnection && configuredKeyCount >= maxConnectedKeys) {
        setShowKeyLimitModal(true);
        return;
      }
    }

    try {
      await registryApi.setKey({ developer_id: developerId, api_key: editKey.trim() });
      toast.success(`Saved key for ${developerId}`);
      setEditDev('');
      setEditKey('');
      await fetchKeys();
    } catch (error) {
      if (String(error?.message || '').toLowerCase().includes('connected keys')) {
        setShowKeyLimitModal(true);
      }
      toast.error(error.message || 'Failed to save key');
    }
  };

  const removeKey = async (developerId) => {
    try {
      await registryApi.removeKey(developerId);
      toast.success(`Removed key for ${developerId}`);
      await fetchKeys();
    } catch (error) {
      toast.error(error.message || 'Failed to remove key');
    }
  };

  if (loading) {
    return <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-500" data-testid="key-manager-loading">Loading API key statuses…</div>;
  }

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-4" data-testid="key-manager">
      <div className="mb-3">
        <h2 className="text-base font-semibold text-zinc-100">API keys</h2>
        <p className="text-xs text-zinc-500">Provider credentials and universal-key fallback status.</p>
      </div>
      <div className="space-y-3">
        {keys.map((item) => {
          const meta = statusMeta(item.status);
          const Icon = meta.icon;
          return (
            <article key={item.developer_id} className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
              <div className={`flex flex-wrap items-center justify-between gap-3 ${compact ? '' : 'sm:flex-nowrap'}`}>
                <div className="flex min-w-0 items-start gap-3">
                  <Key size={16} className="mt-0.5 text-zinc-500" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-zinc-200" data-testid={`key-manager-developer-${item.developer_id}`}>{item.developer_id}</div>
                    <div className={`mt-1 flex items-center gap-1 text-xs ${meta.className}`} data-testid={`key-manager-status-${item.developer_id}`}>
                      <Icon size={11} /> {item.masked_key || meta.label}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {editDev === item.developer_id ? (
                    <>
                      <input
                        type="password"
                        value={editKey}
                        onChange={(event) => setEditKey(event.target.value)}
                        placeholder="Provider key"
                        data-testid={`key-manager-input-${item.developer_id}`}
                        className="w-44 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs text-zinc-100 outline-none focus:border-emerald-500/50"
                      />
                      <button onClick={() => saveKey(item.developer_id)} className="rounded-xl bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-500" data-testid={`key-manager-save-button-${item.developer_id}`}>Save</button>
                      <button onClick={() => { setEditDev(''); setEditKey(''); }} className="text-xs text-zinc-500 hover:text-zinc-300" data-testid={`key-manager-cancel-button-${item.developer_id}`}>Cancel</button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          const isNewConnection = item.status !== 'configured';
                          if (isNewConnection && maxConnectedKeys !== null && configuredKeyCount >= maxConnectedKeys) {
                            setShowKeyLimitModal(true);
                            return;
                          }
                          setEditDev(item.developer_id);
                        }}
                        className="rounded-xl border border-zinc-800 px-3 py-2 text-xs text-zinc-300 hover:border-zinc-700 hover:text-white"
                        data-testid={`key-manager-edit-button-${item.developer_id}`}
                      >
                        {item.status === 'missing' ? 'Add key' : 'Change key'}
                      </button>
                      {item.status === 'configured' && (
                        <button onClick={() => removeKey(item.developer_id)} className="rounded-xl border border-zinc-800 p-2 text-zinc-500 hover:border-red-500/30 hover:text-red-300" data-testid={`key-manager-remove-button-${item.developer_id}`}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <UpgradeToProModal
        open={showKeyLimitModal}
        title="Connected key limit reached"
        description="Free tier supports 1 connected BYOK key. Upgrade to Pro for unlimited connected keys."
        currentCount={configuredKeyCount}
        maxAllowed={maxConnectedKeys}
        contextLabel="Connected keys"
        onClose={() => setShowKeyLimitModal(false)}
        onUpgrade={() => {
          window.location.href = '/pricing';
        }}
      />
    </section>
  );
}
// "lines of code":"153","lines of commented":"0"
