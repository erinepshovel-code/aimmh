import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
axios.defaults.withCredentials = true;

export default function A0Settings() {
  const [a0Health, setA0Health] = useState(null);
  const [checking, setChecking] = useState(false);
  const [a0Url, setA0Url] = useState('http://127.0.0.1:8787');
  const [a0Key, setA0Key] = useState('');
  const [routeViaA0, setRouteViaA0] = useState(false);
  const [autoIngest, setAutoIngest] = useState(false);

  useEffect(() => {
    checkA0Health();
  }, []);

  const checkA0Health = async () => {
    setChecking(true);
    try {
      const response = await axios.get(`${API}/a0/health`);
      setA0Health(response.data);
      if (response.data.status === 'connected') {
        toast.success('Agent Zero connected');
      }
    } catch (error) {
      setA0Health({ status: 'error', error: error.message });
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            🤖 Agent Zero Integration
          </CardTitle>
          <CardDescription>
            Connect to A0 control plane for TIW policy, EDCM logging, and unified routing
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Health Status */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <span className="text-sm">Status</span>
            <Badge variant={a0Health?.status === 'connected' ? 'default' : 'destructive'}>
              {a0Health?.status || 'Unknown'}
            </Badge>
          </div>

          {/* A0 URL */}
          <div className="space-y-2">
            <Label>Agent Zero URL</Label>
            <div className="flex gap-2">
              <Input
                value={a0Url}
                onChange={(e) => setA0Url(e.target.value)}
                placeholder="http://127.0.0.1:8787"
                className="font-mono text-xs"
              />
              <Button size="sm" onClick={checkA0Health} disabled={checking}>
                Test
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Default: localhost:8787 • LAN: http://&lt;PHONE_IP&gt;:8787
            </p>
          </div>

          {/* A0 API Key */}
          <div className="space-y-2">
            <Label>A0 API Key (optional)</Label>
            <Input
              type="password"
              value={a0Key}
              onChange={(e) => setA0Key(e.target.value)}
              placeholder="Leave empty if not required"
              className="font-mono text-xs"
            />
          </div>

          {/* Route via A0 */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <div>
              <Label>Route All Requests via A0</Label>
              <p className="text-xs text-muted-foreground">TIW policy gate + unified logging</p>
            </div>
            <Switch
              checked={routeViaA0}
              onCheckedChange={setRouteViaA0}
              disabled={a0Health?.status !== 'connected'}
            />
          </div>

          {/* Auto-ingest to A0 */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
            <div>
              <Label>Auto-Ingest to A0</Label>
              <p className="text-xs text-muted-foreground">Export to EDCM jsonl after each conversation</p>
            </div>
            <Switch
              checked={autoIngest}
              onCheckedChange={setAutoIngest}
              disabled={a0Health?.status !== 'connected'}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
