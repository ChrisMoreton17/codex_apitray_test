# API Test Tray

This project provides a small cross-platform system tray application that checks the status of an API and displays a green or red icon accordingly. Users can configure the API URL and optional API key through a settings dialog. Configuration values are stored in `~/.api_tray_config.json`.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

For testing (optional):

```bash
pip install -r requirements-dev.txt
```

## Usage

Run the tray application:

```bash
python app.py
```

On the first run, you will be prompted to enter the API URL and optional API key. The application periodically checks the API and updates the tray icon:

- **Green** – API responded successfully.
- **Red** – API request failed or returned a non-OK status.

You can right-click the tray icon to access:
- Check Now: Trigger an immediate API check
- Set API URL / Set API Key: Update credentials directly
- Set Interval: Change the periodic check interval (seconds)
- Settings: Full dialog for URL and key
- Quit

Notifications
- Alerts when the API goes down.
- Alerts when the API recovers and is responding again.
 - Configure under Tray > Notifications: All, Failures Only, or Off.

## Testing

Run unit tests (non-UI logic):

```bash
pytest -q
```

Tests cover config load/save and API status checks. UI behavior is not exercised.

## Build & Deploy (macOS)

Build a macOS app bundle with py2app:

```bash
python3 -m pip install py2app
python3 setup.py py2app
open dist
```

Or use the helper script to build and create a DMG:

```bash
bash scripts/build_mac.sh
```

Customize the bundle identifier in `setup.py` (`CFBundleIdentifier`) before code signing.

### Code signing and notarization (recommended)

To distribute outside the App Store, sign with a Developer ID certificate and notarize with Apple. Summary of steps:

- Ensure Xcode command line tools are installed and you have a Developer ID Application certificate in your login keychain.
- Set a unique bundle identifier in `setup.py`.
- Codesign the built app:

```bash
codesign --deep --force --options runtime \
  --sign "Developer ID Application: Your Name (TEAMID)" \
  "dist/API Test Tray.app"
```

- Notarize (recommended: notarytool). First create a keychain profile or use an API key.

Using an Apple ID keychain profile (once):

```bash
xcrun notarytool store-credentials apitray-profile --apple-id "you@domain.com" --team-id TEAMID --password "app-specific-password"
```

Submit and wait:

```bash
xcrun notarytool submit "dist/API Test Tray.app" --keychain-profile apitray-profile --wait
```

- Staple the ticket:

```bash
xcrun stapler staple "dist/API Test Tray.app"
```

- Optionally wrap into a DMG and sign it:

```bash
hdiutil create -volname "API Test Tray" -srcfolder "dist/API Test Tray.app" -ov -format UDZO "dist/API Test Tray.dmg"
codesign --force --sign "Developer ID Application: Your Name (TEAMID)" "dist/API Test Tray.dmg"
```

Gatekeeper will accept the stapled .app/.dmg on end-user machines.

## GitHub Actions CI/CD

This repo includes a workflow at `.github/workflows/ci.yml` that:
- Runs tests on every push/PR (Linux runner, core logic only).
- Builds a signed, notarized macOS app on tags like `v1.2.3` and attaches a DMG to the GitHub Release.

### Secrets to configure

Set these repository secrets (Settings → Secrets and variables → Actions → New repository secret):

- `MAC_CERT_P12`: Base64-encoded `Developer ID Application` certificate (.p12)
- `MAC_CERT_P12_PASSWORD`: Password for the .p12 file
- `MAC_CODESIGN_IDENTITY`: e.g., `Developer ID Application: Your Name (TEAMID)`
- `MAC_KEYCHAIN_PASSWORD`: Any strong password for the temporary build keychain
- `NOTARY_APPLE_ID`: Apple ID email used for notarization
- `NOTARY_APP_PASSWORD`: App-specific password (from appleid.apple.com) for notarization
- `NOTARY_TEAM_ID`: Your 10-character Team ID

Notes:
- If signing secrets are omitted, the workflow still builds and uploads unsigned artifacts for inspection.
- If notarization secrets are omitted, steps are skipped; you can staple locally later.

### Releasing

Create a version tag to trigger the macOS build and release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds `dist/API Test Tray.app`, signs/notarizes (if secrets present), creates `dist/API Test Tray.dmg`, uploads artifacts, and publishes a GitHub Release with the DMG attached.

### How it works (learning)

- Tests job (Ubuntu): installs `pytest` and `requests`, runs unit tests in `tests/` without needing a GUI.
- macOS job (tagged builds):
  - Installs Python 3.10, project deps, and `py2app`.
  - Builds the `.app` bundle from `setup.py`.
  - Creates a temporary keychain; imports your Developer ID certificate from a base64 secret.
  - Codesigns the app with hardened runtime (`--options runtime`) and a timestamp.
  - Notarizes with `xcrun notarytool submit ... --wait`, then staples.
  - Creates a compressed DMG and attaches it to the GitHub Release.


Note (macOS): When running via `python app.py`, the app tries to hide the Dock icon using AppKit. If `pyobjc` is not installed, this step is skipped (the .app bundle built with py2app already hides the Dock via `LSUIElement`). To enable Dock hiding in script mode, install:

```bash
pip install pyobjc-framework-Cocoa
```
