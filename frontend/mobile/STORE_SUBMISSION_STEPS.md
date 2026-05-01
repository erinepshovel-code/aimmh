# AIMMH Store Submission Steps (All Major Stores)

This checklist maps each store to the expected binary format and a practical submission flow.

## 0) One-time release prerequisites

1. Finalize brand assets: icon, splash, screenshots, feature graphics.
2. Verify legal docs: Privacy Policy URL, Terms URL, support email.
3. Confirm production backend URLs and auth callbacks for mobile.
4. Set semantic version + Android `versionCode` / iOS build number.
5. Freeze release notes and known issues.

---

## 1) Google Play (Android)

**Binary format:** `AAB` (preferred/standard).

1. Build bundled release artifacts:
   - `./mobile/apk/build-release-artifacts.sh bundled`
2. Use `mobile/apk/out/aimmh-bundled-release.aab` for upload.
3. In Play Console:
   - Create app listing and store metadata.
   - Fill Data Safety, ads declaration, content rating.
   - Upload to Internal testing.
4. Promote to Closed/Open testing.
5. Roll out Production when validation passes.

---

## 2) Amazon Appstore (Android)

**Binary format:** Signed `APK`.

1. Build bundled release artifacts.
2. Use `mobile/apk/out/aimmh-bundled-release.apk`.
3. In Amazon Developer Console:
   - Create app record, upload APK.
   - Complete ratings, pricing, territories.
4. Submit to review and publish.

---

## 3) Samsung Galaxy Store (Android)

**Binary format:** Signed `APK`.

1. Build bundled release artifacts.
2. Upload signed APK in Samsung Seller Portal.
3. Add store listing assets and regional availability.
4. Complete compliance and review submission.

---

## 4) Huawei AppGallery (Android)

**Binary format:** Signed `APK`.

1. Build bundled release artifacts.
2. Validate dependencies for HMS compatibility if required.
3. Upload APK and metadata in AppGallery Connect.
4. Complete privacy/compliance sections.
5. Submit for review.

---

## 5) Apple App Store (iOS)

**Binary format:** `IPA` via Xcode archive upload.

> APKs are not used on iOS.

1. Generate Capacitor iOS project (`npx cap add ios`) if missing.
2. Open `ios/App/App.xcworkspace` in Xcode.
3. Configure bundle identifier, signing team, and provisioning profile.
4. Archive app and upload to App Store Connect.
5. Complete App Privacy details and TestFlight testing.
6. Submit for App Review.

---

## 6) Microsoft Store

Two common paths:

- **PWA submission** (recommended for web-first app) via Partner Center.
- **Android app via Windows Subsystem for Android support** policies may vary.

For AIMMH today, submit as a **PWA** unless a dedicated Windows package is created.

---

## 7) Operational cadence (every release)

1. Bump versions.
2. Build binaries (`AAB` + `APK`, and `IPA` if shipping iOS).
3. Smoke test on real devices.
4. Upload to test tracks/TestFlight first.
5. Validate analytics/crash monitoring.
6. Promote to production in phases.
