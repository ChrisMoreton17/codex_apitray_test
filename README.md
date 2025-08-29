# API Test Tray

API Test Tray is a lightweight menu bar (system tray) and Dock app that pings an HTTP endpoint on an interval and shows a clear up/down status. It is designed to be simple, unobtrusive, and reliable for quick API health checks during development or operations.

At a glance, you get:
- A colored tray icon with a bold badge (✓ for OK, ! for Down).
- A Dock-visible window for setup, status, and quick actions.
- First-run onboarding to capture your API URL and optional API key.
- Notifications on failures and (optionally) recoveries.
- Logs for diagnostics and an optional debug window that tails them live.

Configuration is stored in `~/.api_tray_config.json`.

## Features

- Status indicator in the menu bar with an easily visible icon.
- First-run settings dialog and a Dock window for ongoing control.
- Manual “Check Now”, adjustable interval, and notification modes (All, Failures Only, Off).
- Persistent config (URL, API key, interval, notifications).
- Structured logging to `~/Library/Logs/api_test_tray.log` (macOS) for troubleshooting.
- Optional debug window (`python debug_ui.py`) to tail logs and trigger checks.

## Tech Stack

- Python 3.10
- PyQt5 (Qt Widgets for tray icon, menus, and window)
- Requests (HTTP checks)
- Pillow + iconutil (build-time .icns icon generation)
- py2app (macOS app bundling)
- GitHub Actions (tests, build, codesign, notarization, DMG release)
- pytest (core logic tests)

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

Run the tray application (menu bar + Dock window):

```bash
python app.py
```

On the first run, you will be prompted to enter the API URL and optional API key. The application periodically checks the API and updates the tray icon:

- **Green** – API responded successfully.
- **Red** – API request failed or returned a non-OK status.

Tip: Use quick test endpoints like `https://httpbin.org/status/200` (OK) and `https://httpbin.org/status/500` (Down).

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

### Configuration

The app stores configuration in `~/.api_tray_config.json` with keys:
- `api_url`: string
- `api_key`: string (optional, used as `Authorization: Bearer <key>`) 
- `interval_seconds`: number (default 60)
- `notify_mode`: `all` | `fail` | `off`

### App window (Dock) and debug

The app now has a Dock-visible window for initial setup and troubleshooting. From the tray icon, choose “Open App Window…”. On first run, this window opens automatically.

For additional diagnostics, you can also run a standalone debug window alongside the app:

```bash
python debug_ui.py
```

This opens a small window that:
- Shows your current config (URL, interval, notifications)
- Tails the app log at `~/Library/Logs/api_test_tray.log` (macOS)
- Lets you trigger a “Check Now” to test the endpoint
- Buttons to open the config and log file

## Testing

Run unit tests (non-UI logic):

```bash
pytest -q
```

Tests cover config load/save and API status checks. UI behavior is not exercised.

## How It Works

- The tray icon is a small, high-contrast, dynamically drawn icon with a status badge.
- Status checks use `requests.get` with a 5s timeout, treating any non-2xx response as Down.
- State transitions (OK→Down, Down→OK) trigger notifications according to the selected mode.
- The Dock window provides manual checks, access to settings, and shortcuts to open the config and logs.
- Logs capture startup and each check result (status or error) for postmortem.

## Build & Deploy (macOS)

Build a macOS app bundle with py2app:

```bash
python3 -m pip install py2app
python3 -m pip install pillow
python3 scripts/make_icon.py && iconutil -c icns assets/AppIcon.iconset -o assets/AppIcon.icns
python3 setup.py py2app
open dist
```

Or use the helper script to build and create a DMG:

```bash
bash scripts/build_mac.sh
```

Customize the bundle identifier in `setup.py` (`CFBundleIdentifier`) before code signing.

The CI workflow automatically generates a crisp `.icns` Dock icon at build time and includes essential Qt plugins.

### Code signing and notarization (recommended)

To distribute outside the App Store, sign with a Developer ID certificate and notarize with Apple. Summary of steps:

- Ensure Xcode command line tools are installed and you have a Developer ID Application certificate in your login keychain.
- Set a unique bundle identifier in `setup.py`.
  - Example: `com.yourcompany.apitesttray`
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

### Troubleshooting (macOS)

- Remove quarantine after moving the app to Applications:
  - `xattr -dr com.apple.quarantine "/Applications/API Test Tray.app"`
- Run from Terminal with Qt plugin debug to see detailed loader output:
  - `QT_DEBUG_PLUGINS=1 "/Applications/API Test Tray.app/Contents/MacOS/API Test Tray"`
- Check logs: `open ~/Library/Logs/api_test_tray.log`
- If you don’t see the tray icon, open the Dock window from the tray menu or first-run prompt; on crowded menu bars the icon might be hidden.

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
 - Ensure the bundle identifier in `setup.py` matches your team’s preferences; the signing identity does not have to embed the bundle ID but should belong to the same Apple Developer Team.

### Releasing

Create a version tag to trigger the macOS build and release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds `dist/API Test Tray.app`, signs/notarizes (if secrets present), creates `dist/API Test Tray.dmg`, uploads artifacts, and publishes a GitHub Release with the DMG attached.

## Roadmap (notifications beyond the desktop)

Future optional integrations for off-device alerts:
- Slack (Incoming Webhook or Bot token)
- Email (SMTP or transactional APIs like SendGrid/Mailgun)
- SMS (Twilio)

These will be added as pluggable notifiers with simple configuration and safe secret handling.

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
