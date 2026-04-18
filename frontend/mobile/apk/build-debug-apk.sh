#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-bundled}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "$MODE" != "bundled" && "$MODE" != "webview" ]]; then
  echo "Usage: ./mobile/apk/build-debug-apk.sh [bundled|webview]"
  exit 1
fi

cd "$ROOT_DIR"
node mobile/apk/switch-capacitor-mode.mjs "$MODE"

if [[ "$MODE" == "bundled" ]]; then
  yarn build
fi

if [[ ! -d "$ROOT_DIR/android" ]]; then
  npx cap add android
fi

npx cap sync android

if ! command -v java >/dev/null 2>&1; then
  echo "Android project synced for mode '$MODE'."
  echo "Java/Android SDK not found in this environment, so APK binary was not compiled here."
  echo "Open '$ROOT_DIR/android' in Android Studio and run Assemble Debug to generate APK."
  exit 0
fi

(cd "$ROOT_DIR/android" && ./gradlew assembleDebug)
echo "APK should be at: $ROOT_DIR/android/app/build/outputs/apk/debug/app-debug.apk"
