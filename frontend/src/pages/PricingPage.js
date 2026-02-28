import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, ShieldCheck, Sparkles, Coins } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
axios.defaults.withCredentials = true;

const getAuthConfig = () => {
  const token = localStorage.getItem('token');
  return token ? { headers: { Authorization: `Bearer ${token}` } } : undefined;
};

const PackageCard = ({ item, onCheckout, loadingPackage, disabled = false, extraBadge = null }) => (
  <Card className="border-border" data-testid={`pricing-package-card-${item.package_id}`}>
    <CardHeader>
      <div className="flex items-center justify-between gap-2">
        <CardTitle className="text-base">{item.name}</CardTitle>
        {extraBadge}
      </div>
      <CardDescription>{item.description}</CardDescription>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="text-2xl font-bold">${Number(item.amount).toFixed(2)}{item.billing_type === 'monthly' ? <span className="text-sm font-normal text-muted-foreground"> / month</span> : ''}</div>
      <ul className="space-y-1 text-sm text-muted-foreground" data-testid={`pricing-features-${item.package_id}`}>
        {item.features.map((feature) => (
          <li key={feature}>• {feature}</li>
        ))}
      </ul>
      <Button
        onClick={() => onCheckout(item.package_id)}
        disabled={disabled || loadingPackage === item.package_id}
        data-testid={`pricing-checkout-btn-${item.package_id}`}
      >
        {loadingPackage === item.package_id ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
        Checkout
      </Button>
    </CardContent>
  </Card>
);

export default function PricingPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [catalog, setCatalog] = useState(null);
  const [activeTab, setActiveTab] = useState('core');
  const [supportRecurring, setSupportRecurring] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingPackage, setLoadingPackage] = useState('');
  const [pollingStatus, setPollingStatus] = useState(false);

  const packages = catalog?.prices || [];
  const corePackages = useMemo(() => packages.filter((p) => p.category === 'core'), [packages]);
  const founderPackages = useMemo(() => packages.filter((p) => p.category === 'founder'), [packages]);
  const creditPackages = useMemo(() => packages.filter((p) => p.category === 'credits'), [packages]);
  const supportPackages = useMemo(() => {
    const mode = supportRecurring ? 'monthly' : 'one_time';
    return packages.filter((p) => p.category === 'support' && p.billing_type === mode);
  }, [packages, supportRecurring]);

  const loadCatalog = async () => {
    setLoading(true);
    try {
      const authConfig = getAuthConfig();
      const response = await axios.get(`${API}/payments/catalog`, authConfig);
      setCatalog(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load pricing catalog');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  const pollCheckoutStatus = async (sessionId) => {
    setPollingStatus(true);
    const authConfig = getAuthConfig();
    let attempts = 0;
    const maxAttempts = 8;

    while (attempts < maxAttempts) {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/payments/checkout/status/${sessionId}`, authConfig);
        const status = response.data;

        if (status.payment_status === 'paid') {
          toast.success('Payment successful. Entitlements activated.');
          setPollingStatus(false);
          loadCatalog();
          return;
        }

        if (status.status === 'expired') {
          toast.error('Checkout session expired. Please try again.');
          setPollingStatus(false);
          return;
        }
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Failed to verify checkout status');
        setPollingStatus(false);
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 2000));
    }

    setPollingStatus(false);
    toast('Payment status still processing. You can refresh this page later.');
  };

  useEffect(() => {
    const sessionId = params.get('session_id');
    if (sessionId) {
      pollCheckoutStatus(sessionId);
    }
  }, [params]);

  const startCheckout = async (packageId) => {
    setLoadingPackage(packageId);
    try {
      const authConfig = getAuthConfig();
      const response = await axios.post(
        `${API}/payments/checkout/session`,
        {
          package_id: packageId,
          origin_url: window.location.origin,
        },
        authConfig,
      );

      if (!response.data?.url) {
        throw new Error('Checkout URL missing');
      }
      window.location.href = response.data.url;
    } catch (error) {
      toast.error(error.response?.data?.detail || error.message || 'Unable to start checkout');
      setLoadingPackage('');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background p-6" data-testid="pricing-page-loading">
        <div className="text-sm text-muted-foreground">Loading pricing…</div>
      </div>
    );
  }

  const founderRemaining = catalog?.founder_slots_remaining ?? 0;

  return (
    <div className="min-h-screen bg-background pb-16" data-testid="pricing-page">
      <div className="max-w-6xl mx-auto p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate('/chat')} data-testid="pricing-back-chat-btn">
            <ArrowLeft className="h-4 w-4 mr-1" />Chat
          </Button>
          <h1 className="text-2xl font-semibold">Pricing & Support</h1>
          <Button variant="outline" size="sm" onClick={() => navigate('/console')} className="ml-auto" data-testid="pricing-go-console-btn">
            Console
          </Button>
        </div>

        {pollingStatus && (
          <Card data-testid="pricing-polling-status-card">
            <CardContent className="py-3 flex items-center gap-2 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />Checking payment status…
            </CardContent>
          </Card>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} data-testid="pricing-tabs">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="core" data-testid="pricing-tab-core">Core Access</TabsTrigger>
            <TabsTrigger value="support" data-testid="pricing-tab-support">Support</TabsTrigger>
            <TabsTrigger value="founder" data-testid="pricing-tab-founder">Founder</TabsTrigger>
            <TabsTrigger value="credits" data-testid="pricing-tab-credits">Compute Credits</TabsTrigger>
          </TabsList>

          <TabsContent value="core" className="mt-4" data-testid="pricing-core-content">
            <div className="grid md:grid-cols-2 gap-3">
              {corePackages.map((item) => (
                <PackageCard
                  key={item.package_id}
                  item={item}
                  onCheckout={startCheckout}
                  loadingPackage={loadingPackage}
                  extraBadge={<Badge variant="outline" className="text-emerald-300"><ShieldCheck className="h-3 w-3 mr-1" />Core</Badge>}
                />
              ))}
              <Card data-testid="pricing-core-copy-card">
                <CardHeader>
                  <CardTitle>$15 / month — Core Access</CardTitle>
                  <CardDescription>Full console access · EDCM instrumentation · Hourly heartbeat · BYO API keys · Cost telemetry</CardDescription>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Designed for continuous usage with instrumentation and reliable payment telemetry.
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="support" className="mt-4 space-y-3" data-testid="pricing-support-content">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Optional Support (one-time or recurring)</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <Label htmlFor="support-recurring-switch">Recurring monthly mode</Label>
                <Switch id="support-recurring-switch" checked={supportRecurring} onCheckedChange={setSupportRecurring} data-testid="support-recurring-switch" />
              </CardContent>
            </Card>
            <div className="grid md:grid-cols-3 gap-3">
              {supportPackages.map((item) => (
                <PackageCard
                  key={item.package_id}
                  item={item}
                  onCheckout={startCheckout}
                  loadingPackage={loadingPackage}
                  extraBadge={<Badge variant="outline"><Sparkles className="h-3 w-3 mr-1" />Support</Badge>}
                />
              ))}
            </div>
          </TabsContent>

          <TabsContent value="founder" className="mt-4" data-testid="pricing-founder-content">
            <div className="grid md:grid-cols-2 gap-3">
              {founderPackages.map((item) => (
                <PackageCard
                  key={item.package_id}
                  item={item}
                  onCheckout={startCheckout}
                  loadingPackage={loadingPackage}
                  disabled={founderRemaining <= 0}
                  extraBadge={<Badge variant="outline" className="text-amber-300">Remaining {founderRemaining}/{catalog?.founder_slots_total}</Badge>}
                />
              ))}
              <Card data-testid="pricing-founder-details-card">
                <CardHeader>
                  <CardTitle>Founder — $153 one-time (limited to 53)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm text-muted-foreground">
                  <div>• Founder registry listing</div>
                  <div>• Founder badge</div>
                  <div>• Locked $15 base rate while active</div>
                  <div>• Early refinement channel</div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="credits" className="mt-4" data-testid="pricing-credits-content">
            <div className="grid md:grid-cols-3 gap-3">
              {creditPackages.map((item) => (
                <PackageCard
                  key={item.package_id}
                  item={item}
                  onCheckout={startCheckout}
                  loadingPackage={loadingPackage}
                  extraBadge={<Badge variant="outline"><Coins className="h-3 w-3 mr-1" />Credits</Badge>}
                />
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
