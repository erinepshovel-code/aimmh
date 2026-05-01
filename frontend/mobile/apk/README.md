# AIMMH Android Build + Store Submission Guide

This folder supports both Android packaging modes and now includes release artifact output suitable for app stores.

## Packaging Modes

- **Mode A — Quick WebView APK**: app opens the live AIMMH URL.
- **Mode B — Bundled Capacitor APK/AAB**: app ships frontend assets from local `build/`.

## App Defaults

- App Name: `AIMMH (Assistive Iterational Modular Model Hub)`
- Package ID: `org.interdependentway.aimmh`
- Versioning source: `frontend/android/app/build.gradle`

## Build Commands

Run from `/workspace/aimmh/frontend`.
## Local Debug Commands

### Debug APK

```bash
# Mode B (bundled assets)
./mobile/apk/build-debug-apk.sh bundled

# Mode A (webview/live URL)
./mobile/apk/build-debug-apk.sh webview
```

Expected output:

`android/app/build/outputs/apk/debug/app-debug.apk`

### Release artifacts (AAB + APK)

```bash
# Optional signing env vars (recommended for distribution)
export ANDROID_KEYSTORE_FILE=/absolute/path/to/keystore.jks
export ANDROID_KEYSTORE_PASSWORD='...'
export ANDROID_KEY_ALIAS='...'
export ANDROID_KEY_PASSWORD='...'

# Bundled mode release (recommended for store upload)
./mobile/apk/build-release-artifacts.sh bundled

# WebView mode release
./mobile/apk/build-release-artifacts.sh webview
```

Expected copied output artifacts:

- `mobile/apk/out/aimmh-bundled-release.aab`
- `mobile/apk/out/aimmh-bundled-release.apk`
- `mobile/apk/out/aimmh-webview-release.aab`
- `mobile/apk/out/aimmh-webview-release.apk`

If Java/Android SDK are missing, scripts stop after project sync and print next steps.

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

### Google Play Store

1. Build **release AAB** (`aimmh-bundled-release.aab`).
2. Ensure `versionCode` increments for every release.
3. Create/verify Play Console app listing (title, short/full description, screenshots, icon, feature graphic).
4. Complete Data Safety + Privacy Policy declarations.
5. Upload AAB to internal testing, then closed/open/prod tracks.
6. Resolve pre-launch report warnings, then roll out production.

### Amazon Appstore

1. Build **signed release APK** (`aimmh-bundled-release.apk`).
2. Verify target API level meets Amazon requirements.
3. Prepare Amazon listing assets and content rating.
4. Upload APK and complete compatibility/device targeting.
5. Submit for review.

### Samsung Galaxy Store

1. Build **signed release APK**.
2. Register seller account and create new Android app entry.
3. Add binary, screenshots, privacy URL, and region pricing.
4. Complete age rating and compliance forms.
5. Submit for certification.

### Huawei AppGallery

1. Build **signed release APK** (and HMS compatibility checks if using Google APIs).
2. Create AppGallery Connect listing and package name match.
3. Upload APK, fill privacy, permissions, and region distribution metadata.
4. Complete AppGallery review questionnaire.
5. Submit for review.

## Cross-store release discipline

For store deployments, release AAB output is expected at:

`android/app/build/outputs/bundle/release/app-release.aab`

If Java/SDK are missing locally, the debug script still prepares and syncs the Android project, then prints instructions.
