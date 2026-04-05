import React from 'react';
import { ArrowLeft, BadgeCheck, HeartHandshake, Loader2, Sparkles, Users } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { paymentsApi } from '../lib/paymentsApi';

const CATEGORY_ORDER = ['supporter', 'pro', 'team', 'team_addon'];

function PackageCard({ item, onCheckout, loadingPackage }) {
  return (
    <article className="rounded-3xl border border-zinc-800 bg-zinc-900/60 p-4 shadow-[0_10px_40px_rgba(0,0,0,0.2)]" data-testid={`pricing-package-card-${item.package_id}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-zinc-100" data-testid={`pricing-package-title-${item.package_id}`}>{item.name}</h3>
          <p className="mt-2 text-sm text-zinc-500" data-testid={`pricing-package-description-${item.package_id}`}>{item.description}</p>
        </div>
        <div className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-[11px] uppercase tracking-[0.22em] text-zinc-400" data-testid={`pricing-package-category-${item.package_id}`}>{item.category}</div>
      </div>
      <div className="mt-4 text-3xl font-semibold text-zinc-50" data-testid={`pricing-package-amount-${item.package_id}`}>${Number(item.amount).toFixed(2)}{item.billing_type !== 'one_time' ? <span className="text-sm font-normal text-zinc-500"> / {item.billing_type}</span> : null}</div>
      <ul className="mt-4 space-y-2 text-sm text-zinc-300" data-testid={`pricing-package-features-${item.package_id}`}>
        {item.features.map((feature) => <li key={feature}>• {feature}</li>)}
      </ul>
      <button onClick={() => onCheckout(item.package_id)} disabled={loadingPackage === item.package_id} className="mt-5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-60" data-testid={`pricing-package-checkout-button-${item.package_id}`}>
        <span className="flex items-center gap-2">{loadingPackage === item.package_id ? <Loader2 size={14} className="animate-spin" /> : <BadgeCheck size={14} />} Checkout</span>
      </button>
    </article>
  );
}

export default function PricingPageV2() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [catalog, setCatalog] = React.useState([]);
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [loadingPackage, setLoadingPackage] = React.useState('');
  const [pollingStatus, setPollingStatus] = React.useState(false);
  const [hallName, setHallName] = React.useState('');
  const [hallLink, setHallLink] = React.useState('');
  const [donationAmount, setDonationAmount] = React.useState('10.00');

  const loadPricing = React.useCallback(async () => {
    try {
      setLoading(true);
      const [catalogResponse, summaryResponse] = await Promise.all([
        paymentsApi.getCatalog(),
        paymentsApi.getSummary(),
      ]);
      const ordered = [...(catalogResponse.prices || [])].sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category));
      setCatalog(ordered);
      setSummary(summaryResponse);
    } catch (error) {
      toast.error(error.message || 'Failed to load pricing');
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadPricing();
  }, [loadPricing]);

  const pollCheckoutStatus = React.useCallback(async (sessionId) => {
    setPollingStatus(true);
    let attempts = 0;
    while (attempts < 8) {
      attempts += 1;
      try {
        const status = await paymentsApi.getCheckoutStatus(sessionId);
        if (status.payment_status === 'paid') {
          toast.success('Payment successful. AIMMH tier updated.');
          await loadPricing();
          setPollingStatus(false);
          return;
        }
        if (status.status === 'expired') {
          toast.error('Checkout session expired. Please try again.');
          setPollingStatus(false);
          return;
        }
      } catch (error) {
        toast.error(error.message || 'Failed to verify checkout status');
        setPollingStatus(false);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    setPollingStatus(false);
    toast('Payment status still processing. You can refresh this page later.');
  }, [loadPricing]);

  React.useEffect(() => {
    const sessionId = params.get('session_id');
    const checkoutState = params.get('checkout');
    if (checkoutState === 'cancel') toast.error('Checkout cancelled.');
    if (sessionId) pollCheckoutStatus(sessionId);
  }, [params, pollCheckoutStatus]);

  const startCheckout = async (packageId) => {
    try {
      setLoadingPackage(packageId);
      const response = await paymentsApi.createCheckout(packageId, window.location.origin);
      window.location.href = response.url;
    } catch (error) {
      toast.error(error.message || 'Unable to start checkout');
      setLoadingPackage('');
    }
  };

  const startCustomDonation = async () => {
    const parsed = Number(donationAmount);
    if (Number.isNaN(parsed) || parsed < 1) {
      toast.error('Enter a valid donation amount (minimum $1.00).');
      return;
    }
    try {
      setLoadingPackage('supporter_custom');
      const response = await paymentsApi.createCheckout('supporter_custom', window.location.origin, Number(parsed.toFixed(2)));
      window.location.href = response.url;
    } catch (error) {
      toast.error(error.message || 'Unable to start donation checkout');
      setLoadingPackage('');
    }
  };

  const saveHallProfile = async () => {
    try {
      await paymentsApi.updateHallProfile({ display_name: hallName.trim(), link: hallLink.trim() || null, opt_in: true });
      toast.success('Hall of Makers profile updated');
    } catch (error) {
      toast.error(error.message || 'Failed to save Hall of Makers profile');
    }
  };

  const grouped = {
    supporter: catalog.filter((item) => item.category === 'supporter'),
    pro: catalog.filter((item) => item.category === 'pro'),
    team: catalog.filter((item) => ['team', 'team_addon'].includes(item.category)),
  };

  return (
    <div className="min-h-screen bg-zinc-950 px-4 py-6 text-zinc-100 sm:px-6" data-testid="pricing-v2-page">
      <div className="mx-auto max-w-6xl space-y-4">
        <button onClick={() => navigate('/chat')} className="inline-flex items-center gap-2 rounded-xl border border-zinc-800 px-3 py-2 text-sm text-zinc-300 hover:border-zinc-700 hover:text-white" data-testid="pricing-v2-back-button">
          <ArrowLeft size={14} /> Back to AIMMH
        </button>

        <section className="rounded-3xl border border-zinc-800 bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] sm:p-7">
          <div className="flex flex-wrap items-center gap-2 text-emerald-300"><Sparkles size={16} /> AIMMH pricing tiers</div>
          <h1 className="mt-2 text-3xl font-semibold text-zinc-50 sm:text-4xl" data-testid="pricing-v2-title">Free, Supporter, Pro, Team</h1>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-zinc-400" data-testid="pricing-v2-subtitle">Start free with strict trial guardrails, then unlock unlimited orchestration on Pro.</p>
          {summary && (
            <div className="mt-5 flex flex-wrap gap-2 text-xs" data-testid="pricing-v2-summary-chips">
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-current-tier-chip">Current tier: {summary.current_tier}</span>
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-max-instances-chip">Agents: {summary.max_instances === null ? 'Unlimited' : summary.max_instances}</span>
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-max-personas-chip">Personas: {summary.max_personas === null ? 'Unlimited' : summary.max_personas}</span>
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-max-keys-chip">Connected keys: {summary.max_connected_keys === null ? 'Unlimited' : summary.max_connected_keys}</span>
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-max-runs-chip">Runs / month: {summary.max_runs_per_month === null ? 'Unlimited' : summary.max_runs_per_month}</span>
              <span className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1 text-zinc-300" data-testid="pricing-v2-hide-badge-chip">Hide badge: {summary.hide_emergent_badge ? 'Yes' : 'No'}</span>
            </div>
          )}
        </section>

        <section className="grid gap-4 lg:grid-cols-4">
          <article className="rounded-3xl border border-zinc-800 bg-zinc-900/60 p-4 lg:col-span-1" data-testid="pricing-v2-free-tier-card">
            <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">Free</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">$0</div>
            <ul className="mt-4 space-y-2 text-sm text-zinc-300">
              <li>• Max 3 active agents</li>
              <li>• Max 3 saved personas</li>
              <li>• Max 1 connected BYOK key</li>
              <li>• Light batch + monthly usage limits</li>
              <li>• Made with Emergent badge remains visible</li>
            </ul>
          </article>
          <div className="grid gap-4 lg:col-span-3 md:grid-cols-2 xl:grid-cols-3">
            {grouped.supporter.map((item) => <PackageCard key={item.package_id} item={item} onCheckout={startCheckout} loadingPackage={loadingPackage} />)}
            {grouped.pro.map((item) => <PackageCard key={item.package_id} item={item} onCheckout={startCheckout} loadingPackage={loadingPackage} />)}
            {grouped.team.map((item) => <PackageCard key={item.package_id} item={item} onCheckout={startCheckout} loadingPackage={loadingPackage} />)}
          </div>
        </section>

        <section className="rounded-3xl border border-zinc-800 bg-zinc-900/60 p-5" data-testid="pricing-v2-custom-donation-section">
          <div className="flex flex-wrap items-center gap-2 text-zinc-100"><HeartHandshake size={16} /> Effort support donation</div>
          <p className="mt-2 text-sm text-zinc-500" data-testid="pricing-v2-custom-donation-description">
            Enter any one-time amount to support the project effort.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <label className="text-sm text-zinc-400" htmlFor="custom-donation-amount">Amount (USD)</label>
            <input
              id="custom-donation-amount"
              type="number"
              min={1}
              step="0.01"
              value={donationAmount}
              onChange={(event) => setDonationAmount(event.target.value)}
              className="w-40 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50"
              data-testid="pricing-v2-custom-donation-input"
            />
            <button
              type="button"
              onClick={startCustomDonation}
              disabled={loadingPackage === 'supporter_custom'}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:opacity-60"
              data-testid="pricing-v2-custom-donation-button"
            >
              <span className="flex items-center gap-2">
                {loadingPackage === 'supporter_custom' ? <Loader2 size={14} className="animate-spin" /> : <BadgeCheck size={14} />}
                Donate now
              </span>
            </button>
          </div>
        </section>

        {pollingStatus && <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-400">Checking Stripe payment status…</div>}

        {summary?.current_tier && summary.current_tier !== 'free' && (
          <section className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-3xl border border-zinc-800 bg-zinc-900/60 p-5">
              <div className="flex items-center gap-2 text-zinc-100"><HeartHandshake size={16} /> Hall of Makers profile</div>
              <p className="mt-2 text-sm text-zinc-500" data-testid="pricing-v2-hall-description">Supporter, Pro, and Team users can opt into the public credits page.</p>
              <div className="mt-4 space-y-3">
                <input value={hallName} onChange={(event) => setHallName(event.target.value)} placeholder="Display name" className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50" data-testid="pricing-v2-hall-name-input" />
                <input value={hallLink} onChange={(event) => setHallLink(event.target.value)} placeholder="Optional link" className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500/50" data-testid="pricing-v2-hall-link-input" />
                <button onClick={saveHallProfile} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500" data-testid="pricing-v2-save-hall-button">Save Hall profile</button>
              </div>
            </article>
            <article className="rounded-3xl border border-zinc-800 bg-zinc-900/60 p-5">
              <div className="flex items-center gap-2 text-zinc-100"><Users size={16} /> Perk summary</div>
              <ul className="mt-4 space-y-2 text-sm text-zinc-300" data-testid="pricing-v2-perk-summary-list">
                <li>• Supporter: remove badge, higher usage limits, Hall of Makers access</li>
                <li>• Pro: unlimited agents, personas, runs, and connected keys</li>
                <li>• Team: Pro + seat-aware billing foundation for teams</li>
                <li>• Paid tiers hide the Made with Emergent badge automatically</li>
              </ul>
              <button onClick={() => navigate('/makers')} className="mt-4 rounded-xl border border-zinc-800 px-4 py-2 text-sm text-zinc-300 hover:border-zinc-700 hover:text-white" data-testid="pricing-v2-view-makers-button">View Hall of Makers</button>
            </article>
          </section>
        )}

        {loading && <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-500" data-testid="pricing-v2-loading-state">Loading pricing…</div>}
      </div>
    </div>
  );
}
