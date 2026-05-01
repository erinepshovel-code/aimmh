import { copyFile } from 'node:fs/promises';
import path from 'node:path';

const mode = process.argv[2] || 'bundled';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', '..');
const source = mode === 'webview'
  ? path.join(root, 'capacitor.config.webview.ts')
  : path.join(root, 'capacitor.config.bundled.ts');
const destination = path.join(root, 'capacitor.config.ts');

await copyFile(source, destination);
console.log(`Capacitor mode set to: ${mode}`);
console.log(`Runtime config: ${destination}`);
