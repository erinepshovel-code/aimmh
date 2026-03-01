import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Bot, Copy, KeyRound, RefreshCw, ShieldAlert, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Switch } from '../ui/switch';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatDate = (value) => {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleString();
};

export const ServiceAccountManager = () => {
  const [accounts, setAccounts] = useState([]);
  const [tokens, setTokens] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [loadingTokens, setLoadingTokens] = useState(false);
  const [creating, setCreating] = useState(false);
  const [issuingToken, setIssuingToken] = useState(false);
  const [createForm, setCreateForm] = useState({ username: '', password: '', label: '' });
  const [tokenForm, setTokenForm] = useState({ password: '', expiresInDays: '90' });
  const [issuedToken, setIssuedToken] = useState('');
  const [oneTokenPerBot, setOneTokenPerBot] = useState(false);
  const [updatingPolicy, setUpdatingPolicy] = useState(false);

  const selectedAccount = useMemo(
    () => accounts.find((item) => item.id === selectedAccountId),
    [accounts, selectedAccountId]
  );

  const loadServiceAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const response = await axios.get(`${API}/auth/service-accounts`);
      const items = response.data?.items || [];
      setAccounts(items);
      setSelectedAccountId((prev) => {
        if (prev && items.some((item) => item.id === prev)) {
          return prev;
        }
        return items[0]?.id || '';
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load service accounts');
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadServiceTokens = async (serviceAccountId) => {
    if (!serviceAccountId) {
      setTokens([]);
      return;
    }
    setLoadingTokens(true);
    try {
      const response = await axios.get(`${API}/auth/service-accounts/${serviceAccountId}/tokens`);
      setTokens(response.data?.items || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load service tokens');
    } finally {
      setLoadingTokens(false);
    }
  };

  const loadServicePolicy = async () => {
    try {
      const response = await axios.get(`${API}/auth/service-account/policy`);
      setOneTokenPerBot(Boolean(response.data?.one_token_per_bot));
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to load service account policy');
    }
  };

  useEffect(() => {
    loadServiceAccounts();
    loadServicePolicy();
  }, []);

  useEffect(() => {
    loadServiceTokens(selectedAccountId);
  }, [selectedAccountId]);

  const handleCreateServiceAccount = async () => {
    if (!createForm.username.trim() || !createForm.password.trim()) {
      toast.error('Username and password are required');
      return;
    }
    setCreating(true);
    try {
      await axios.post(`${API}/auth/service-account/create`, {
        username: createForm.username.trim(),
        password: createForm.password,
        label: createForm.label.trim() || null,
      });
      toast.success('Service account created');
      setCreateForm({ username: '', password: '', label: '' });
      await loadServiceAccounts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create service account');
    } finally {
      setCreating(false);
    }
  };

  const handleToggleServiceAccount = async (account) => {
    try {
      await axios.patch(`${API}/auth/service-accounts/${account.id}`, {
        active: !account.active,
      });
      toast.success(account.active ? 'Service account disabled' : 'Service account enabled');
      await loadServiceAccounts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update service account');
    }
  };

  const handleIssueToken = async () => {
    if (!selectedAccount) {
      toast.error('Select a service account first');
      return;
    }
    if (!tokenForm.password.trim()) {
      toast.error('Enter service account password to issue token');
      return;
    }
    setIssuingToken(true);
    try {
      const response = await axios.post(`${API}/auth/service-account/token`, {
        username: selectedAccount.username,
        password: tokenForm.password,
        expires_in_days: Number(tokenForm.expiresInDays) || 90,
      });
      setIssuedToken(response.data.access_token || '');
      setTokenForm((prev) => ({ ...prev, password: '' }));
      toast.success(oneTokenPerBot ? 'Long-lived token issued (previous active tokens auto-revoked)' : 'Long-lived service token issued');
      await loadServiceTokens(selectedAccount.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to issue service token');
    } finally {
      setIssuingToken(false);
    }
  };

  const handleRevokeToken = async (tokenId) => {
    try {
      await axios.post(`${API}/auth/service-account/tokens/${tokenId}/revoke`);
      toast.success('Service token revoked');
      await loadServiceTokens(selectedAccountId);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to revoke token');
    }
  };

  const handleCopyToken = async () => {
    if (!issuedToken) {
      return;
    }
    try {
      await navigator.clipboard.writeText(issuedToken);
      toast.success('Token copied to clipboard');
    } catch {
      toast.error('Could not copy token');
    }
  };

  const handlePolicyToggle = async (checked) => {
    const previous = oneTokenPerBot;
    setOneTokenPerBot(checked);
    setUpdatingPolicy(true);
    try {
      await axios.put(`${API}/auth/service-account/policy`, {
        one_token_per_bot: checked,
      });
      toast.success(checked ? 'One-token-per-bot enabled' : 'One-token-per-bot disabled');
    } catch (error) {
      setOneTokenPerBot(previous);
      toast.error(error.response?.data?.detail || 'Failed to update service account policy');
    } finally {
      setUpdatingPolicy(false);
    }
  };

  return (
    <Card className="border-border" data-testid="service-account-manager-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2" data-testid="service-account-manager-title">
          <Bot className="h-5 w-5" />
          Service Accounts (a0 / API Automation)
        </CardTitle>
        <CardDescription data-testid="service-account-manager-description">
          Create machine users, issue long-lived bearer tokens, and revoke tokens when needed.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="space-y-3 rounded-lg border border-border bg-muted/20 p-4" data-testid="service-account-create-section">
          <Label className="text-sm" data-testid="service-account-create-label">Create service account</Label>
          <div className="grid gap-3 md:grid-cols-3">
            <Input
              value={createForm.username}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, username: event.target.value }))}
              placeholder="bot_username"
              data-testid="service-account-create-username-input"
            />
            <Input
              type="password"
              value={createForm.password}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="password"
              data-testid="service-account-create-password-input"
            />
            <Input
              value={createForm.label}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, label: event.target.value }))}
              placeholder="label (optional)"
              data-testid="service-account-create-label-input"
            />
          </div>
          <Button
            onClick={handleCreateServiceAccount}
            disabled={creating}
            data-testid="service-account-create-submit-button"
          >
            {creating ? 'Creating...' : 'Create Service Account'}
          </Button>
        </div>

        <div className="space-y-3" data-testid="service-account-list-section">
          <div className="flex items-center justify-between">
            <Label className="text-sm" data-testid="service-account-list-label">Your service accounts</Label>
            <Button
              variant="outline"
              size="sm"
              onClick={loadServiceAccounts}
              disabled={loadingAccounts}
              data-testid="service-account-refresh-button"
            >
              <RefreshCw className={`mr-1 h-3 w-3 ${loadingAccounts ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>

          {accounts.length === 0 && (
            <div className="rounded border border-dashed border-border p-3 text-xs text-muted-foreground" data-testid="service-account-empty-state">
              No service accounts yet.
            </div>
          )}

          {accounts.map((account) => {
            const isSelected = selectedAccountId === account.id;
            return (
              <div
                key={account.id}
                className={`rounded-lg border p-3 ${isSelected ? 'border-primary/60 bg-primary/5' : 'border-border bg-card'}`}
                data-testid={`service-account-item-${account.id}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button
                    type="button"
                    className="text-left"
                    onClick={() => setSelectedAccountId(account.id)}
                    data-testid={`service-account-select-button-${account.id}`}
                  >
                    <div className="text-sm font-semibold" data-testid={`service-account-username-${account.id}`}>{account.username}</div>
                    <div className="text-xs text-muted-foreground" data-testid={`service-account-meta-${account.id}`}>
                      {account.label || 'No label'} • Created {formatDate(account.created_at)}
                    </div>
                  </button>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={account.active ? 'default' : 'outline'}
                      data-testid={`service-account-status-${account.id}`}
                    >
                      {account.active ? 'Active' : 'Disabled'}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggleServiceAccount(account)}
                      data-testid={`service-account-toggle-button-${account.id}`}
                    >
                      {account.active ? (
                        <><ShieldAlert className="mr-1 h-3 w-3" /> Disable</>
                      ) : (
                        <><ShieldCheck className="mr-1 h-3 w-3" /> Enable</>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="space-y-3 rounded-lg border border-border p-4" data-testid="service-account-token-section">
          <Label className="text-sm" data-testid="service-account-token-section-label">
            {selectedAccount ? `Token management for ${selectedAccount.username}` : 'Select a service account to manage tokens'}
          </Label>

          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-2" data-testid="service-account-policy-row">
            <div>
              <div className="text-xs font-medium" data-testid="service-account-policy-title">One active token per bot</div>
              <div className="text-[10px] text-muted-foreground" data-testid="service-account-policy-help">
                When enabled, issuing a new token auto-revokes any previous active token for that bot.
              </div>
            </div>
            <Switch
              checked={oneTokenPerBot}
              disabled={updatingPolicy}
              onCheckedChange={handlePolicyToggle}
              data-testid="service-account-policy-toggle"
            />
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <Input
              type="password"
              value={tokenForm.password}
              onChange={(event) => setTokenForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="service account password"
              disabled={!selectedAccount}
              data-testid="service-account-token-password-input"
            />
            <Input
              type="number"
              min="1"
              max="365"
              value={tokenForm.expiresInDays}
              onChange={(event) => setTokenForm((prev) => ({ ...prev, expiresInDays: event.target.value }))}
              placeholder="Expires in days"
              disabled={!selectedAccount}
              data-testid="service-account-token-expiry-input"
            />
            <Button
              onClick={handleIssueToken}
              disabled={!selectedAccount || issuingToken}
              data-testid="service-account-token-issue-button"
            >
              <KeyRound className="mr-1 h-3 w-3" />
              {issuingToken ? 'Issuing...' : 'Issue Token'}
            </Button>
          </div>

          {issuedToken && (
            <div className="rounded border border-emerald-400/30 bg-emerald-400/10 p-3" data-testid="service-account-issued-token-banner">
              <div className="mb-2 text-xs text-emerald-200" data-testid="service-account-issued-token-help">
                Copy this token now. It will not be shown again.
              </div>
              <div className="flex flex-col gap-2 md:flex-row">
                <Input
                  value={issuedToken}
                  readOnly
                  className="font-mono text-xs"
                  data-testid="service-account-issued-token-value"
                />
                <Button
                  variant="outline"
                  onClick={handleCopyToken}
                  data-testid="service-account-issued-token-copy-button"
                >
                  <Copy className="mr-1 h-3 w-3" /> Copy
                </Button>
              </div>
            </div>
          )}

          <div className="space-y-2" data-testid="service-account-token-list">
            {loadingTokens && (
              <div className="text-xs text-muted-foreground" data-testid="service-account-token-loading">Loading tokens…</div>
            )}
            {!loadingTokens && tokens.length === 0 && (
              <div className="text-xs text-muted-foreground" data-testid="service-account-token-empty">No tokens issued yet.</div>
            )}
            {!loadingTokens && tokens.map((token) => (
              <div
                key={token.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-muted/20 p-2"
                data-testid={`service-account-token-item-${token.id}`}
              >
                <div className="text-xs" data-testid={`service-account-token-meta-${token.id}`}>
                  <div className="font-mono">{token.token_prefix}••••••••</div>
                  <div className="text-muted-foreground">
                    Expires {formatDate(token.expires_at)} • Last used {formatDate(token.last_used_at)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={token.revoked ? 'outline' : 'default'} data-testid={`service-account-token-status-${token.id}`}>
                    {token.revoked ? 'Revoked' : 'Active'}
                  </Badge>
                  {!token.revoked && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleRevokeToken(token.id)}
                      data-testid={`service-account-token-revoke-button-${token.id}`}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
