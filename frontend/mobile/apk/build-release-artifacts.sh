#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-bundled}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANDROID_DIR="$ROOT_DIR/android"
OUTPUT_DIR="$ROOT_DIR/mobile/apk/out"

if [[ "$MODE" != "bundled" && "$MODE" != "webview" ]]; then
  echo "Usage: ./mobile/apk/build-release-artifacts.sh [bundled|webview]"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

cd "$ROOT_DIR"
node mobile/apk/switch-capacitor-mode.mjs "$MODE"

if [[ "$MODE" == "bundled" ]]; then
  yarn build
fi

if [[ ! -d "$ANDROID_DIR" ]]; then
  npx cap add android
fi

npx cap sync android

if ! command -v java >/dev/null 2>&1; then
  echo "Android project synced for mode '$MODE'."
  echo "Java/Android SDK not found in this environment, so release binaries were not compiled here."
  echo "Open '$ANDROID_DIR' in Android Studio and run Generate Signed Bundle / APK."
  exit 0
fi

if [[ -n "${ANDROID_KEYSTORE_FILE:-}" ]]; then
  cat > "$ANDROID_DIR/keystore.properties" <<KEYSTORE
storeFile=${ANDROID_KEYSTORE_FILE}
storePassword=${ANDROID_KEYSTORE_PASSWORD:-}
keyAlias=${ANDROID_KEY_ALIAS:-}
keyPassword=${ANDROID_KEY_PASSWORD:-}
KEYSTORE
  echo "Wrote $ANDROID_DIR/keystore.properties from environment variables."
else
  echo "No ANDROID_KEYSTORE_FILE set. Building unsigned release artifacts."
fi

(
  cd "$ANDROID_DIR"
  ./gradlew clean app:bundleRelease app:assembleRelease
)

if [[ -f "$ANDROID_DIR/app/build/outputs/bundle/release/app-release.aab" ]]; then
  cp "$ANDROID_DIR/app/build/outputs/bundle/release/app-release.aab" "$OUTPUT_DIR/aimmh-${MODE}-release.aab"
fi

if [[ -f "$ANDROID_DIR/app/build/outputs/apk/release/app-release.apk" ]]; then
  cp "$ANDROID_DIR/app/build/outputs/apk/release/app-release.apk" "$OUTPUT_DIR/aimmh-${MODE}-release.apk"
fi

echo "Build complete for mode '$MODE'."
echo "Artifacts (when available):"
echo "- $OUTPUT_DIR/aimmh-${MODE}-release.aab"
echo "- $OUTPUT_DIR/aimmh-${MODE}-release.apk"
