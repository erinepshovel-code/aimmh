# AIMMH APK Build Modes

This folder supports **both APK modes** requested:

- **Mode A — Quick WebView APK**: app opens the live AIMMH URL.
- **Mode B — Bundled Capacitor APK**: app ships frontend assets from local `build/`.

## App Defaults

- App Name: `AIMMH (Assistive Iterational Modular Model Hub)`
- Package ID: `org.interdependentway.aimmh`
- Version defaults are controlled by Android Gradle files once project is generated.

## Commands

Run from `/app/frontend`:

```bash
# Mode B (bundled assets)
./mobile/apk/build-debug-apk.sh bundled

# Mode A (webview/live URL)
./mobile/apk/build-debug-apk.sh webview
```

## Mode Switching

The mode switch script copies one of these files into `capacitor.config.ts`:

- `capacitor.config.bundled.ts`
- `capacitor.config.webview.ts`

For WebView mode, it uses `AIMMH_WEBVIEW_URL` if present, otherwise `REACT_APP_BACKEND_URL`, and defaults to `/chat` path.

## Output

When Java + Android SDK are available, debug APK output is expected at:

`android/app/build/outputs/apk/debug/app-debug.apk`

If Java/SDK are missing, the script still prepares and syncs the Android project, then prints instructions.
