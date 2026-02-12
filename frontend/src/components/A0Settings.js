import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { Wifi, WifiOff, Cloud, Smartphone, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
axios.defaults.withCredentials = true;

export default function A0Settings() {
  const [config, setConfig] = useState({
    mode: 'local',
    local_url: 'http://192.168.1.1',
    local_port: 8787,
    cloud_url: '',
    api_key: '',
    route_via_a0: false,
    auto_ingest: false
  });
  const [health, setHealth] = useState(null);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await axios.get(`${API}/a0/config`);
      setConfig(res.data);
    } catch (err) {
      // use defaults
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      await axios.put(`${API}/a0/config`, config);
      toast.success('A0 config saved');
    } catch (err) {
      toast.error('Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const checkHealth = async () => {
    setChecking(true);
    try {
      const res = await axios.get(`${API}/a0/health`);
      setHealth(res.data);
      if (res.data.status === 'connected') {
        toast.success('Agent Zero connected');
      } else {
        toast.error(`A0: ${res.data.status}`);
      }
    } catch (err) {
      setHealth({ status: 'error' });
      toast.error('Health check failed');
    } finally {
      setChecking(false);
    }
  };

  const statusColor = health?.status === 'connected' ? 'text-emerald-400' : health?.status === 'unreachable' ? 'text-red-400' : 'text-muted-foreground';

  return (
    <Card className="border-border" data-testid="a0-settings-card">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          Agent Zero Integration
          <Badge variant={health?.status === 'connected' ? 'default' : 'outline'} className="text-[10px] ml-auto">
            {health?.status || 'Unknown'}
          </Badge>
        </CardTitle>
        <CardDescription className="text-xs">
          Connect to A0 control plane for EDCM analysis and unified routing
        </CardDescription>
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        {/* Connection Mode Tabs */}
        <div className="flex gap-2">
          <Button
            variant={config.mode === 'local' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setConfig(prev => ({ ...prev, mode: 'local' }))}
            className="flex-1"
            data-testid="a0-mode-local"
          >
            <Smartphone className="h-3 w-3 mr-1" /> Local Device
          </Button>
          <Button
            variant={config.mode === 'cloud' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setConfig(prev => ({ ...prev, mode: 'cloud' }))}
            className="flex-1"
            data-testid="a0-mode-cloud"
          >
            <Cloud className="h-3 w-3 mr-1" /> Google Cloud
          </Button>
        </div>

        {/* Local Device Config */}
        {config.mode === 'local' && (
          <div className="space-y-3 p-3 rounded-lg bg-muted/30 border border-border">
            <Label className="text-xs font-medium flex items-center gap-1">
              <Smartphone className="h-3 w-3" /> Samsung Galaxy A16u / Local Device
            </Label>
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-2">
                <Label className="text-[10px] text-muted-foreground">Device IP / URL</Label>
                <Input
                  value={config.local_url}
                  onChange={e => setConfig(prev => ({ ...prev, local_url: e.target.value }))}
                  placeholder="http://192.168.1.50"
                  className="font-mono text-xs h-8"
                  data-testid="a0-local-url"
                />
              </div>
              <div>
                <Label className="text-[10px] text-muted-foreground">Port</Label>
                <Input
                  type="number"
                  value={config.local_port}
                  onChange={e => setConfig(prev => ({ ...prev, local_port: parseInt(e.target.value) || 8787 }))}
                  placeholder="8787"
                  className="font-mono text-xs h-8"
                  data-testid="a0-local-port"
                />
              </div>
            </div>
            <p className="text-[10px] text-muted-foreground">
              LAN: http://&lt;PHONE_IP&gt;:PORT &middot; Spawnable subagents on configurable ports
            </p>
          </div>
        )}

        {/* Google Cloud Config (Stub) */}
        {config.mode === 'cloud' && (
          <div className="space-y-3 p-3 rounded-lg bg-muted/30 border border-border">
            <Label className="text-xs font-medium flex items-center gap-1">
              <Cloud className="h-3 w-3" /> Google Cloud Endpoint
            </Label>
            <Input
              value={config.cloud_url}
              onChange={e => setConfig(prev => ({ ...prev, cloud_url: e.target.value }))}
              placeholder="https://your-a0-instance.run.app"
              className="font-mono text-xs h-8"
              data-testid="a0-cloud-url"
            />
            <Badge variant="outline" className="text-[9px]">Coming Soon &mdash; Cloud deployment stub</Badge>
          </div>
        )}

        {/* API Key */}
        <div className="space-y-1">
          <Label className="text-xs">A0 API Key (optional)</Label>
          <Input
            type="password"
            value={config.api_key}
            onChange={e => setConfig(prev => ({ ...prev, api_key: e.target.value }))}
            placeholder="Leave empty if not required"
            className="font-mono text-xs h-8"
            data-testid="a0-api-key"
          />
        </div>

        {/* Toggles */}
        <div className="space-y-2">
          <div className="flex items-center justify-between p-2 rounded bg-muted/30">
            <div>
              <Label className="text-xs">Route via A0</Label>
              <p className="text-[10px] text-muted-foreground">TIW policy gate + unified logging</p>
            </div>
            <Switch
              checked={config.route_via_a0}
              onCheckedChange={v => setConfig(prev => ({ ...prev, route_via_a0: v }))}
              data-testid="a0-route-toggle"
            />
          </div>
          <div className="flex items-center justify-between p-2 rounded bg-muted/30">
            <div>
              <Label className="text-xs">Auto-Ingest to A0</Label>
              <p className="text-[10px] text-muted-foreground">Export EDCM jsonl after each conversation</p>
            </div>
            <Switch
              checked={config.auto_ingest}
              onCheckedChange={v => setConfig(prev => ({ ...prev, auto_ingest: v }))}
              data-testid="a0-ingest-toggle"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <Button size="sm" onClick={saveConfig} disabled={saving} className="flex-1" data-testid="a0-save-btn">
            {saving ? 'Saving...' : 'Save Config'}
          </Button>
          <Button size="sm" variant="outline" onClick={checkHealth} disabled={checking} data-testid="a0-health-btn">
            <RefreshCw className={`h-3 w-3 mr-1 ${checking ? 'animate-spin' : ''}`} />
            Test
          </Button>
        </div>

        {/* Health details */}
        {health && (
          <div className="text-[10px] p-2 rounded bg-muted/30 space-y-1">
            <div className="flex items-center gap-1">
              {health.status === 'connected' ? <Wifi className="h-3 w-3 text-emerald-400" /> : <WifiOff className="h-3 w-3 text-red-400" />}
              <span className={statusColor}>{health.status}</span>
            </div>
            {health.a0_url && <div className="text-muted-foreground font-mono">{health.a0_url}</div>}
            {health.error && <div className="text-red-400">{health.error}</div>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
