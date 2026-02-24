import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Switch } from '../components/ui/switch';
import { ArrowLeft, ExternalLink, Key, Lock, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import A0Settings from '../components/A0Settings';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const UNIVERSAL_STATUS_KEY = 'universal_key_status';
const UNIVERSAL_STATUS_TTL = 10 * 60 * 1000;

// Configure axios to send cookies for authentication
axios.defaults.withCredentials = true;

const UNIVERSAL_STATUS_META = {
  valid: { label: 'Valid', className: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200' },
  invalid: { label: 'Invalid', className: 'border-red-500/40 bg-red-500/10 text-red-200' },
  missing: { label: 'Missing', className: 'border-amber-500/40 bg-amber-500/10 text-amber-200' },
  error: { label: 'Error', className: 'border-orange-500/40 bg-orange-500/10 text-orange-200' }
};

export default function SettingsPage() {
  const navigate = useNavigate();
  const [keys, setKeys] = useState({});
  const [useUniversal, setUseUniversal] = useState({});
  const [editingKey, setEditingKey] = useState(null);
  const [keyInput, setKeyInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [universalStatus, setUniversalStatus] = useState(null);
  const [checkingUniversal, setCheckingUniversal] = useState(false);

  useEffect(() => {
    loadKeys();
    loadUniversalStatus();
  }, []);

  const loadKeys = async () => {
    try {
      // Don't add Authorization header - let axios use cookies automatically
      const response = await axios.get(`${API}/keys`);
      const loadedKeys = response.data;
      setKeys(loadedKeys);
      
      // Set universal flags (default ON for GPT/Claude/Gemini unless explicitly DISABLED)
      const universalFlags = {};
      Object.entries(loadedKeys).forEach(([provider, key]) => {
        if (API_KEY_GUIDES[provider]?.universal) {
          universalFlags[provider] = key !== 'DISABLED' && (key === 'UNIVERSAL' || !key);
        } else {
          universalFlags[provider] = false;
        }
      });
      setUseUniversal(universalFlags);
    } catch (error) {
      console.error('Load keys error:', error);
      toast.error(error.response?.data?.detail || 'Failed to load API keys. Please login again.');
    }
  };

  const loadUniversalStatus = () => {
    try {
      const raw = sessionStorage.getItem(UNIVERSAL_STATUS_KEY);
      if (!raw) {
        checkUniversalStatus();
        return;
      }
      const cached = JSON.parse(raw);
      const checkedAt = cached?.checked_at ? new Date(cached.checked_at).getTime() : 0;
      if (Date.now() - checkedAt < UNIVERSAL_STATUS_TTL) {
        setUniversalStatus(cached);
        return;
      }
      checkUniversalStatus();
    } catch {
      checkUniversalStatus();
    }
  };

  const checkUniversalStatus = async () => {
    setCheckingUniversal(true);
    try {
      const res = await axios.get(`${API}/keys/universal/status`);
      const payload = { ...res.data, checked_at: new Date().toISOString() };
      setUniversalStatus(payload);
      sessionStorage.setItem(UNIVERSAL_STATUS_KEY, JSON.stringify(payload));
    } catch (error) {
      const payload = {
        status: 'error',
        message: error.response?.data?.detail || 'Unable to validate universal key',
        checked_at: new Date().toISOString()
      };
      setUniversalStatus(payload);
      sessionStorage.setItem(UNIVERSAL_STATUS_KEY, JSON.stringify(payload));
      toast.error('Universal key check failed');
    } finally {
      setCheckingUniversal(false);
    }
  };

  const handleSaveKey = async (provider) => {
    setLoading(true);
    try {
      // Don't add Authorization header - let axios use cookies automatically
      await axios.put(`${API}/keys`, {
        provider,
        api_key: keyInput,
        use_universal: false
      });
      toast.success('API key saved');
      setEditingKey(null);
      setKeyInput('');
      loadKeys();
    } catch (error) {
      toast.error('Failed to save API key');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUniversal = async (provider, enabled) => {
    setLoading(true);
    
    // Optimistically update UI
    setUseUniversal(prev => ({
      ...prev,
      [provider]: enabled
    }));
    
    try {
      // Don't add Authorization header - let axios use cookies automatically
      await axios.put(`${API}/keys`, {
        provider,
        use_universal: enabled
      });
      
      toast.success(
        enabled 
          ? `✓ ${API_KEY_GUIDES[provider].name} - Using universal key` 
          : `${API_KEY_GUIDES[provider].name} - Universal key disabled`
      );
      
      // Reload to confirm from server
      await loadKeys();
    } catch (error) {
      console.error('Toggle error:', error);
      toast.error(error.response?.data?.detail || 'Failed to update key setting');
      
      // Revert optimistic update on error
      setUseUniversal(prev => ({
        ...prev,
        [provider]: !enabled
      }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto p-4 md:p-6">
        {/* Header */}
        <div className="mb-6 flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/chat')}
            data-testid="back-to-chat-btn"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Chat
          </Button>
          <h1 className="text-3xl font-bold" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Settings
          </h1>
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="ml-auto"
            data-testid="go-to-dashboard-btn"
          >
            <BarChart3 className="h-4 w-4 mr-1" />
            Dashboard
          </Button>
        </div>

        {/* Universal Key Info */}
        <Card className="mb-6 border-primary/20 bg-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              Universal Key
            </CardTitle>
            <CardDescription>
              Use the Emergent universal key for GPT, Claude, and Gemini models without providing your own API keys.
            </CardDescription>
          </CardHeader>
        </Card>

        {/* Agent Zero Integration */}
        <div className="mb-6">
          <A0Settings />
        </div>

        {/* API Keys */}
        <div className="space-y-4">
          {Object.entries(API_KEY_GUIDES).map(([provider, info]) => (
            <Card key={provider} className="border-border" data-testid={`api-key-card-${provider}`}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="h-10 w-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: info.color + '20', borderColor: info.color + '40' }}
                    >
                      <Lock className="h-5 w-5" style={{ color: info.color }} />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{info.name}</CardTitle>
                      <CardDescription>
                        {keys[provider] && keys[provider] !== 'UNIVERSAL' ? (
                          <span className="text-xs font-mono">{keys[provider]}</span>
                        ) : useUniversal[provider] ? (
                          <span className="text-xs text-muted-foreground">Using universal key</span>
                        ) : keys[provider] === 'DISABLED' ? (
                          <span className="text-xs text-muted-foreground">Universal key disabled</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">No key configured</span>
                        )}
                      </CardDescription>
                    </div>
                  </div>
                  <a
                    href={info.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                    data-testid={`api-guide-link-${provider}`}
                  >
                    Get API Key
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {info.universal && (
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <Label htmlFor={`universal-${provider}`} className="text-sm">
                      Use Universal Key (Emergent)
                    </Label>
                    <Switch
                      id={`universal-${provider}`}
                      checked={useUniversal[provider] || false}
                      onCheckedChange={(checked) => handleToggleUniversal(provider, checked)}
                      disabled={loading}
                      data-testid={`universal-switch-${provider}`}
                    />
                  </div>
                )}

                {!useUniversal[provider] && (
                  <>
                    {editingKey === provider ? (
                      <div className="space-y-2">
                        <Input
                          type="password"
                          placeholder="Enter your API key"
                          value={keyInput}
                          onChange={(e) => setKeyInput(e.target.value)}
                          className="font-mono text-sm"
                          data-testid={`api-key-input-${provider}`}
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleSaveKey(provider)}
                            disabled={loading || !keyInput}
                            data-testid={`save-key-btn-${provider}`}
                          >
                            Save Key
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingKey(null);
                              setKeyInput('');
                            }}
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditingKey(provider)}
                        data-testid={`edit-key-btn-${provider}`}
                      >
                        {keys[provider] && keys[provider] !== 'UNIVERSAL' ? 'Update Key' : 'Add Key'}
                      </Button>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
