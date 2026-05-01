import type { CapacitorConfig } from '@capacitor/cli';

const rawBase = process.env.AIMMH_WEBVIEW_URL || process.env.REACT_APP_BACKEND_URL || 'https://aimmh-hub-1.preview.emergentagent.com';
const base = rawBase.replace(/\/$/, '');
const webviewUrl = base.endsWith('/chat') ? base : `${base}/chat`;

const config: CapacitorConfig = {
  appId: 'org.interdependentway.aimmh',
  appName: 'AIMMH (Assistive Iterational Modular Model Hub)',
  webDir: 'build',
  bundledWebRuntime: false,
  server: {
    url: webviewUrl,
    cleartext: false,
  },
  android: {
    allowMixedContent: true,
  },
};

export default config;
