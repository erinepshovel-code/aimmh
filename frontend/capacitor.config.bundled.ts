import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'org.interdependentway.aimmh',
  appName: 'AIMMH (Assistive Iterational Modular Model Hub)',
  webDir: 'build',
  bundledWebRuntime: false,
  android: {
    allowMixedContent: true,
  },
};

export default config;
