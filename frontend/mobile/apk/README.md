# AIMMH APK Build Modes

This folder supports **both APK modes** requested:

- **Mode A — Quick WebView APK**: app opens the live AIMMH URL.
- **Mode B — Bundled Capacitor APK**: app ships frontend assets from local `build/`.

## App Defaults

- App Name: `AIMMH (Assistive Iterational Modular Model Hub)`
- Package ID: `org.interdependentway.aimmh`
- Version defaults are controlled by Android Gradle files once project is generated.

## Local Debug Commands

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

## Play Store Release Workflow (GitHub Actions)

A CI workflow now exists at:

- `.github/workflows/android-store-release.yml`

Trigger it manually from **Actions → Android Store Release → Run workflow**.

### Required repository secrets

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`
- `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`

The workflow:

1. Installs frontend dependencies.
2. Builds production web assets.
3. Runs `npx cap sync android`.
4. Decodes signing keystore + writes `frontend/android/keystore.properties`.
5. Builds signed `bundleRelease` (`.aab`).
6. Uploads `.aab` artifact.
7. Publishes to Play track (`internal`, `alpha`, `beta`, `production`).

> Note: Google Play production uploads are expected to be staged through `internal` first.

## Output

When Java + Android SDK are available, debug APK output is expected at:

`android/app/build/outputs/apk/debug/app-debug.apk`

For store deployments, release AAB output is expected at:

`android/app/build/outputs/bundle/release/app-release.aab`

If Java/SDK are missing locally, the debug script still prepares and syncs the Android project, then prints instructions.
